# -*- coding: utf-8 -*-
"""
align_images_to_kg.py
功能：遍历 artwork_images 文件夹，提取图片特征，并与 Neo4j 中的节点建立对齐关系。
依赖：请先运行 pip install torch torchvision transformers pillow py2neo
"""

import os
import json
import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from py2neo import Graph, NodeMatcher

# ==========================================
# 配置区 (请根据你的实际情况修改)
# ==========================================

# 1. 数据路径
JSON_PATH = "golden_dataset.json"  # 你的数据集路径
IMAGE_ROOT = "artwork_images"  # 图片根目录

# 2. Neo4j 数据库连接 (TODO: 修改这里)
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Zyr123456"  # TODO: 改成你的密码

# 3. 模型选择
MODEL_NAME = "openai/clip-vit-base-patch32"  # 通用，下载快

# ==========================================
# 初始化
# ==========================================

# 连接 Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
matcher = NodeMatcher(graph)

# 加载 CLIP 模型
print(f"正在加载模型 {MODEL_NAME} ...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用设备: {device}")

# 尝试使用 safetensors，如果不行则回退到传统方式
try:
    model = CLIPModel.from_pretrained(MODEL_NAME, use_safetensors=True).to(device)
except:
    print("无法使用 safetensors，正在尝试传统加载方式...")
    model = CLIPModel.from_pretrained(MODEL_NAME, use_safetensors=False).to(device)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)


# ==========================================
# 核心函数 (已修复)
# ==========================================

def encode_image(image_path):
    """
    输入图片路径，输出特征向量 (512维)
    """
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = model.get_image_features(**inputs)

        # 归一化
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        return image_features.cpu().numpy()[0].tolist()  # 转为 list
    except Exception as e:
        print(f"编码失败 {image_path}: {e}")
        return None


def find_image_file(base_dir, sub_folder, base_filename):
    """
    在指定目录下查找文件。
    1. 自动去除文件名中的括号内容（解决“册页”、“局部”问题）。
    2. 自动尝试多种后缀。
    3. 严格检查是否为文件。
    """
    # 定义搜索目录
    search_dir = os.path.join(base_dir, sub_folder)
    if not os.path.exists(search_dir):
        return None

    # 定义可能的文件名变体
    possible_names = []

    # 变体1: 原始文件名
    possible_names.append(base_filename)

    # 变体2: 去掉中文括号及其后内容
    clean_name_cn = base_filename.split('（')[0]
    if clean_name_cn != base_filename:
        possible_names.append(clean_name_cn)

    # 变体3: 去掉英文括号及其后内容
    clean_name_en = base_filename.split('(')[0]
    if clean_name_en != base_filename and clean_name_en not in possible_names:
        possible_names.append(clean_name_en)

    # 定义可能的后缀
    extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']

    # 遍历所有组合进行查找
    for name in possible_names:
        # 跳过空名字
        if not name or name.strip() == "":
            continue

        for ext in extensions:
            # 拼接完整文件路径
            full_path = os.path.join(search_dir, name + ext)

            # 检查文件是否存在 且 是一个文件
            if os.path.isfile(full_path):
                return full_path

    return None


# ==========================================
# 主程序 (已修改匹配逻辑)
# ==========================================

