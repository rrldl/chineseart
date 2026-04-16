import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import json
import io
import threading
import queue  # For thread-safe communication
import logging
from datetime import datetime
import urllib.parse
from functools import wraps
from flask import Flask, render_template, request, Response, stream_with_context, jsonify, send_from_directory, send_file, abort
import mimetypes
import q_a  # Assuming q_a.py is in the same directory or accessible via PYTHONPATH
from rich.console import Console
from ansi2html import Ansi2HTMLConverter  # For converting rich's ANSI output to HTML
from py2neo import Graph as Py2neoGraph  # Explicit import for clarity

from image_search_app import ImageSearchService

# 导入新模块
from data_collection import DataCollectionService
from la_clip_alignment import LAClipAlignmentService
from knowledge_graph import KnowledgeGraphManager
from application_service import ApplicationService
from performance_optimizer import cache_manager, async_processor, batch_processor
from dotenv import load_dotenv
import dashscope

#处理图片和云端模型的库
import base64  # 用于将图片编码发送给云端
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage

load_dotenv()

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
print("KEY =", os.getenv("DASHSCOPE_API_KEY"))

# 路径转换函数
def get_absolute_path(path_from_db):
    """
    将数据库中的绝对路径转换为当前环境下的绝对路径
    """
    if not path_from_db:
        return None
        
    # 从 .env 获取配置，如果没有配置则默认用 F 盘路径
    local_root = os.getenv("LOCAL_PROJECT_ROOT")

    # 1. 统一斜杠格式
    standard_path = path_from_db.replace("\\", "/")
    
    # 2. 核心替换：把数据库存的前缀（F:/Chineseart）换成当前的根目录
    if standard_path.startswith(db_prefix):
        # 只替换一次，得到当前电脑上的真实路径
        final_path = standard_path.replace(db_prefix, local_root, 1)
    else:
        # 如果路径里没包含前缀，说明存的是相对路径，直接拼接
        final_path = os.path.join(local_root, path_from_db)
        
    # 3. 转回系统识别的路径（Windows下会转回反斜杠）
    return os.path.abspath(final_path)

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
# 允许上传最大 50MB 的文件
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# 导入图像搜索服务
# 初始化图像搜索服务
image_search_service = None

# 初始化新服务
data_service = None
alignment_service = None
kg_manager = None
application_service = None


def init_image_search():
    """初始化图像搜索服务"""
    global image_search_service
    try:
        image_search_service = ImageSearchService(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD")
        )
        print("✓ 图像搜索服务初始化成功")
        return True
    except Exception as e:
        print(f"✗ 图像搜索服务初始化失败: {e}")
        return False


def init_new_services():
    """初始化新服务"""
    global data_service, alignment_service, kg_manager, application_service
    
    try:
        # 初始化数据采集服务
        data_service = DataCollectionService()
        print("✓ 数据采集服务初始化成功")
        
        # 初始化对齐服务
        alignment_service = LAClipAlignmentService(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD")
        )
        print("✓ 对齐服务初始化成功")
        
        # 初始化知识图谱管理器
        kg_manager = KnowledgeGraphManager(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD")
        )
        print("✓ 知识图谱管理器初始化成功")
        
        # 初始化应用服务
        application_service = ApplicationService(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD")
        )
        print("✓ 应用服务初始化成功")
        
        return True
    except Exception as e:
        print(f"✗ 新服务初始化失败: {e}")
        return False
