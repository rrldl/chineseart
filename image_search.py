# -*- coding: utf-8 -*-
"""
image_search.py - 修复打印问题的版本
"""
import os
import numpy as np
from PIL import Image
import torch
import datetime
from transformers import CLIPProcessor, CLIPModel
from py2neo import Graph, NodeMatcher

# ==========================================
# 配置
# ==========================================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Zyr123456"  # 改成你的密码

# 加载预训练的 CLIP 模型
MODEL_NAME = "openai/clip-vit-base-patch32"


# ==========================================
# 初始化 (模型和数据库)
# ==========================================
def initialize_model():
    """安全地初始化模型"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"正在加载模型: {MODEL_NAME}")
    print(f"使用设备: {device}")

    # 尝试多种加载方式
    model = None
    try:
        # 方法1：尝试使用 safetensors
        model = CLIPModel.from_pretrained(MODEL_NAME, use_safetensors=True).to(device)
        print("使用 safetensors 加载成功")
    except Exception as e1:
        print(f"使用 safetensors 失败: {e1}")
        try:
            # 方法2：尝试传统方式（可能需要 torch>=2.6）
            model = CLIPModel.from_pretrained(MODEL_NAME, use_safetensors=False).to(device)
            print("使用传统方式加载成功")
        except Exception as e2:
            print(f"传统方式加载失败: {e2}")
            try:
                # 方法3：尝试离线模式（如果之前下载过）
                model = CLIPModel.from_pretrained(MODEL_NAME, local_files_only=True).to(device)
                print("使用离线模式加载成功")
            except Exception as e3:
                print(f"所有加载方式都失败: {e3}")
                return None, None

    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return model, processor, device


# 初始化
model, processor, device = initialize_model()
if model is None:
    print("模型加载失败，请尝试升级 PyTorch 或检查网络连接")
    print("运行: pip install torch==2.6.0 torchvision==0.19.0")
    exit(1)

# 连接数据库
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
matcher = NodeMatcher(graph)


def extract_image_embedding(image_path):
    """
    输入本地图片路径，输出 CLIP 特征向量
    """
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = model.get_image_features(**inputs)

        # 归一化
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        return image_features.cpu().numpy()[0]  # 返回 numpy 数组
    except Exception as e:
        print(f"特征提取失败: {e}")
        return None


def search_similar_images(query_embedding, search_label="Artwork", top_k=5):
    """
    在图数据库中搜索最相似的图片。
    """
    results = []

    # 获取数据库中所有指定类型的节点
    nodes = matcher.match(search_label)

    print(f"正在搜索 {search_label} 节点... 共找到 {len(list(nodes))} 个节点")

    # 需要重新获取迭代器
    nodes = matcher.match(search_label)
    for node in nodes:
        # 检查节点是否有图片特征
        if 'image_embedding' in node:
            # 将数据库里的列表转为 numpy 数组
            db_embedding = np.array(node['image_embedding'])

            # 计算余弦相似度
            similarity = np.dot(query_embedding, db_embedding)

            # 创建结果字典
            result_item = {
                'similarity': float(similarity),
                'node': node
            }

            # 根据不同节点类型添加额外信息
            if search_label == "Artwork":
                result_item['title'] = node.get('title', '未知标题')
                result_item['type'] = '画作'
                result_item['author'] = node.get('author', '未知作者')
            elif search_label == "Seal":
                result_item['title'] = node.get('text', node.get('name', '无文'))
                result_item['type'] = '印章'
                result_item['owner'] = node.get('owner', '未知藏家')
            elif search_label == "Inscription":
                result_item['title'] = f"{node.get('author', '佚名')} - {node.get('type', '')}"
                result_item['type'] = '题跋'
                result_item['author'] = node.get('author', '佚名')

            results.append(result_item)

    # 按相似度排序 (从高到低)
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]


def print_results(results, label):
    """打印搜索结果"""
    print(f"\n=== {label} ===")
    print("=" * 50)

    if not results:
        print("未找到匹配结果")
        return

    for i, item in enumerate(results):
        similarity = item['similarity']

        if '画作' in label:
            title = item.get('title', '未知标题')
            author = item.get('author', '未知作者')
            print(f"{i + 1}. 《{title}》 - {author}")
            print(f"   相似度: {similarity:.4f}")

        elif '印章' in label:
            title = item.get('title', '无文')
            owner = item.get('owner', '未知藏家')
            print(f"{i + 1}. {owner} 的印章")
            print(f"   印文: {title}")
            print(f"   相似度: {similarity:.4f}")

        elif '题跋' in label:
            author = item.get('author', '佚名')
            title = item.get('title', '未知题跋')
            print(f"{i + 1}. {author} 的题跋")
            print(f"   类型: {title}")
            print(f"   相似度: {similarity:.4f}")

        print("-" * 30)


def print_summary(artworks, seals, inscriptions):
    """打印汇总信息"""
    print("\n" + "=" * 60)
    print("搜索结果汇总")
    print("=" * 60)

    if artworks:
        best_artwork = artworks[0]
        print(f"最相似的画作: 《{best_artwork.get('title', '未知')}》 (相似度: {best_artwork['similarity']:.4f})")

    if seals:
        best_seal = seals[0]
        print(
            f"最相似的印章: {best_seal.get('owner', '未知')} - {best_seal.get('title', '无文')} (相似度: {best_seal['similarity']:.4f})")

    if inscriptions:
        best_inscription = inscriptions[0]
        print(
            f"最相似的题跋: {best_inscription.get('author', '佚名')} - {best_inscription.get('title', '未知')} (相似度: {best_inscription['similarity']:.4f})")

    print(f"\n总计找到: {len(artworks)} 个画作, {len(seals)} 个印章, {len(inscriptions)} 个题跋")


# ==========================================
# 测试运行
# ==========================================
if __name__ == "__main__":
    # 测试图片路径 - 可以修改成你自己的图片
    test_images = [
        "test_query.jpg",
        "query.jpg",
        "test.jpg",
        "test_image.jpg"
    ]

    query_image_path = None
    for img_path in test_images:
        if os.path.exists(img_path):
            query_image_path = img_path
            break

    if query_image_path is None:
        print("请准备一张测试图片（如 test_query.jpg）或指定图片路径")
        user_path = input("请输入图片路径: ").strip()
        if os.path.exists(user_path):
            query_image_path = user_path
        else:
            print("图片不存在，程序退出")
            exit(1)

    print(f"正在处理查询图片: {query_image_path}")

    # 提取特征
    query_emb = extract_image_embedding(query_image_path)

    if query_emb is not None:
        print(f"特征提取成功，向量维度: {query_emb.shape}")

        # 搜索画作
        print("\n" + "=" * 60)
        print("开始搜索画作...")
        artworks = search_similar_images(query_emb, search_label="Artwork", top_k=5)
        print_results(artworks, "最相似的画作 (前5名)")

        # 搜索印章
        print("\n" + "=" * 60)
        print("开始搜索印章...")
        seals = search_similar_images(query_emb, search_label="Seal", top_k=5)
        print_results(seals, "最相似的印章 (前5名)")

        # 搜索题跋
        print("\n" + "=" * 60)
        print("开始搜索题跋...")
        inscriptions = search_similar_images(query_emb, search_label="Inscription", top_k=5)
        print_results(inscriptions, "最相似的题跋 (前5名)")

        # 打印汇总
        print_summary(artworks, seals, inscriptions)

        # 保存结果到文件（可选）
        save_to_file = input("\n是否保存结果到文件？(y/n): ")
        if save_to_file.lower() == 'y':
            import json

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.json"

            results = {
                'query_image': query_image_path,
                'artworks': artworks,
                'seals': seals,
                'inscriptions': inscriptions,
                'timestamp': timestamp
            }


            # 转换节点对象为可序列化的字典
            def node_to_dict(node):
                return dict(node)


            for category in ['artworks', 'seals', 'inscriptions']:
                for i, item in enumerate(results[category]):
                    if 'node' in item:
                        results[category][i]['node'] = dict(item['node'])

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到 {filename}")

    else:
        print("特征提取失败")