import os
import json
import io
import threading
import queue  # For thread-safe communication
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, Response, stream_with_context, jsonify, send_from_directory
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

#处理图片和云端模型的库
import base64  # 用于将图片编码发送给云端
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)

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
        llm = ChatTongyi(model_name="qwen-vl-plus", dashscope_api_key=api_key)

        # 将本地图片转换为 Base64 编码
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 构造多模态消息
        message = HumanMessage(
            content=[
                {"type": "text", "text": "请以专业的艺术鉴赏角度描述这张中国古代书画。"},
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
                api_key = os.getenv("DASHSCOPE_API_KEY") # 获取阿里云Key
                ali_model = os.getenv("ALI_MODEL0", "qwen-plus") # 获取云端模型名

                #  实例化问答系统
                rag_system = q_a.Neo4jRAGSystem(
                    neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                    neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
                    neo4j_password=os.getenv("NEO4J_PASSWORD", "12345678"), # 确保密码正确
                    
                    # --- 注入云端/本地切换参数 ---
                    llm_mode=llm_mode,
                    dashscope_api_key=api_key,
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
            input_size=1024,
            iou_threshold=0.7,
            conf_threshold=0.25,
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
        app.logger.info(f"开始云端图像描述: {segmented_path}")
        # 直接调用我们刚才写的云端函数
        success, description = describe_image_with_qwen(segmented_path)
        
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


@app.route('/get_artwork_details/<title>', methods=['GET'])
def get_artwork_details(title):
    """获取画作详细信息"""
    try:
        # 解码URL编码的标题
        import urllib.parse
        title = urllib.parse.unquote(title)

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


# 只有一个 artwork_image 路由定义 - 这是正确的版本
@app.route('/artwork_image/<filename>')
def get_artwork_image(filename):
    """获取画作图片 - 直接从artwork_images目录提供"""
    try:
        import urllib.parse
        # 解码文件名
        filename_decoded = urllib.parse.unquote(filename)

        # 去除扩展名，获取画作标题
        base_name = os.path.splitext(filename_decoded)[0]

        # 尝试不同的图片扩展名
        extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']

        # 直接在artwork_images/artworks目录查找
        image_dir = "artwork_images/artworks"

        for ext in extensions:
            image_path = os.path.join(image_dir, base_name + ext)
            if os.path.exists(image_path):
                return send_from_directory(image_dir, base_name + ext)

        # 如果找不到，尝试查找原始文件名（带扩展名的）
        if os.path.exists(os.path.join(image_dir, filename_decoded)):
            return send_from_directory(image_dir, filename_decoded)

        logger.warning(f"找不到画作图片: {filename_decoded}")
        # 返回404图片或占位符
        return jsonify({"error": "图片未找到"}), 404

    except Exception as e:
        logger.error(f"获取图片失败: {e}")
        return jsonify({"error": "获取图片失败"}), 500


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