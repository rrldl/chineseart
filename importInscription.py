import os
import json
import time
from py2neo import Graph, Node
import dashscope
from dashscope import MultiModalConversation

# --- 整合后的配置读取部分 ---
from dotenv import load_dotenv

load_dotenv()

# API 配置
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# Neo4j 配置
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "你的默认密码")

graph = Graph(uri, auth=(user, password))

IMAGE_DIR = r"F:\Chineseart\inscriptions"
JSON_PATH = r"F:\Chineseart\detail_json\works_details_inscriptions_cleaned.json"


# --- 1. 加载 JSON 数据 ---
print("正在加载 JSON 配置文件...")
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

import io
from PIL import Image
import tempfile

def get_ai_description(image_path, basic_info):
    """调用 Qwen-VL 视觉模型生成专业描述（修复 Windows 文件锁定问题）"""
    temp_file_path = None
    try:
        file_size = os.path.getsize(image_path)
        
        if image_path.lower().endswith('.bmp') or file_size > 5 * 1024 * 1024:
            with Image.open(image_path) as img:
                rgb_img = img.convert('RGB')
                # delete=False 配合手动 close 是 Windows 下处理临时文件的稳妥做法
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file_path = temp_file.name
                temp_file.close()  # 立即关闭句柄，释放锁定
                
                rgb_img.save(temp_file_path, 'JPEG', quality=85)
                image_to_send = f"file://{temp_file_path}"
        else:
            image_to_send = f"file://{image_path}"

        prompt = f"""
        你是一位中国传统书法鉴赏专家。
        已知这张图片是《{basic_info['work_name']}》的局部，作者是{basic_info['artist']}，属于{basic_info['dynasty']}时期。
        请观察图片，给出一段100-150字的专业描述，内容包括：书法字体及笔画特征、拓本质感、整体艺术风格。
        请直接输出描述文字。
        """
        
        messages = [{"role": "user", "content": [{"image": image_to_send}, {"text": prompt}]}]
        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
        
        if response.status_code == 200:
            return response.output.choices[0].message.content[0]['text']
        else:
            print(f"AI 调用失败: {response.code} - {response.message}")
            return "暂无详细描述"

    except Exception as e:
        print(f"处理异常: {e}")
        return "描述生成异常"
    finally:
        # 确保在函数结束时清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass # 如果实在删不掉就随它去，系统重启会自动清理 Temp
# --- 2. 遍历图片并导入 ---
def run_import():
    files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.bmp', '.jpg', '.png'))]
    print(f"共发现 {len(files)} 张图片，准备开始处理...")

    for filename in files:
        # 解析文件名: 60d5bbee1376494a7ff87ccb_2.bmp
        # 假设文件名格式是 {ID}_{序号}.bmp
        if "_" in filename:
            json_id = filename.rsplit('_', 1)[0]
            part_index = filename.rsplit('_', 1)[1].split('.')[0]
        else:
            json_id = filename.split('.')[0]
            part_index = "1"

        full_path = os.path.join(IMAGE_DIR, filename)
        
        # 从 JSON 获取基本属性
        info = json_data.get(json_id, {})
        suha = info.get('suha', {})
        
        basic_info = {
            "work_name": suha.get('name', '未知书法'),
            "artist": suha.get('author', '佚名'),
            "dynasty": suha.get('age', '年代不详'),
            "tags": ",".join(suha.get('tags', [])),
            "source_id": json_id
        }

        # 判断是否需要 AI 生成描述
        # 如果 JSON 里的 desc 只是“包含XX张图”这种废话，就调 AI
        raw_desc = suha.get('desc', '')
        if "包含" in raw_desc and "张" in raw_desc:
            print(f"[{filename}] 正在请求 AI 生成专业描述...")
            final_description = get_ai_description(full_path, basic_info)
            # 适当休眠防止限流
            time.sleep(0.5)
        else:
            final_description = raw_desc if raw_desc else "待补充描述"

        # --- 3. 创建 Neo4j 节点 ---
        inscription_node = Node(
            "Inscription",
            name=f"{basic_info['work_name']} - 局部{part_index}",
            artist=basic_info['artist'],
            dynasty=basic_info['dynasty'],
            description=final_description,
            path=full_path,
            part_order=int(part_index),
            tags=basic_info['tags'],
            source_id=basic_info['source_id'],
        )
        
        graph.merge(inscription_node, "Inscription", "path")
        print(f"成功导入: {basic_info['work_name']} (局部{part_index})")

if __name__ == "__main__":
    run_import()
    print("--- 导入全部完成 ---")