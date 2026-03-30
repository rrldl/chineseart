import os
import json
import dashscope
import re
from py2neo import Graph, NodeMatcher
from dotenv import load_dotenv
from dashscope import MultiModalConversation, Generation

# --- 1. 核心初始化 ---
# 必须先执行 load_dotenv() 才能读取到 .env 里的内容
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 检查 Key 是否加载成功
if not dashscope.api_key:
    
    raise ValueError("错误：未检测到 DASHSCOPE_API_KEY，请检查 .env 文件路径是否在 F:\\Chineseart\\.env")

# 连接 Neo4j
graph = Graph("bolt://localhost:7687", auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
matcher = NodeMatcher(graph)

# 图片目录
IMAGE_DIR = r'F:\Chineseart\artwork_images\artworks'

def get_ground_truth(title):
    """
    【事实检索】利用文本大模型查明历史真相
    """
    print(f"正在检索《{title}》的历史真实背景...")
    prompt = f"中国名画《{title}》公认的作者是谁？属于哪个朝代？艺术流派是什么？请严谨回答，仅以JSON格式返回，禁止任何废话：{{'author': '...', 'dynasty': '...', 'style': '...'}}"
    
    try:
        response = Generation.call(model='qwen-plus', prompt=prompt)
        if response.status_code == 200:
            res_text = response.output.text
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if match:
                # 统一转为双引号解析
                return json.loads(match.group().replace("'", '"'))
        return None
    except Exception as e:
        print(f"   检索真相失败: {e}")
        return None

def master_sync_pipeline_v2():
    all_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f" 发现 {len(all_files)} 张图片，启动‘知识锚定’模式...")

    # 缓存已查询过的作品事实，避免重复调用（省钱 + 统一属性）
    fact_cache = {}

    for filename in all_files:
        # 1. 精准提取主标题 (例如: '千里江山图_1.jpg' -> '千里江山图')
        # 考虑到你的文件名可能有 '局部' 两个字，我们也切掉
        base_title = re.split(r'[_局部.]', filename)[0]
        
        # 2. 获取该作品的标准事实
        if base_title not in fact_cache:
            fact_cache[base_title] = get_ground_truth(base_title)
        
        truth = fact_cache.get(base_title)
        if not truth:
            print(f"   无法获取《{base_title}》的背景信息，跳过。")
            continue

        # 3. 定位数据库节点
        node = matcher.match("Artwork", image_filename=filename).first()
        if not node:
            print(f"   数据库无此节点: {filename}")
            continue

        # 4. 调用视觉模型（不再问他是谁，而是命令它描述细节）
        img_path = os.path.abspath(os.path.join(IMAGE_DIR, filename))
        prompt = (
            f"这张图片确认为名作《{base_title}》的局部，作者是{truth['author']}（{truth['dynasty']}）。"
            "请根据此事实，仅描述该局部画面的内容（如山石、树木、色彩、意境），"
            "严格按 JSON 格式返回：{'detail': '...'}. 禁止修改作者和朝代信息。"
        )

        print(f" 正在标注: {filename}")
        try:
            res_vl = MultiModalConversation.call(
                model='qwen-vl-plus',
                messages=[{"role": "user", "content": [
                    {"image": f"file://{img_path}"},
                    {"text": prompt}
                ]}]
            )

            if res_vl.status_code == 200:
                text_result = res_vl.output.choices[0].message.content[0]['text']
                match = re.search(r'\{.*\}', text_result, re.DOTALL)
                if match:
                    vl_data = json.loads(match.group().replace("'", '"'))
                    
                    # 【核心修正】强制使用从文本模型查来的“真相”
                    node['author'] = truth['author']
                    node['dynasty'] = truth['dynasty']
                    node['style'] = truth['style']
                    node['info'] = vl_data.get('detail', '')
                    node['status'] = "Verified"
                    
                    graph.push(node)
                    print(f"   完美标注: [{node['author']}] - {filename}")
            else:
                print(f"  视觉识别报错: {res_vl.message}")
        except Exception as e:
            print(f"   异常: {e}")

if __name__ == "__main__":
    master_sync_pipeline_v2()