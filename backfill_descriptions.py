import os
import json
import re
import dashscope
from dashscope import MultiModalConversation
from py2neo import Graph, NodeMatcher
from dotenv import load_dotenv
# 补齐217张图的描述 2026.4.7
# 217张图的描述来自 JSON 文件，112张图的描述来自 Qwen-VL-Plus
# --- 1. 初始化 ---
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

graph = Graph(os.getenv("NEO4J_URI", "bolt://localhost:7687"), 
              auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")))
matcher = NodeMatcher(graph)

def get_visual_description(image_path, title, author, dynasty):
    """调用 Qwen-VL-Plus 获取图片的详细描述"""
    try:
        abs_path = os.path.abspath(image_path)
        prompt = (
            f"这张图片确认为中国名画《{title}》的局部或全图，作者是{author}（{dynasty}）。"
            "请根据此事实，详细描述该画面的艺术内容（如山石笔触、树木造型、色彩运用、意境氛围），"
            "字数控制在 100-200 字左右，风格要专业且具有艺术感。"
            "严格按 JSON 格式返回：{'detail': '...'}"
        )

        messages = [{
            "role": "user",
            "content": [
                {"image": f"file://{abs_path}"},
                {"text": prompt}
            ]
        }]

        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)

        if response.status_code == 200:
            text_result = response.output.choices[0].message.content[0]['text']
            # 兼容有些模型返回时带的 markdown 代码块
            match = re.search(r'\{.*\}', text_result, re.DOTALL)
            if match:
                json_str = match.group().replace("'", '"')
                # 再次清理可能存在的非法字符或换行
                try:
                    data = json.loads(json_str)
                    return data.get('detail', '')
                except:
                    # 如果 JSON 解析失败，尝试直接返回清理后的文本
                    return text_result.strip()
        else:
            print(f"  [Error] {title}: {response.message}")
            return None
    except Exception as e:
        print(f"  [Exception] {title}: {e}")
        return None

def backfill_descriptions():
    print("Starting description backfill for 217 artworks (source: sync_all_images_pipeline)...")
    
    # 强制选取 217 张图这批来源的所有节点进行重刷
    artworks = graph.run(
        "MATCH (a:Artwork) WHERE a.source = 'sync_all_images_pipeline' RETURN a"
    ).data()
    
    print(f"Found {len(artworks)} artworks to re-process.")

    count = 0
    for i, item in enumerate(artworks):
        node = item['a']
        title = node.get('title', 'Unknown')
        author = node.get('author', 'Unknown')
        dynasty = node.get('dynasty', 'Unknown')
        img_path = node.get('image_path')

        if not img_path or not os.path.exists(img_path):
            print(f"  [{i+1}/{len(artworks)}] Skipping {title}: Invalid path")
            continue

        print(f"  [{i+1}/{len(artworks)}] Generating description for {title}...")
        description = get_visual_description(img_path, title, author, dynasty)
        
        if description:
            # 去除描述中的 JSON 标签（如果有残留）
            description = re.sub(r'\{"detail":\s*"|"\s*\}', '', description)
            node['description'] = description
            graph.push(node)
            count += 1
            print(f"    - Success: Description updated.")
        
    print(f"\nDone! Updated {count} artworks.")

if __name__ == "__main__":
    backfill_descriptions()
