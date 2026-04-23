#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 这个脚本的功能是将 golden_dataset.json 中存储的中国古代书画作品数据，
# 导入到 Neo4j 图数据库中，构建一个知识图谱。
import json
import os
from dotenv import load_dotenv
from py2neo import Graph, Node, Relationship

# --- 1. 配置并连接到 Neo4j 数据库 ---
# (这部分与原脚本类似，确保您的 .env 文件配置正确)
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
if not NEO4J_PASSWORD:
    raise EnvironmentError("请在 .env 文件中设置 NEO4J_PASSWORD 环境变量。")

print("正在连接到 Neo4j 数据库...")
try:
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # 清空数据库，以便重新导入 (如果您想保留旧数据，请注释掉下面这行)
    print("正在清空现有数据库...")
    graph.delete_all()
    print("数据库已清空。")
except Exception as e:
    print(f"数据库连接失败，请检查配置或Neo4j服务状态: {e}")
    exit()
print("数据库连接成功！")

# --- 2. 读取您的中国古代书画JSON数据 ---
DATA_FILE = "golden_dataset.json"
print(f"正在读取数据文件: {DATA_FILE}...")
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"成功读取 {len(data)} 条数据。")
except FileNotFoundError:
    print(f"错误: 未找到数据文件 '{DATA_FILE}'。请确保它和脚本在同一目录下。")
    exit()
except json.JSONDecodeError:
    print(f"错误: '{DATA_FILE}' 文件格式不正确，请检查是否为标准的JSON格式。")
    exit()


# --- 3. 定义可复用的节点与关系创建函数 ---
def merge_unique_node(label, name_property, name_value, **properties):
    """
    一个更通用的节点合并函数。
    - label: 节点的标签 (e.g., "Artist")
    - name_property: 用于唯一标识节点的属性名 (e.g., "name")
    - name_value: 唯一标识节点的值 (e.g., "董其昌")
    """
    node = Node(label, **{name_property: name_value}, **properties)
    graph.merge(node, label, name_property)
    return node


def merge_unique_relationship(start_node, rel_type, end_node):
    """
    创建或合并一个唯一的关系，防止重复。
    """
    rel = Relationship(start_node, rel_type, end_node)
    graph.merge(rel)


# --- 4. 核心逻辑：遍历数据并构建知识图谱 ---
print("开始构建知识图谱...")
total_items = len(data)
for i, item in enumerate(data):
    artwork_title = item.get("title")
    if not artwork_title:
        print(f"警告: 第 {i + 1} 条数据缺少 'title'，已跳过。")
        continue

    print(f"  ({i + 1}/{total_items}) 正在处理作品: 《{artwork_title}》")

    # a. 创建核心节点：作品 (Artwork)
    artwork_props = {
        "description": item.get("description", ""),
        "medium": item.get("medium", ""),
        # 将维度信息扁平化存入属性，便于查询
        "height_cm": item.get("dimensions", {}).get("height_cm"),
        "width_cm": item.get("dimensions", {}).get("width_cm")
    }
    artwork_node = merge_unique_node("Artwork", "title", artwork_title, **artwork_props)

    # b. 作者 (Artist) 节点与关系
    if author_name := item.get("author"):
        artist_node = merge_unique_node("Artist", "name", author_name)
        merge_unique_relationship(artwork_node, "CREATED_BY", artist_node)

    # c. 朝代 (Dynasty) 节点与关系
    if dynasty_name := item.get("dynasty"):
        dynasty_node = merge_unique_node("Dynasty", "name", dynasty_name)
        merge_unique_relationship(artwork_node, "PART_OF", dynasty_node)
        # 额外建立“作者-朝代”的关联，丰富图谱信息
        if 'artist_node' in locals():
            merge_unique_relationship(artist_node, "LIVED_IN", dynasty_node)

    # d. 风格 (Style) 节点与关系
    for style_name in item.get("style", []):
        style_node = merge_unique_node("Style", "name", style_name)
        merge_unique_relationship(artwork_node, "HAS_STYLE", style_node)

    # e. 馆藏地 (Collection) 节点与关系
    for collection_name in item.get("collections", []):
        collection_node = merge_unique_node("Collection", "name", collection_name)
        merge_unique_relationship(artwork_node, "STORED_IN", collection_node)

    # f. 印章 (Seal) 及其所有者 (Owner) 的精细刻画
    for seal_info in item.get("seals", []):
        # 修复：包含 owner 属性
        seal_props = {
            "text": seal_info.get("text"),
            "type": seal_info.get("type"),
            "owner": seal_info.get("owner")  # 添加这一行
        }

        # 建议：将 unique_id 改为 "title_owner_text_type" 格式，以便后续识别
        # 这样即使 owner 属性为空，也能从 unique_id 中提取
        seal_unique_id = f"{artwork_title}_{seal_props['owner']}_{seal_props['text']}_{seal_props['type']}"

        seal_node = merge_unique_node("Seal", "unique_id", seal_unique_id, **seal_props)
        merge_unique_relationship(artwork_node, "HAS_SEAL", seal_node)

        if owner_name := seal_info.get("owner"):
            # 使用"Person"作为通用的人物节点，便于关联
            owner_node = merge_unique_node("Person", "name", owner_name)
            merge_unique_relationship(seal_node, "OWNED_BY", owner_node)
    # g. 题跋 (Inscription) 及其作者的精细刻画
    for inscription_info in item.get("inscriptions", []):
        inscription_props = {"text": inscription_info.get("text"), "type": inscription_info.get("type")}
        # 题跋内容可能很长，这里用“作品名+作者+类型”作为ID
        author_for_id = inscription_info.get('author', '未知')
        inscription_unique_id = f"{artwork_title}_{author_for_id}_{inscription_props['type']}"
        inscription_node = merge_unique_node("Inscription", "unique_id", inscription_unique_id, **inscription_props)
        merge_unique_relationship(artwork_node, "HAS_INSCRIPTION", inscription_node)

        if author_name := inscription_info.get("author"):
            author_node_ins = merge_unique_node("Person", "name", author_name)
            merge_unique_relationship(inscription_node, "WRITTEN_BY", author_node_ins)

print("\n知识图谱构建完成！")
print("您现在可以登录Neo4j Browser，使用Cypher查询来探索您的图谱。")
print("例如，尝试执行: MATCH (a:Artwork {title:'清明上河图'})-[r]->(b) RETURN a, r, b")
