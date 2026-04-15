import os
import time
from py2neo import Graph
import dashscope
from dashscope import MultiModalConversation
from PIL import Image
import tempfile
from dotenv import load_dotenv

# --- 1. 环境配置 ---
load_dotenv()
dashscope.api_key = os.getenv("sk-18e0af55804c4829ae1bea3fb95c4aa9")
graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

def get_ai_description_fixed(image_path, node_name, artist, dynasty):
    """带压缩处理的 AI 描述生成函数"""
    temp_file_path = None
    try:
        # 处理 BMP 大文件锁定问题
        file_size = os.path.getsize(image_path)
        if image_path.lower().endswith('.bmp') or file_size > 5 * 1024 * 1024:
            with Image.open(image_path) as img:
                rgb_img = img.convert('RGB')
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_file_path = temp_file.name
                temp_file.close() 
                rgb_img.save(temp_file_path, 'JPEG', quality=85)
                image_to_send = f"file://{temp_file_path}"
        else:
            image_to_send = f"file://{image_path}"

        prompt = f"你是一位中国传统书法鉴赏专家。这张图是《{node_name}》，作者：{artist}，年代：{dynasty}。请给出一段100-150字的专业描述，包含字体特征、拓本质感与艺术风格。请直接输出描述。"
        
        messages = [{"role": "user", "content": [{"image": image_to_send}, {"text": prompt}]}]
        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
        
        if response.status_code == 200:
            return response.output.choices[0].message.content[0]['text']
        else:
            return None
    except Exception as e:
        print(f"处理 {node_name} 时出错: {e}")
        return None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.remove(temp_file_path)
            except: pass

# --- 2. 核心补救逻辑 ---
def patch_missing_descriptions():
    # 查询所有描述为“待补充”的节点
    query = """
    MATCH (n:Inscription)
    WHERE n.description = '待补充描述' OR n.description = '描述生成异常'
    RETURN n
    """
    nodes_to_fix = graph.run(query).data()
    
    print(f"发现 {len(nodes_to_fix)} 个节点需要补救...")
    
    for record in nodes_to_fix:
        node = record['n']
        print(f"正在为 [{node['name']}] 生成描述...")
        
        # 调用修复后的 AI 函数
        new_desc = get_ai_description_fixed(
            node['path'], 
            node['name'], 
            node.get('artist', '佚名'), 
            node.get('dynasty', '未知')
        )
        
        if new_desc:
            # 直接更新 Neo4j 节点属性
            node['description'] = new_desc
            graph.push(node)
            print(f"✅ 成功更新: {node['name']}")
            # 稍微停顿，防止 API 并发过高
            time.sleep(0.8)
        else:
            print(f"❌ 更新失败: {node['name']}")

if __name__ == "__main__":
    patch_missing_descriptions()
    print("--- 补救工作完成 ---")