#云端视觉描述函数  
def describe_image_with_qwen(image_path):
    """使用通义千问视觉大模型 (qwen-vl-plus) 描述图片"""
    try:
        from langchain_community.chat_models import ChatTongyi
        from langchain_core.messages import HumanMessage
        import base64

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return False, "缺少 DASHSCOPE_API_KEY"

        # 初始化视觉模型
        llm = ChatTongyi(model_name="qwen-vl-plus", dashscope_api_key="DASHSCOPE_API_KEY")

        # 将本地图片转换为 Base64 编码
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 构造多模态消息
        prompt_text = (
            "你是一位经验丰富的中国古代艺术史专家和书画鉴赏家。请以专业、严谨、结构化的方式，详细分析眼前这幅图像。\n\n"
            "重要提示：请忽略图像中的红色轮廓线、彩色遮罩区域和分割标记，这些是分析工具留下的。请专注于底层原画的艺术风格、构图、笔触和历史背景进行鉴赏。\n\n"
            "分析要求：\n"
            "1.  客观描述优先：首先对画面进行客观的视觉描述，不加入主观推测。\n"
            "2.  逻辑推断：在描述的基础上，结合艺术史知识进行推断。\n\n"
            "请从以下几个核心角度展开分析：\n\n"
            "1.  主题与内容：画面描绘了什么？是山水、人物、花鸟，还是书法？如果有人物，他们在做什么？如果是山水，描绘的是何种景致？\n\n"
            "2.  风格与技法：笔墨线条特点？如果是山水画，主要使用了哪种皴法？是水墨画还是设色画？色彩运用有何特点？\n\n"
            "3.  构图与布局：画面元素如何安排？空间感处理得如何？\n\n"
            "4.  印章与题跋：画面上是否有可见的印章或文字？若有，描述其位置和颜色。\n\n"
            "5.  作者与朝代推断：风格最符合哪个朝代？可能出自哪个流派或画家？\n\n"
            "6.  情感与意境：这幅画作传达了怎样的情感或氛围？\n\n"
            "请用专业术语进行描述，并以清晰的结构输出你的分析报告。"
        )
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {"type": "image", "image": f"data:image/png;base64,{image_base64}"}
            ]
        )

        # 调用模型
        response = llm.invoke([message])
        content = response.content
        
        # --- 提取文字逻辑 ---
        if isinstance(content, list):
            final_text = ""
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    final_text += item['text']
            description = final_text
        else:
            description = str(content)
        
        # 清理格式
        description = description.replace('**', '')
        import re
        
        # 直接让前端处理格式，后端只保留原始文本
        # 这样前端的 formatArtReport 函数可以完全控制格式化
        
        # 只清理多余的空行
        lines = description.split('\n')
        formatted_lines = []
        empty_line_count = 0

        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
                empty_line_count = 0
            else:
                empty_line_count += 1
                if empty_line_count == 1 and formatted_lines:
                    formatted_lines.append('')

        # 清理开头和结尾的空行
        while formatted_lines and not formatted_lines[0]:
            formatted_lines.pop(0)
        while formatted_lines and not formatted_lines[-1]:
            formatted_lines.pop()

        description = '\n'.join(formatted_lines)
            
        return True, description

    except Exception as e:
        if 'logger' in globals():
            logger.error(f"云端图像描述出错: {e}")
        return False, str(e)
    

# 在 Flask 启动时初始化
init_image_search()
init_new_services()

# --- Helper for Log Streaming ---
def sse_log_print(*args, **kwargs):
    """
    Monkey-patched print function for q_a.console.
    Captures rich output and yields it for SSE.
    """
    global current_sse_yield_callback
    if not current_sse_yield_callback:
        if original_q_a_console_print:
            original_q_a_console_print(*args, **kwargs)
        return

    s_io = io.StringIO()
    if args and hasattr(args[0], '__rich_console__'):
        temp_console_for_export = Console(file=s_io, record=True, width=100, force_terminal=False, color_system=None)
        temp_console_for_export.print(*args, **kwargs)
        s_io.seek(0)
        s_io.truncate(0)
        recorded_console = Console(file=s_io, record=True, width=100)
        recorded_console.print(*args, **kwargs)
        html_content = recorded_console.export_html(inline_styles=True, code_format="<pre class=\"code\">{code}</pre>")

        if "<!DOCTYPE html>" in html_content:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            body_content = soup.body.decode_contents() if soup.body else html_content
            body_content = body_content.replace("background-color:#ffffff;", "", 1).replace("color:#000000;", "", 1)
            current_sse_yield_callback(f"data: {json.dumps({'type': 'log_html', 'content': body_content})}\n\n")
    else:
        temp_console_for_ansi = Console(file=s_io, force_terminal=True, color_system="truecolor", width=100)
        temp_console_for_ansi.print(*args, **kwargs)
        ansi_output = s_io.getvalue()
        conv = Ansi2HTMLConverter(inline=True, scheme="solarized", linkify=False, dark_bg=True)
        html_output = conv.convert(ansi_output, full=False)
        log_content = f'<div class="log-entry-raw">{html_output}</div>'
        current_sse_yield_callback(f"data: {json.dumps({'type': 'log_html', 'content': log_content})}\n\n")

    if original_q_a_console_print:
        original_q_a_console_print(*args, **kwargs)


# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    """首页"""
    # ✅ 从环境变量获取 Neo4j 配置，传给前端显示
    neo4j_config = {
        "uri": os.getenv("NEO4J_URI"),
        "user": os.getenv("NEO4J_USER"),
    }
    return render_template("index.html", neo4j_config=neo4j_config)


@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.json
    question_text = data.get("question")
    enable_multi_hop = data.get("enable_multi_hop", True)
    search_budget = data.get("search_budget", "Deeper")

    if not question_text:
        return Response(json.dumps({"error": "No question provided."}), status=400, mimetype='application/json')

    def generate_response_stream():
        message_queue = queue.Queue()
        finished_signal = threading.Event()

        class SseLogStreamWrapper(io.TextIOBase):
            def __init__(self, q):
                self.queue = q
                self.buffer = ""
                self.ansi_conv = Ansi2HTMLConverter(inline=True, scheme="solarized", linkify=False, dark_bg=True)

            def write(self, s: str):
                if not isinstance(s, str):
                    try:
                        s = s.decode(errors='replace')
                    except (AttributeError, UnicodeDecodeError):
                        s = str(s)
                self.buffer += s
                while True:
                    try:
                        newline_index = self.buffer.index('\n')
                    except ValueError:
                        break
                    line_to_process = self.buffer[:newline_index + 1]
                    self.buffer = self.buffer[newline_index + 1:]
                    if line_to_process.strip():
                        html_line = self.ansi_conv.convert(line_to_process.strip(), full=False)
                        self.queue.put({'type': 'log_html', 'content': f"<div class='log-item'>{html_line}</div>"})
                return len(s.encode())

            def flush(self):
                if self.buffer.strip():
                    html_line = self.ansi_conv.convert(self.buffer.strip(), full=False)
                    self.queue.put({'type': 'log_html', 'content': f"<div class='log-item'>{html_line}</div>"})
                    self.buffer = ""

            def isatty(self):
                return False

            def readable(self):
                return False

            def seekable(self):
                return False

            def writable(self):
                return True

        def rag_worker(q, question, multi_hop, budget, finish_event):
            original_q_a_console_file = None
            worker_sse_wrapper = SseLogStreamWrapper(q)

            try:
                if hasattr(q_a, 'console') and hasattr(q_a.console, 'file'):
                    original_q_a_console_file = q_a.console.file

                if hasattr(q_a, 'console'):
                    q_a.console.file = worker_sse_wrapper
                else:
                    q.put({'type': 'error', 'content': 'Internal error: q_a.console not found.'})
                    finish_event.set()
                    return


                #以下是修改

                # 从环境变量读取配置
                llm_mode = os.getenv("LL_MODE", "cloud") # 获取模式，默认cloud
                dashscope_api_key = os.getenv("DASHSCOPE_API_KEY") # 获取阿里云Key
                ali_model = os.getenv("ALI_MODEL0", "qwen-plus") # 获取云端模型名

                #  实例化问答系统
                rag_system = q_a.Neo4jRAGSystem(
                    neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                    neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
                    neo4j_password=os.getenv("NEO4J_PASSWORD", "12345678"), # 确保密码正确
                    
                    # --- 注入云端/本地切换参数 ---
                    llm_mode=llm_mode,
                    dashscope_api_key=dashscope_api_key,
                    ali_model=ali_model,
                    
                    # --- 注入本地备选参数 ---
                    ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), 
                    ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    
                    # --- 其他原有参数 ---
                    enable_multi_hop=multi_hop,
                    search_budget_mode=budget
                )

                 #以上是修改

                final_answer = rag_system.answer_question(question)
                worker_sse_wrapper.flush()
                q.put({'type': 'answer', 'content': final_answer})

            except Exception as e:
                app.logger.error(f"Error in RAG worker thread: {e}", exc_info=True)
                try:
                    worker_sse_wrapper.flush()
                except:
                    pass
                q.put({'type': 'error', 'content': f"An error occurred: {str(e)}"})
            finally:
                if original_q_a_console_file is not None and hasattr(q_a, 'console'):
                    q_a.console.file = original_q_a_console_file
                finish_event.set()
                q.put({'type': 'finished'})

        worker_thread = threading.Thread(target=rag_worker, args=(
            message_queue, question_text, enable_multi_hop, search_budget, finished_signal))
        worker_thread.start()

        while not finished_signal.is_set() or not message_queue.empty():
            try:
                msg = message_queue.get(timeout=0.1)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get('type') == 'finished':
                    break
            except queue.Empty:
                continue
            except Exception as e:
                app.logger.error(f"Error yielding SSE message: {e}")
                break

    return Response(stream_with_context(generate_response_stream()), mimetype='text/event-stream')


