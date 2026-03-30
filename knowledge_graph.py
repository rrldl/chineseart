#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识图谱模块 - 实现多模态知识存储与融合
"""
import os
import json
import requests
from py2neo import Graph, Node, Relationship
import numpy as np

class KnowledgeGraphManager:
    """知识图谱管理器"""

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        """
        初始化知识图谱管理器
        
        Args:
            neo4j_uri: Neo4j数据库连接地址
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        # 连接Neo4j数据库
        self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # 确保必要的目录存在
        os.makedirs("./data/knowledge_graph", exist_ok=True)
        os.makedirs("./data/extracted_triples", exist_ok=True)
        os.makedirs("./data/vector_index", exist_ok=True)

    def build_ontology(self):
        """
        构建书画领域本体
        
        Returns:
            dict: 本体结构
        """
        print("正在构建书画领域本体...")
        
        # 定义核心实体类型
        entity_types = [
            "Artwork",      # 艺术品
            "Artist",       # 艺术家
            "Dynasty",      # 朝代
            "Style",        # 艺术风格
            "HistoricalEvent",  # 历史事件
            "Collection",   # 馆藏机构
            "Seal",         # 印章
            "Inscription",  # 题跋
            "Person"        # 人物
        ]
        
        # 定义关系类型
        relationship_types = [
            "CREATED_BY",       # 作品由谁创作
            "PART_OF",          # 作品属于哪个朝代
            "LIVED_IN",         # 艺术家生活在哪个朝代
            "HAS_STYLE",        # 作品具有什么风格
            "INFLUENCED_BY",    # 艺术家受谁影响
            "INFLUENCED",       # 艺术家影响了谁
            "STORED_IN",        # 作品收藏在哪个机构
            "HAS_SEAL",         # 作品包含什么印章
            "HAS_INSCRIPTION",  # 作品包含什么题跋
            "OWNED_BY",         # 印章由谁拥有
            "WRITTEN_BY",       # 题跋由谁撰写
            "RELATED_TO",       # 相关联
            "HAS_ALIGNMENT"     # 实体有对齐节点
        ]
        
        # 定义属性模板
        property_templates = {
            "Artwork": {
                "title": "string",
                "description": "string",
                "medium": "string",
                "date": "string",
                "dimensions": "object",
                "collection": "string",
                "style": "string",
                "image_url": "string"
            },
            "Artist": {
                "name": "string",
                "birth_year": "string",
                "death_year": "string",
                "style": "string",
                "description": "string",
                "era": "string"
            },
            "Dynasty": {
                "name": "string",
                "start_year": "string",
                "end_year": "string",
                "description": "string"
            },
            "Style": {
                "name": "string",
                "origin": "string",
                "characteristics": "list",
                "description": "string"
            },
            "HistoricalEvent": {
                "name": "string",
                "time": "string",
                "description": "string",
                "influence": "list"
            },
            "Collection": {
                "name": "string",
                "location": "string",
                "description": "string"
            },
            "Seal": {
                "text": "string",
                "owner": "string",
                "type": "string",
                "description": "string"
            },
            "Inscription": {
                "text": "string",
                "author": "string",
                "type": "string",
                "description": "string"
            },
            "Person": {
                "name": "string",
                "era": "string",
                "description": "string"
            }
        }
        
        # 保存本体结构
        ontology = {
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            "property_templates": property_templates
        }
        
        save_path = "./data/knowledge_graph/ontology.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(ontology, f, ensure_ascii=False, indent=2)
        
        print(f"本体结构已保存到: {save_path}")
        return ontology

    def extract_triples_with_llm(self, text, model="glm-4"):
        """
        使用大语言模型提取三元组
        
        Args:
            text: 文本内容
            model: 使用的模型
            
        Returns:
            list: 提取的三元组列表
        """
        print("正在使用大语言模型提取三元组...")
        
        # 构建提示词
        prompt = f"""
        你是一位书画专家，请从以下文本中抽取实体和关系，并以JSON格式输出三元组。
        
        文本：{text}
        
        输出格式：
        {{
          "triples": [
            {{
              "subject": "主语实体",
              "predicate": "关系",
              "object": "宾语实体"
            }}
          ]
        }}
        
        请严格按照此格式输出，不要添加任何解释。
        """
        
        # 调用Ollama API
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                
                json={
                    "model": "qwen2.5:7b",
                    # "model": model,
                    "prompt": prompt,
                    "stream": False
                    
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                
                # 解析JSON
                try:
                    triples_data = json.loads(content)
                    triples = triples_data.get("triples", [])
                    print(f"成功提取 {len(triples)} 个三元组")
                    return triples
                except json.JSONDecodeError:
                    print("提取结果解析失败")
                    return []
            else:
                print(f"API调用失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"提取三元组失败: {e}")
            return []

    def import_triples(self, triples):
        """
        导入三元组到知识图谱
        
        Args:
            triples: 三元组列表
            
        Returns:
            int: 成功导入的三元组数量
        """
        print(f"正在导入 {len(triples)} 个三元组到知识图谱...")
        
        count = 0
        
        for triple in triples:
            subject = triple.get("subject")
            predicate = triple.get("predicate")
            object_ = triple.get("object")
            
            if not all([subject, predicate, object_]):
                continue
            
            try:
                # 创建或合并节点
                subject_node = Node("Entity", name=subject)
                object_node = Node("Entity", name=object_)
                
                self.graph.merge(subject_node, "Entity", "name")
                self.graph.merge(object_node, "Entity", "name")
                
                # 创建关系
                rel = Relationship(subject_node, predicate, object_node)
                self.graph.merge(rel)
                
                count += 1
            except Exception as e:
                print(f"导入三元组失败: {e}")
                continue
        
        print(f"成功导入 {count} 个三元组")
        return count

    def build_vector_index(self):
        """
        构建向量索引
        
        Returns:
            dict: 索引信息
        """
        print("正在构建向量索引...")
        
        # 获取所有对齐节点
        query = """
        MATCH (a:AlignmentNode)
        RETURN a.id as id, a.entity_id as entity_id, a.entity_type as entity_type, 
               a.embedding as embedding
        """
        
        embeddings = []
        metadata = []
        
        for record in self.graph.run(query):
            embedding = np.array(record["embedding"])
            embeddings.append(embedding)
            metadata.append({
                "id": record["id"],
                "entity_id": record["entity_id"],
                "entity_type": record["entity_type"]
            })
        
        if embeddings:
            # 保存向量和元数据
            embeddings_array = np.array(embeddings)
            metadata_array = np.array(metadata, dtype=object)
            
            np.save("./data/vector_index/embeddings.npy", embeddings_array)
            np.save("./data/vector_index/metadata.npy", metadata_array)
            
            print(f"向量索引已构建，包含 {len(embeddings)} 个向量")
            
            return {
                "count": len(embeddings),
                "dimension": embeddings_array.shape[1],
                "path": "./data/vector_index/"
            }
        else:
            print("没有找到对齐节点，向量索引构建失败")
            return {}

    def search_similar_entities(self, query_embedding, top_k=5):
        """
        搜索相似实体
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            
        Returns:
            list: 相似实体列表
        """
        # 加载向量索引
        try:
            embeddings = np.load("./data/vector_index/embeddings.npy")
            metadata = np.load("./data/vector_index/metadata.npy", allow_pickle=True)
        except Exception as e:
            print(f"加载向量索引失败: {e}")
            return []
        
        # 计算相似度
        similarities = np.dot(embeddings, query_embedding)
        
        # 排序并返回Top K
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "metadata": metadata[idx],
                "similarity": float(similarities[idx])
            })
        
        return results

    def import_artwork_data(self, artwork_data):
        """
        导入艺术品数据
        
        Args:
            artwork_data: 艺术品数据
            
        Returns:
            bool: 是否导入成功
        """
        print(f"正在导入艺术品数据: {artwork_data.get('title')}")
        
        try:
            # 创建艺术品节点
            artwork_node = Node(
                "Artwork",
                title=artwork_data.get("title"),
                description=artwork_data.get("description", ""),
                medium=artwork_data.get("medium", ""),
                date=artwork_data.get("date", "")
            )
            self.graph.merge(artwork_node, "Artwork", "title")
            
            # 处理作者
            if author_name := artwork_data.get("author"):
                artist_node = Node("Artist", name=author_name)
                self.graph.merge(artist_node, "Artist", "name")
                rel = Relationship(artwork_node, "CREATED_BY", artist_node)
                self.graph.merge(rel)
            
            # 处理朝代
            if dynasty_name := artwork_data.get("dynasty"):
                dynasty_node = Node("Dynasty", name=dynasty_name)
                self.graph.merge(dynasty_node, "Dynasty", "name")
                rel = Relationship(artwork_node, "PART_OF", dynasty_node)
                self.graph.merge(rel)
                
                # 关联作者和朝代
                if author_name:
                    artist_node = Node("Artist", name=author_name)
                    self.graph.merge(artist_node, "Artist", "name")
                    rel = Relationship(artist_node, "LIVED_IN", dynasty_node)
                    self.graph.merge(rel)
            
            # 处理风格
            for style_name in artwork_data.get("style", []):
                style_node = Node("Style", name=style_name)
                self.graph.merge(style_node, "Style", "name")
                rel = Relationship(artwork_node, "HAS_STYLE", style_node)
                self.graph.merge(rel)
            
            # 处理馆藏
            for collection_name in artwork_data.get("collections", []):
                collection_node = Node("Collection", name=collection_name)
                self.graph.merge(collection_node, "Collection", "name")
                rel = Relationship(artwork_node, "STORED_IN", collection_node)
                self.graph.merge(rel)
            
            # 处理印章
            for seal_info in artwork_data.get("seals", []):
                seal_node = Node(
                    "Seal",
                    text=seal_info.get("text"),
                    owner=seal_info.get("owner"),
                    type=seal_info.get("type")
                )
                self.graph.merge(seal_node, "Seal", "text")
                rel = Relationship(artwork_node, "HAS_SEAL", seal_node)
                self.graph.merge(rel)
                
                # 关联印章所有者
                if owner_name := seal_info.get("owner"):
                    person_node = Node("Person", name=owner_name)
                    self.graph.merge(person_node, "Person", "name")
                    rel = Relationship(seal_node, "OWNED_BY", person_node)
                    self.graph.merge(rel)
            
            # 处理题跋
            for inscription_info in artwork_data.get("inscriptions", []):
                inscription_node = Node(
                    "Inscription",
                    text=inscription_info.get("text"),
                    author=inscription_info.get("author"),
                    type=inscription_info.get("type")
                )
                self.graph.merge(inscription_node, "Inscription", "text")
                rel = Relationship(artwork_node, "HAS_INSCRIPTION", inscription_node)
                self.graph.merge(rel)
                
                # 关联题跋作者
                if author_name := inscription_info.get("author"):
                    person_node = Node("Person", name=author_name)
                    self.graph.merge(person_node, "Person", "name")
                    rel = Relationship(inscription_node, "WRITTEN_BY", person_node)
                    self.graph.merge(rel)
            
            print(f"艺术品数据导入成功: {artwork_data.get('title')}")
            return True
        except Exception as e:
            print(f"导入艺术品数据失败: {e}")
            return False

    def get_graph_statistics(self):
        """
        获取知识图谱统计信息
        
        Returns:
            dict: 统计信息
        """
        print("正在获取知识图谱统计信息...")
        
        statistics = {}
        
        # 获取节点数量
        query = "MATCH (n) RETURN labels(n) as label, count(*) as count"
        node_counts = {}
        for record in self.graph.run(query):
            labels = record["label"]
            count = record["count"]
            for label in labels:
                node_counts[label] = node_counts.get(label, 0) + count
        statistics["node_counts"] = node_counts
        
        # 获取关系数量
        query = "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
        relationship_counts = {}
        for record in self.graph.run(query):
            rel_type = record["type"]
            count = record["count"]
            relationship_counts[rel_type] = count
        statistics["relationship_counts"] = relationship_counts
        
        # 获取总节点和关系数量
        statistics["total_nodes"] = sum(node_counts.values())
        statistics["total_relationships"] = sum(relationship_counts.values())
        
        print(f"知识图谱统计: {statistics['total_nodes']} 个节点, {statistics['total_relationships']} 个关系")
        
        return statistics

# 测试代码
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 初始化管理器
    manager = KnowledgeGraphManager(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "Zyr123456")
    )
    
    # 测试构建本体
    print("测试构建本体...")
    ontology = manager.build_ontology()
    print(f"本体包含 {len(ontology['entity_types'])} 个实体类型")
    
    # 测试提取三元组
    print("\n测试提取三元组...")
    test_text = "张择端是北宋末年画家，他的代表作品是《清明上河图》，描绘了北宋都城汴京的繁华景象。"
    triples = manager.extract_triples_with_llm(test_text)
    print(f"提取的三元组: {triples}")
    
    # 测试导入三元组
    if triples:
        print("\n测试导入三元组...")
        count = manager.import_triples(triples)
        print(f"成功导入 {count} 个三元组")
    
    # 测试获取统计信息
    print("\n测试获取统计信息...")
    stats = manager.get_graph_statistics()
    print(f"统计信息: {stats}")
