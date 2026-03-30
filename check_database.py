#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库连接和Artwork节点数量
"""

from py2neo import Graph, NodeMatcher
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接信息
neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "Zyr123456")

print("检查数据库连接...")
try:
    # 连接数据库
    graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
    print("✓ 数据库连接成功")
    
    # 测试连接
    result = graph.run("RETURN 1").data()
    print("✓ 数据库查询成功")
    
    # 检查Artwork节点数量
    matcher = NodeMatcher(graph)
    artwork_nodes = list(matcher.match("Artwork"))
    print(f"✓ 找到 {len(artwork_nodes)} 个 Artwork 节点")
    
    # 打印前5个Artwork节点的标题
    print("\n前5个Artwork节点:")
    for i, node in enumerate(artwork_nodes[:5]):
        title = node.get('title', '无标题')
        print(f"  {i+1}. {title}")
        
    # 检查是否有图片文件
    print("\n检查artwork_images目录:")
    if os.path.exists("artwork_images"):
        print("✓ artwork_images目录存在")
        if os.path.exists("artwork_images/artworks"):
            images = os.listdir("artwork_images/artworks")
            print(f"✓ 找到 {len(images)} 个图片文件")
            print("前5个图片文件:")
            for img in images[:5]:
                print(f"  - {img}")
        else:
            print("✗ artwork_images/artworks目录不存在")
    else:
        print("✗ artwork_images目录不存在")
        
except Exception as e:
    print(f"✗ 数据库连接失败: {e}")

print("\n检查完成")