@app.route('/upload_image', methods=['POST'])
def upload_image():
    """处理图像文件上传和分割"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file uploaded."}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "No image file selected."}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    if not (image_file.filename and '.' in image_file.filename and
            image_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({"error": "Unsupported file type. Please upload PNG, JPG, JPEG, GIF, BMP, or TIFF files."}), 400

    try:
        # 延迟导入，避免模块加载时的依赖问题
        from artwork_segmentation import image_segmentation_service
        
        app.logger.info(f"开始处理图像文件: {image_file.filename}")
        uploaded_path = image_segmentation_service.save_uploaded_image(image_file)

        if not uploaded_path:
            return jsonify({"error": "Failed to save uploaded image."}), 500

        app.logger.info(f"开始图像分割: {uploaded_path}")
        segmented_path, original_path, seg_info = image_segmentation_service.segment_artwork(
            uploaded_path,
            input_size=2048,
            iou_threshold=0.6,
            conf_threshold=0.1,
            better_quality=True,
            withContours=True,
            use_retina=True,
            mask_random_color=True
        )

        if not segmented_path:
            app.logger.error(f"图像分割失败: {seg_info}")
            return jsonify({"error": f"Image segmentation failed: {seg_info}"}), 500

        app.logger.info(f"开始图像描述: {segmented_path}")
        # 延迟导入，避免模块加载时的依赖问题
        from artwork_description import image_description_service

        # --- 修改开始：使用云端模型代替本地 Ollama ---
        app.logger.info(f"开始云端图像描述: {original_path}")
        # 直接调用我们刚才写的云端函数 - 使用原始图像，而不是分割后的图像
        success, description = describe_image_with_qwen(original_path)
        
        if not success:
            app.logger.warning(f"云端图像描述失败: {description}")
            # 如果云端也失败了，再尝试一次本地作为兜底（或者直接报错）
            description = "图像描述生成失败（云端连接异常）。"
        # --- 修改结束 ---
    

        if not success:
            app.logger.warning(f"图像描述失败: {description}")
            description = "图像描述生成失败，但图像分割已完成。"

        app.logger.info(f"图像分割和描述完成: {segmented_path}")

        return jsonify({
            "success": True,
            "original_image": f"/uploads/{os.path.basename(original_path)}",
            "segmented_image": f"/segmented/{os.path.basename(segmented_path)}",
            "segmentation_info": seg_info,
            "description": description
        })

    except Exception as e:
        app.logger.error(f"图像分割过程中出错: {e}", exc_info=True)
        return jsonify({"error": f"Image segmentation error: {str(e)}"}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)


@app.route('/segmented/<filename>')
def segmented_file(filename):
    return send_from_directory('static/segmented', filename)


@app.route('/search_by_image', methods=['POST'])
def search_by_image():
    """以图搜图"""
    if 'image' not in request.files:
        return jsonify({"error": "请上传图片"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "请选择图片文件"}), 400

    # 获取数量参数，默认为5
    try:
        top_k = int(request.form.get('count', 5))
    except:
        top_k = 5
    # 确保数量在有效范围内
    top_k = max(1, min(top_k, 10))  # 限制在1-10之间

    # 保存临时文件
    import time
    timestamp = int(time.time())
    temp_path = f"temp_{timestamp}_{image_file.filename}"
    try:
        image_file.save(temp_path)
    except Exception as e:
        logger.error(f"保存临时文件失败: {e}")
        return jsonify({"error": f"保存图片失败: {str(e)}"}), 500

    try:
        # 检查服务是否初始化
        if image_search_service is None:
            success = init_image_search()
            if not success or image_search_service is None:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({"error": "图像搜索服务未初始化"}), 500

        # 进行图像搜索，传入数量参数
        results = image_search_service.search_by_image(temp_path, top_k=top_k)

        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 检查是否有错误
        if results is None:
            return jsonify({"error": "搜索服务返回了空结果，请检查后端日志"}), 500
        
        if isinstance(results, dict) and 'error' in results:
            return jsonify({"error": results['error']}), 500
        # 统一返回格式
        artworks = results.get('artworks', [])
        actual_count = len(artworks)

        return jsonify({
            "success": True,
            "results": artworks,
            "count": actual_count,
            "requested_count": top_k,
            "message": f"找到 {actual_count} 个相似作品 (请求 {top_k} 个)",
            "seals": results.get('seals', []),
            "inscriptions": results.get('inscriptions', [])
        })

    except Exception as e:
        logger.error(f"以图搜图失败: {e}", exc_info=True)
        # 清理临时文件
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return jsonify({"error": f"搜索失败: {str(e)}"}), 500


@app.route('/search_by_text', methods=['POST'])
def search_by_text():
    """以文搜图"""
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "请输入搜索文本"}), 400

    # 获取数量参数，默认为5
    try:
        top_k = int(data.get('count', 5))
    except:
        top_k = 5
    # 确保数量在有效范围内
    top_k = max(1, min(top_k, 10))  # 限制在1-10之间

    try:
        # 检查服务是否初始化
        if image_search_service is None:
            success = init_image_search()
            if not success or image_search_service is None:
                return jsonify({"error": "图像搜索服务未初始化"}), 500

        results = image_search_service.search_by_text(text, top_k=top_k)

        # 检查是否有错误
        if 'error' in results:
            return jsonify({"error": results['error']}), 500

        # 统一返回格式
        artworks = results.get('artworks', [])
        actual_count = len(artworks)

        return jsonify({
            "success": True,
            "results": artworks,
            "count": actual_count,
            "requested_count": top_k,
            "message": f"找到 {actual_count} 个相关作品 (请求 {top_k} 个)",
            "seals": results.get('seals', []),
            "inscriptions": results.get('inscriptions', [])
        })

    except Exception as e:
        logger.error(f"以文搜图失败: {e}", exc_info=True)
        return jsonify({"error": f"搜索失败: {str(e)}"}), 500


@app.route('/get_artwork_details', methods=['GET'])
def get_artwork_details():
    """获取画作详细信息"""
    try:
        # 从查询参数获取标题和文件名
        import urllib.parse
        title = urllib.parse.unquote(request.args.get('title', ''))
        image_filename = urllib.parse.unquote(request.args.get('image_filename', ''))

        if not title:
            return jsonify({"error": "缺少标题参数"}), 400

        if image_filename:
            # 复合查询：标题 + 文件名，确保唯一性
            query = """
            MATCH (a:Artwork)
            WHERE a.title = $title AND a.image_filename = $filename
            OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
            OPTIONAL MATCH (a)-[:PART_OF]->(dynasty:Dynasty)
            OPTIONAL MATCH (a)-[:HAS_STYLE]->(style:Style)
            OPTIONAL MATCH (a)-[:HAS_SEAL]->(seal:Seal)
            OPTIONAL MATCH (a)-[:HAS_INSCRIPTION]->(ins:Inscription)
            RETURN a, 
                   collect(DISTINCT artist.name) as authors,
                   collect(DISTINCT dynasty.name) as dynasties,
                   collect(DISTINCT style.name) as styles,
                   collect(DISTINCT {text: seal.text, owner: seal.owner, type: seal.type}) as seals,
                   collect(DISTINCT {text: ins.text, author: ins.author, type: ins.type}) as inscriptions
            """
            result = image_search_service.graph.run(query, title=title, filename=image_filename).data()
        else:
            # 只使用标题查询
            query = """
            MATCH (a:Artwork {title: $title})
            OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
            OPTIONAL MATCH (a)-[:PART_OF]->(dynasty:Dynasty)
            OPTIONAL MATCH (a)-[:HAS_STYLE]->(style:Style)
            OPTIONAL MATCH (a)-[:HAS_SEAL]->(seal:Seal)
            OPTIONAL MATCH (a)-[:HAS_INSCRIPTION]->(ins:Inscription)
            RETURN a, 
                   collect(DISTINCT artist.name) as authors,
                   collect(DISTINCT dynasty.name) as dynasties,
                   collect(DISTINCT style.name) as styles,
                   collect(DISTINCT {text: seal.text, owner: seal.owner, type: seal.type}) as seals,
                   collect(DISTINCT {text: ins.text, author: ins.author, type: ins.type}) as inscriptions
            """
            result = image_search_service.graph.run(query, title=title).data()

        if result:
            artwork_data = result[0]
            # 将节点属性转换为字典
            artwork_data['a'] = dict(artwork_data['a'])
            return jsonify(artwork_data)
        else:
            return jsonify({"error": "未找到该画作"}), 404
    except Exception as e:
        logger.error(f"获取画作详情失败: {e}", exc_info=True)
        return jsonify({"error": f"获取详情失败: {str(e)}"}), 500


# 定义两个确切的图片存储路径
DIR_BMP = r"F:\Chineseart\artworks"                 # 112张 BMP
DIR_JPG = r"F:\Chineseart\artworks"  # 217张 JPG

@app.route('/artwork_image/<filename>')
def serve_artwork(filename):
    """兼容旧前端的按文件名获取图片接口（全门类通用）"""
    print(f"DEBUG: 触发旧图片接口兜底，请求文件名: {filename}")

    try:
        from py2neo import Graph
        from flask import send_file, abort
        import os
        
        # 1. 连接数据库
        graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
        
        # 2. 查询数据库拿 path
        query = """
        MATCH (n) 
        WHERE n.image_filename = $f 
          AND (n:Artwork OR n:Seal OR n:Inscription OR n:ArtistPortrait)
        RETURN n.path AS db_path LIMIT 1
        """
        res = graph.run(query, f=filename).data()
        
        if res and res[0].get('db_path'):
            # --- 关键修改点：转换路径 ---
            db_path = res[0]['db_path']
            full_path = get_absolute_path(db_path)
            
            # 3. 检查文件是否真的存在
            if full_path and os.path.exists(full_path):
                # 针对 bmp 的小优化保持不变
                if full_path.lower().endswith('.bmp'):
                    return send_file(full_path, mimetype='image/bmp')
                else:
                    return send_file(full_path)
            else:
                print(f"ERROR: 磁盘上找不到文件: {full_path}")
                
    except Exception as e:
        print(f"DEBUG: 接口异常: {e}")

    print(f"ERROR: 找不到图片文件记录或磁盘文件已丢失: {filename}")
    from flask import abort
    return abort(404)

IMAGE_BASE_DIR = os.getenv("LOCAL_PROJECT_ROOT")

@app.route('/api/get_image')
def get_image():
    """带深度调试的图片获取接口"""
    try:
        image_rel_path = request.args.get('path')
        if not image_rel_path:
            return "Missing path", 400
        
        # 1. 解码
        image_rel_path = urllib.parse.unquote(image_rel_path)
        
        full_path = os.path.normpath(os.path.join(IMAGE_BASE_DIR, image_rel_path))

        if os.path.exists(full_path):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            return send_from_directory(directory, filename)
        else:
            return f"File not found: {image_rel_path}", 404

    except Exception as e:
        app.logger.error(f"读取图片失败: {e}")
        return str(e), 500


# 启用新API路由

@app.route('/api/qa', methods=['POST'])
def api_qa():
    """智能问答系统API"""
    try:
        data = request.json
        question = data.get("question")
        top_k = data.get("top_k", 5)

        if not question:
            return jsonify({"error": "请提供问题"}), 400

        # 检查服务是否初始化
        if application_service is None:
            success = init_new_services()
            if not success or application_service is None:
                return jsonify({"error": "应用服务未初始化"}), 500

        # 调用智能问答系统
        result = application_service.rag_qa_system(question, top_k)

        return jsonify({
            "success": True,
            "question": result["question"],
            "answer": result["answer"],
            "entities": result["entities"]
        })

    except Exception as e:
        logger.error(f"问答系统失败: {e}")
        return jsonify({"error": f"问答系统失败: {str(e)}"}), 500


@app.route('/api/cross_modal_search', methods=['POST'])
def api_cross_modal_search():
    """跨模态检索API"""
    try:
        data = request.json
        query = data.get("query")
        search_type = data.get("search_type", "text_to_image")
        top_k = data.get("top_k", 5)

        if not query:
            return jsonify({"error": "请提供查询内容"}), 400

        # 检查服务是否初始化
        if application_service is None:
            success = init_new_services()
            if not success or application_service is None:
                return jsonify({"error": "应用服务未初始化"}), 500

        # 调用跨模态检索
        results = application_service.cross_modal_search(query, search_type, top_k)

        return jsonify({
            "success": True,
            "query": query,
            "search_type": search_type,
            "results": results,
            "count": len(results)
        })

    except Exception as e:
        logger.error(f"跨模态检索失败: {e}")
        return jsonify({"error": f"跨模态检索失败: {str(e)}"}), 500


@app.route('/api/build_ontology', methods=['POST'])
def api_build_ontology():
    """构建本体API"""
    try:
        # 检查服务是否初始化
        if application_service is None:
            success = init_new_services()
            if not success or application_service is None:
                return jsonify({"error": "应用服务未初始化"}), 500

        # 构建本体
        ontology = application_service.kg_manager.build_ontology()

        return jsonify({
            "success": True,
            "ontology": ontology
        })

    except Exception as e:
        logger.error(f"构建本体失败: {e}")
        return jsonify({"error": f"构建本体失败: {str(e)}"}), 500


@app.route('/api/batch_process', methods=['POST'])
def api_batch_process():
    """批量处理艺术品数据API"""
    try:
        data = request.json
        artworks = data.get("artworks", [])

        if not artworks:
            return jsonify({"error": "请提供艺术品数据"}), 400

        # 检查服务是否初始化
        if application_service is None:
            success = init_new_services()
            if not success or application_service is None:
                return jsonify({"error": "应用服务未初始化"}), 500

        # 批量处理
        results = application_service.batch_process_artworks(artworks)

        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })

    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        return jsonify({"error": f"批量处理失败: {str(e)}"}), 500


@app.route('/api/crawl_data', methods=['POST'])
def api_crawl_data():
    """爬取百科数据API"""
    try:
        data = request.json
        query = data.get("query")
        entity_type = data.get("entity_type", "Artist")

        if not query:
            return jsonify({"error": "请提供查询关键词"}), 400

        # 检查服务是否初始化
        if data_service is None:
            success = init_new_services()
            if not success or data_service is None:
                return jsonify({"error": "数据服务未初始化"}), 500

        # 爬取数据
        result = data_service.crawl_encyclopedia_data(query, entity_type)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:
        logger.error(f"爬取数据失败: {e}")
        return jsonify({"error": f"爬取数据失败: {str(e)}"}), 500


@app.route('/api/align_entity', methods=['POST'])
def api_align_entity():
    """对齐实体API"""
    try:
        data = request.json
        entity_id = data.get("entity_id")
        entity_type = data.get("entity_type")
        image_paths = data.get("image_paths", [])
        texts = data.get("texts", [])

        if not entity_id or not entity_type:
            return jsonify({"error": "请提供实体ID和类型"}), 400

        # 检查服务是否初始化
        if alignment_service is None:
            success = init_new_services()
            if not success or alignment_service is None:
                return jsonify({"error": "对齐服务未初始化"}), 500

        # 对齐实体
        result = alignment_service.align_entity(entity_id, entity_type, image_paths, texts)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:
        logger.error(f"对齐实体失败: {e}")
        return jsonify({"error": f"对齐实体失败: {str(e)}"}), 500


# --- Startup Neo4j Connection Test ---
def test_neo4j_connection():
    try:
        graph = Py2neoGraph(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD")
            )
        )
        graph.run("RETURN 1")
        app.logger.info("Neo4j connection successful at startup.")
    except Exception as e:
        app.logger.error(f"Neo4j connection failed at startup: {e}")
        # Optional: sys.exit(1) if you want to crash on failure


# --- Main ---
if __name__ == "__main__":
    # 确保静态目录存在
    os.makedirs("static/artworks", exist_ok=True)
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("static/segmented", exist_ok=True)

    test_neo4j_connection()  # Test connection before starting server
    app.run(debug=True, host="0.0.0.0", port=5001, threaded=True, use_reloader=False)
