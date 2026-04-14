import os
import json
import re
from py2neo import Graph, Node, Relationship, NodeMatcher
from dotenv import load_dotenv

# - id : 唯一标识。
# - title : 作品名称。
# - author : 作者名。
# - dynasty : 朝代。
# - style : 风格流派。
# - description : 所有作品均有此项 （217张图初始值为空，112张图来自 JSON 描述）。
# - image_filename : 文件名。
# - image_path : 绝对路径。
# - source : 来源标记。

# --- 1. 初始化 ---
load_dotenv()
graph = Graph(os.getenv("NEO4J_URI", "bolt://localhost:7687"), 
              auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")))
matcher = NodeMatcher(graph)

# 路径定义
DIR1 = r'F:\Chineseart\artwork_images\artworks'  # 217张图
DIR2 = r'F:\Chineseart\artworks'                 # 112张图
JSON1 = 'golden_dataset.json'
JSON2 = r'f:\Chineseart\detail_json\works_details_artworks_cleaned.json'
JSON3 = r'f:\Chineseart\detail_json\artists_works_cleaned.json'

def clean_database():
    print("正在清理现有 Artwork 节点及其关系...")
    graph.run("MATCH (a:Artwork) DETACH DELETE a")
    print("清理完成。")

def load_metadata():
    # 仅加载 112 张图需要的详细 JSON
    meta_details = {}
    if os.path.exists(JSON2):
        with open(JSON2, 'r', encoding='utf-8') as f:
            meta_details = json.load(f)
    return meta_details

def get_or_create_artist(name):
    if not name or name == "未知":
        return None
    artist = matcher.match("Artist", name=name).first()
    if not artist:
        artist = Node("Artist", name=name)
        graph.create(artist)
    return artist

def get_or_create_dynasty(name):
    if not name or name == "未知":
        return None
    dynasty = matcher.match("Dynasty", name=name).first()
    if not dynasty:
        dynasty = Node("Dynasty", name=name)
        graph.create(dynasty)
    return dynasty

def get_ground_truth(title):
    """
    完全复刻 sync_all_images.py 的核心逻辑：
    利用文本大模型查明历史真相
    """
    import dashscope
    from dashscope import Generation
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    
    print(f"   [知识锚定] 正在检索《{title}》的历史真实背景...")
    prompt = f"中国名画《{title}》公认的作者是谁？属于哪个朝代？艺术流派是什么？请严谨回答，仅以JSON格式返回，禁止任何废话：{{'author': '...', 'dynasty': '...', 'style': '...'}}"
    
    try:
        response = Generation.call(model='qwen-plus', prompt=prompt)
        if response.status_code == 200:
            res_text = response.output.text
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if match:
                return json.loads(match.group().replace("'", '"'))
    except Exception as e:
        print(f"   检索失败: {e}")
    return None

def import_from_dir1():
    print(f"正在从 {DIR1} 导入 (217张) - 模式：sync_all_images 逻辑...")
    files = [f for f in os.listdir(DIR1) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    count = 0
    fact_cache = {}

    for filename in files:
        base_title = re.split(r'[_局部.]', filename)[0]
        
        # 获取作品的标准事实 (sync_all_images.py 核心逻辑)
        if base_title not in fact_cache:
            fact_cache[base_title] = get_ground_truth(base_title)
        
        truth = fact_cache.get(base_title) or {
            'author': '未知',
            'dynasty': '未知',
            'style': '未知'
        }

        # 生成 ID
        import hashlib
        artwork_id = "art_" + hashlib.md5(base_title.encode('utf-8')).hexdigest()[:12]

        artwork_node = Node(
            "Artwork",
            id=artwork_id,
            title=base_title,
            author=truth.get('author', '未知'),
            dynasty=truth.get('dynasty', '未知'),
            style=truth.get('style', '未知'),
            description="", # 统一补上描述属性，初始为空
            image_filename=filename,
            image_path=os.path.join(DIR1, filename),
            source="sync_all_images_pipeline"
        )
        graph.create(artwork_node)
        
        # 建立关系 (Artist & Dynasty)
        if truth.get('author') and truth['author'] != '未知':
            artist_node = get_or_create_artist(truth['author'])
            if artist_node:
                graph.merge(Relationship(artwork_node, "CREATED_BY", artist_node))
        
        if truth.get('dynasty') and truth['dynasty'] != '未知':
            dynasty_node = get_or_create_dynasty(truth['dynasty'])
            if dynasty_node:
                graph.merge(Relationship(artwork_node, "PART_OF", dynasty_node))
        
        count += 1
    print(f"目录1导入完成，共 {count} 个节点。")

def import_from_dir2(meta_details):
    print(f"正在从 {DIR2} 导入 (112张) - 模式：ID 精确匹配 (已统一属性)...")
    files = [f for f in os.listdir(DIR2) if f.lower().endswith(('.bmp', '.jpg', '.png'))]
    count = 0
    for filename in files:
        artwork_id = filename.split('_')[0]
        info_wrapper = meta_details.get(artwork_id, {})
        suha = info_wrapper.get("suha", {})
        
        # 统一属性结构
        artwork_node = Node(
            "Artwork",
            id=artwork_id,
            title=suha.get("name", "未命名"),
            author=suha.get("author", "未知"),
            dynasty=suha.get("age", "未知"),
            style=suha.get("styleType", "未知"), # 将 styleType 映射为 style 属性
            description=suha.get("desc", ""),
            image_filename=filename,
            image_path=os.path.join(DIR2, filename),
            source="folder_2_cleaned"
        )
        graph.create(artwork_node)
        
        # 建立关系
        author_name = suha.get("author")
        if author_name and author_name != "未知":
            artist_node = get_or_create_artist(author_name)
            if artist_node:
                graph.merge(Relationship(artwork_node, "CREATED_BY", artist_node))
        
        dynasty_name = suha.get("age")
        if dynasty_name and dynasty_name != "未知":
            dynasty_node = get_or_create_dynasty(dynasty_name)
            if dynasty_node:
                graph.merge(Relationship(artwork_node, "PART_OF", dynasty_node))
        
        count += 1
    print(f"目录2导入完成，共 {count} 个节点。")

def verify():
    count = graph.evaluate("MATCH (a:Artwork) RETURN count(a)")
    print(f"数据库中最终 Artwork 节点总数: {count} (预期: 329)")
    return count

if __name__ == "__main__":
    try:
        clean_database()
        m_details = load_metadata()
        import_from_dir1()
        import_from_dir2(m_details)
        final_count = verify()
        print(f"导入完成！当前 Artwork 总数: {final_count}")
    except Exception as e:
        print(f"发生错误: {e}")
