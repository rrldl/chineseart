import json
from py2neo import Graph

# ================= 配置区 =================
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# 你的终极干净字典（记录了中文名和你的标准 ID 的对应关系）
# 例如: {"legacy0001": {"suha": {"name": "步辇图"}}, "608a...": {"suha": {"name": "千里江山图"}}}
CLEANED_JSON_PATH = r"D:\shuhua_picture\work\cleaned\works_details_artworks_cleaned.json"
# ==========================================

print("🔌 正在连接你同学那堆满脏数据的 Neo4j...")
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("📖 正在加载你的标准字典库...")
with open(CLEANED_JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 建立 中文名 -> 标准 ID 的快速映射表
# {'步辇图': 'legacy0001', '千里江山图': '608a123...'}
name_to_id_map = {}
if isinstance(data, dict):
    for k, v in data.items():
        suha = v.get('suha', v) if isinstance(v, dict) else v
        name = suha.get('name', '').strip()
        if name:
            name_to_id_map[name] = suha.get('Id', '').strip()
elif isinstance(data, list):
    for item in data:
        suha = item.get('suha', item) if isinstance(item, dict) else item
        name = suha.get('name', '').strip()
        if name:
            name_to_id_map[name] = suha.get('Id', '').strip()

print(f"✅ 成功提取了 {len(name_to_id_map)} 个标准画作映射关系。")

# ================= 开始实施换血手术 =================

print("\n🚀 开始重构 Artwork 节点...")

# 获取图谱中所有的 Artwork 节点
query_all = "MATCH (a:Artwork) RETURN id(a) AS internal_id, a.original_title AS old_name, a.title AS old_title"
results = graph.run(query_all).data()

updated_count = 0
deleted_count = 0

for res in results:
    internal_id = res['internal_id']
    
    # 尝试找出这幅画真正的中文名 (优先看 original_title，如果没有再从 "步辇图 (局部3)" 里抠)
    real_name = res.get('old_name')
    if not real_name:
        raw_title = res.get('old_title', '')
        real_name = raw_title.split('（')[0].split('(')[0].split('_')[0].strip()

    # 去我们的字典里查，这幅画的标准 ID 是什么？
    standard_id = name_to_id_map.get(real_name)
    
    if standard_id:
        # 找到了！执行神级洗髓替换
        # 1. 赋予标准 ID
        # 2. 扔掉垃圾属性 (path, source, image_filename, original_title)
        # 3. 将真正的名字赋给 title
        update_query = """
        MATCH (a:Artwork) WHERE id(a) = $internal_id
        SET a.id = $standard_id,
            a.title = $real_name
        REMOVE a.path, a.source, a.image_filename, a.original_title
        """
        graph.run(update_query, internal_id=internal_id, standard_id=standard_id, real_name=real_name)
        updated_count += 1
    else:
        # 如果图谱里有这幅画，但是你的标准 JSON 里没有，说明这是幽灵脏数据
        # 建议直接删掉，或者跳过 (这里做跳过处理并打印警告)
        print(f"⚠️ 警告：图谱中发现画作 '{real_name}'，但标准库中不存在对应 ID。")

print(f"\n🎉 Artwork 节点重构完毕！共清洗/对齐了 {updated_count} 个节点。")

# ================= 可选：清理孤儿节点 =================
# 因为你同学把局部图也建成了独立节点，经过上面的换血，现在会有多个 id 相同的 Artwork 节点。
# 在严格的图谱设计里，这叫数据冗余。你可以运行下面的 Cypher 去重合并它们。
print("🧹 正在合并重复的局部图节点 (将多个相同的 id 融合成一个纯净实体)...")
merge_query = """
MATCH (a:Artwork)
WITH a.id AS standard_id, collect(a) AS nodes
WHERE size(nodes) > 1
CALL apoc.refactor.mergeNodes(nodes, {properties:"overwrite", mergeRels:true})
YIELD node
RETURN count(*)
"""
try:
    graph.run(merge_query)
    print("✅ 重复节点融合成功！图谱已达到完美状态。")
except Exception as e:
    print(f"⚠️ 融合节点需要 APOC 插件支持。如果你没装 APOC，可以暂时忽略此步: {e}")