def main():
    # 调试：打印当前目录和文件列表
    print("当前工作目录:", os.getcwd())
    artwork_dir = os.path.join(IMAGE_ROOT, "artworks")
    if os.path.exists(artwork_dir):
        print("artworks 目录下的文件列表:")
        print(os.listdir(artwork_dir))
    else:
        print(f"错误：找不到目录 {artwork_dir}")
        return

    if not os.path.exists(JSON_PATH):
        print(f"错误：找不到数据集 {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n开始对齐图片与知识图谱...")

    for item in data:
        title = item["title"]
        print(f"\n处理画作: {title}")

        # --------------------------------------------------
        # 1. 对齐主图 (Artwork)
        # --------------------------------------------------
        artwork_img_path = find_image_file(IMAGE_ROOT, "artworks", title)
        if artwork_img_path:
            embedding = encode_image(artwork_img_path)
            if embedding:
                # 查找 Artwork 节点
                node = matcher.match("Artwork", title=title).first()
                if node:
                    node["image_embedding"] = embedding
                    graph.push(node)
                    print(f"  ✓ 主图对齐成功: {os.path.basename(artwork_img_path)}")
                else:
                    print(f"  ⚠ 未找到 Artwork 节点: {title}")
        else:
            print(f"  ⚠ 未找到主图文件: {title}")

        # --------------------------------------------------
        # 2. 对齐题跋 (Inscriptions)
        # --------------------------------------------------
        for ins in item.get("inscriptions", []):
            author = ins["author"]
            ins_type = ins["type"]
            filename = f"{title}_{author}_{ins_type}"
            ins_path = find_image_file(IMAGE_ROOT, "inscriptions", filename)

            if ins_path:
                print(f"    处理题跋文件: {os.path.basename(ins_path)}")
                embedding = encode_image(ins_path)
                if embedding:
                    node = None

                    # 策略1: 通过 unique_id 查找
                    # 从你的数据看，unique_id 是 "墨竹图_郑燮_题诗" 格式
                    unique_id = f"{title}_{author}_{ins_type}"
                    node = matcher.match("Inscription", unique_id=unique_id).first()
                    if node:
                        print(f"    通过 unique_id 找到节点: {unique_id}")

                    # 策略2: 通过 author + type 查找
                    if not node:
                        # 使用 Cypher 查询更可靠
                        query = f"""
                        MATCH (i:Inscription)
                        WHERE i.author = '{author}' AND i.type = '{ins_type}'
                        RETURN i
                        LIMIT 1
                        """
                        result = graph.run(query).data()
                        if result:
                            node = result[0]['i']
                            print(f"    通过 author+type 找到节点: {author} - {ins_type}")

                    # 策略3: 只按 type 查找一个未使用的节点
                    if not node:
                        query = f"""
                        MATCH (i:Inscription {{type: '{ins_type}'}})
                        WHERE NOT EXISTS(i.image_embedding)
                        RETURN i
                        LIMIT 1
                        """
                        result = graph.run(query).data()
                        if result:
                            node = result[0]['i']
                            print(f"    找到未使用的 {ins_type} 类型节点")

                    # 策略4: 随便找一个 type 匹配的节点
                    if not node:
                        query = f"""
                        MATCH (i:Inscription {{type: '{ins_type}'}})
                        RETURN i
                        LIMIT 1
                        """
                        result = graph.run(query).data()
                        if result:
                            node = result[0]['i']
                            print(f"    找到任意 {ins_type} 类型节点")

                    if node:
                        # 确保节点属性正确
                        if not node.get('author') or node['author'] != author:
                            node['author'] = author
                            print(f"    更新节点 author: {author}")
                        if not node.get('unique_id'):
                            node['unique_id'] = unique_id

                        node["image_embedding"] = embedding
                        graph.push(node)
                        print(f"  ✓ 题跋对齐成功: {os.path.basename(ins_path)}")
                    else:
                        print(f"  ⚠ 未找到 Inscription 节点: {author} - {ins_type}")
            else:
                print(f"  ⚠ 未找到题跋文件: {filename}")
        # --------------------------------------------------
        # 3. 对齐印章 (Seals) - 核心修改区
        # --------------------------------------------------
        for seal in item.get("seals", []):
            owner = seal["owner"]
            text = seal["text"]
            # 印章文件名：title_owner_text
            filename = f"{title}_{owner}_{text}"
            seal_path = find_image_file(IMAGE_ROOT, "seals", filename)

            if seal_path:
                embedding = encode_image(seal_path)
                if embedding:
                    # 尝试按 owner 和 text 查找
                    node = matcher.match("Seal").where(f"_.owner='{owner}' AND _.text='{text}'").first()

                    # 如果没找到，尝试只按 text 查找
                    if not node:
                        node = matcher.match("Seal", text=text).first()

                    # 如果还没找到，尝试 name 属性
                    if not node:
                        node = matcher.match("Seal", name=text).first()

                    if node:
                        node["image_embedding"] = embedding
                        graph.push(node)
                        print(f"  ✓ 印章对齐成功: {os.path.basename(seal_path)}")
                    else:
                        print(f"  ⚠ 未找到 Seal 节点: owner={owner}, text={text}")
            else:
                print(f"  ⚠ 未找到印章文件: {filename}")

print("\n所有图片对齐完成！")

if __name__ == "__main__":
    main()