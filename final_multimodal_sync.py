import os
import time
import numpy as np
import dashscope
from dashscope import MultiModalEmbedding
from py2neo import Graph, Node, Relationship
from dotenv import load_dotenv
from PIL import Image
import tempfile

# --- 1. 初始化配置 ---
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

def get_safe_image(image_path):
    """【增强版】处理图片：压缩 BMP 或大图，确保绝对低于 3MB"""
    try:
        file_size = os.path.getsize(image_path)
        # 阿里云限制是 3072KB，我们设为 2500KB (2.5MB) 留出安全余量
        limit = 2.5 * 1024 * 1024 
        
        # 只要是 BMP 或者 大于 2.5MB，就压缩
        if image_path.lower().endswith('.bmp') or file_size > limit:
            with Image.open(image_path) as img:
                rgb_img = img.convert('RGB')
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                temp_path = temp_file.name
                temp_file.close()
                
                # 调低 quality 到 75，并开启 optimize 压缩
                rgb_img.save(temp_path, 'JPEG', quality=75, optimize=True)
                
                # 二次检查压缩后的大小，如果还是大，就再压一次
                if os.path.getsize(temp_path) > 3 * 1024 * 1024:
                    rgb_img.save(temp_path, 'JPEG', quality=50, optimize=True)
                
                return temp_path, True
        return image_path, False
    except Exception as e:
        print(f"  ⚠️ 图片处理失败: {image_path}, 错误: {e}")
        return None, False
def construct_text_input(node, label):
    """根据标签动态拼接语义描述"""
    if label == 'Artwork':
        title = node.get('original_title') or node.get('title') or "未命名画作"
        return f"画作名称：{title}。作者：{node.get('author', '佚名')}。年代：{node.get('dynasty', '未知')}。描述：{node.get('description', '')}"
    
    elif label == 'Seal':
        return f"印章名称：{node.get('name', '')}。印文内容：{node.get('content', '')}。作者：{node.get('artist', '佚名')}。风格：{node.get('style', '')}。描述：{node.get('description', '')}"
    
    elif label == 'Inscription':
        return f"书法题跋：{node.get('name', '')}。作者：{node.get('artist', '佚名')}。年代：{node.get('dynasty', '未知')}。描述：{node.get('description', '')}"
    
    elif label == 'ArtistPortrait':
        return f"艺术家画像：{node.get('name', '')}。姓名：{node.get('artist_name', '未知')}。背景：{node.get('description', '')}"
    
    return node.get('description', '')

def run_master_sync():
    # 1. 查找所有未同步的节点（支持四种标签）
    query = """
    MATCH (n)
    WHERE (n:Artwork OR n:Seal OR n:Inscription OR n:ArtistPortrait)
      AND NOT (n)-[:hasAlignment]->(:AlignmentNode)
    RETURN id(n) as internal_id, labels(n)[0] as label, n
    """
    pending_nodes = graph.run(query).data()
    total = len(pending_nodes)
    print(f"🚀 发现 {total} 个待同步节点。开始马拉松同步...")
    # --- 新增：限制印章数量的计数器 ---
    SEAL_LIMIT = 1000  # 每次只跑 1000 张印章
    seal_count = 0
    if total == 0:
        print("✅ 所有节点已对齐，无需运行。")
        return

    # 准备本地索引缓存
    all_embeddings = []
    all_metadata = []

    for i, row in enumerate(pending_nodes):
        node = row['n']
        label = row['label']
        internal_id = row['internal_id']

        if label == 'Seal':
            if seal_count >= SEAL_LIMIT:
                continue # 跳过这张印章，去处理下一条（可能是画像或题跋）
            seal_count += 1
        
        # 路径兼容处理 (如果你还没运行 Cypher 改名，这里做了二次保险)
        img_path = node.get('path') or node.get('image_path')
        
        if not img_path or not os.path.exists(img_path):
            print(f"  [{i+1}/{total}] ❌ 跳过：找不到路径 {img_path}")
            continue

        # 构造文本语义
        text_input = construct_text_input(node, label)
        
        # 处理图片
        processed_path, is_temp = get_safe_image(img_path)
        if not processed_path: continue

        # 调用 API (带重试机制)
        success = False
        for attempt in range(3):
            try:
                # 核心：图片 + 文本 双模态输入
                res = MultiModalEmbedding.call(
                    model='multimodal-embedding-v1',
                    input=[
                        {'image': f"file://{os.path.abspath(processed_path)}"},
                        {'text': text_input[:500]} # 限制文本长度防止超限
                    ]
                )
                if res.status_code == 200:
                    embedding = res.output['embeddings'][0]['embedding']
                    success = True
                    break
                else:
                    print(f"  retry {attempt+1}: {res.message}")
                    time.sleep(2)
            except Exception as e:
                print(f"  error {attempt+1}: {e}")
                time.sleep(2)

        # 写入 Neo4j
        if success:
            # 创建对齐节点
            sync_query = """
            MATCH (n) WHERE id(n) = $int_id
            CREATE (al:AlignmentNode {
                id: 'align_' + $int_id,
                label: $label,
                embedding: $emb
            })
            CREATE (n)-[:hasAlignment]->(al)
            """
            graph.run(sync_query, int_id=internal_id, label=label, emb=embedding)
            
            # 记录到本地缓存
            all_embeddings.append(embedding)
            all_metadata.append({
                "internal_id": internal_id,
                "label": label,
                "name": node.get('name') or node.get('original_title') or "未知"
            })
            
            print(f"  [{i+1}/{total}] ✅ 同步成功: {label} - {node.get('name', '未命名')}")
        else:
            print(f"  [{i+1}/{total}] ❌ 彻底失败，跳过。")

        # 清理临时文件
        if is_temp and os.path.exists(processed_path):
            os.remove(processed_path)

        # 频率控制（根据阿里云 QPS 限制）
        time.sleep(0.4)

    # 3. 保存本地索引文件 (用于极速搜索)
    if all_embeddings:
        os.makedirs("./data/vector_index", exist_ok=True)
        # 如果以前有文件，可以考虑合并或覆盖。这里建议覆盖，因为我们要的是全库最新。
        np.save("./data/vector_index/embeddings.npy", np.array(all_embeddings))
        np.save("./data/vector_index/metadata.npy", np.array(all_metadata, dtype=object))
        print(f"\n🎊 同步完成！本地索引已更新，共包含 {len(all_embeddings)} 个节点。")

if __name__ == "__main__":
    # 提醒：运行前确保已经清空了旧的对齐节点
    # MATCH (al:AlignmentNode) DETACH DELETE al
    run_master_sync()