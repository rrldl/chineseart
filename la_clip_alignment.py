#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LA-CLIP对齐模块 - 实现多模态数据的细粒度语义对齐
"""
import os
import torch
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from py2neo import Graph, Node, Relationship

class LAClipAlignmentService:
    """LA-CLIP对齐服务类"""

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        """
        初始化LA-CLIP对齐服务
        
        Args:
            neo4j_uri: Neo4j数据库连接地址
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        # 连接Neo4j数据库
        self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # 加载CLIP模型
        self.model_name = "openai/clip-vit-base-patch32"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
        
        # 确保必要的目录存在
        os.makedirs("./data/alignment", exist_ok=True)
        os.makedirs("./data/embeddings", exist_ok=True)

    def _load_model(self):
        """加载CLIP模型"""
        print(f"正在加载CLIP模型: {self.model_name}")
        try:
            self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            print(f"✓ CLIP模型加载成功，使用设备: {self.device}")
        except Exception as e:
            print(f"✗ CLIP模型加载失败: {e}")
            raise

    def extract_image_features(self, image_path):
        """
        提取图像特征
        
        Args:
            image_path: 图像路径
            
        Returns:
            np.ndarray: 图像特征向量
        """
        try:
            from PIL import Image
            
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                features = self.model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            
            return features.cpu().numpy()[0]
        except Exception as e:
            print(f"图像特征提取失败: {e}")
            return None

    def extract_text_features(self, text):
        """
        提取文本特征
        
        Args:
            text: 文本内容
            
        Returns:
            np.ndarray: 文本特征向量
        """
        try:
            # 限制文本长度，确保不超过CLIP模型的最大序列长度
            if len(text) > 50:
                text = text[:50]
            
            inputs = self.processor(text=[text], return_tensors="pt").to(self.device)
            
            # 检查输入长度
            if inputs['input_ids'].shape[1] > 77:
                # 如果仍然超过限制，截断到75个token（留出空间给特殊标记）
                inputs['input_ids'] = inputs['input_ids'][:, :75]
                inputs['attention_mask'] = inputs['attention_mask'][:, :75]
            
            with torch.no_grad():
                features = self.model.get_text_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            
            return features.cpu().numpy()[0]
        except Exception as e:
            print(f"文本特征提取失败: {e}")
            return None

    def generate_alignment_node(self, entity_id, entity_type, multimodal_features):
        """
        生成对齐专用节点
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            multimodal_features: 多模态特征列表
            
        Returns:
            dict: 对齐节点信息
        """
        print(f"正在为实体 {entity_id} 生成对齐节点...")
        
        # 聚合多模态特征
        aggregated_features = self._aggregate_features(multimodal_features)
        
        # 生成对齐节点ID
        alignment_node_id = f"alignment_{entity_type}_{entity_id}"
        
        # 确保所有值都是Neo4j支持的类型
        # 将NumPy数组转换为Python列表，将NumPy浮点数转换为Python浮点数
        embedding_list = [float(val) for val in aggregated_features.tolist()]
        confidence = float(self._calculate_confidence(multimodal_features))
        consistency_score = float(self._calculate_consistency(multimodal_features))
        
        # 创建对齐节点
        alignment_node = Node(
            "AlignmentNode",
            id=alignment_node_id,
            entity_id=entity_id,
            entity_type=entity_type,
            embedding=embedding_list,
            confidence=confidence,
            consistency_score=consistency_score
        )
        
        # 保存到Neo4j
        self.graph.merge(alignment_node, "AlignmentNode", "id")
        
        # 构建与实体的关系
        if entity_type == "Artwork":
            entity = Node("Artwork", title=entity_id)
        elif entity_type == "Artist":
            entity = Node("Artist", name=entity_id)
        elif entity_type == "HistoricalEvent":
            entity = Node("HistoricalEvent", name=entity_id)
        elif entity_type == "Style":
            entity = Node("Style", name=entity_id)
        else:
            entity = Node(entity_type, name=entity_id)
        
        # 合并实体节点
        self.graph.merge(entity, entity_type, "name" if entity_type != "Artwork" else "title")
        
        # 创建hasAlignment关系
        rel = Relationship(entity, "hasAlignment", alignment_node)
        self.graph.merge(rel)
        
        print(f"对齐节点已创建: {alignment_node_id}")
        
        return {
            "alignment_node_id": alignment_node_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "confidence": confidence,
            "consistency_score": consistency_score
        }

    def _aggregate_features(self, features):
        """
        聚合多模态特征
        
        Args:
            features: 多模态特征列表
            
        Returns:
            np.ndarray: 聚合后的特征向量
        """
        if not features:
            return np.zeros(512)  # CLIP模型的特征维度
        
        # 转换为numpy数组
        feature_arrays = []
        for feature in features:
            if feature is not None:
                feature_arrays.append(feature)
        
        if not feature_arrays:
            return np.zeros(512)
        
        # 计算门控权重
        weights = self._calculate_gate_weights(feature_arrays)
        
        # 加权平均
        weighted_features = np.zeros_like(feature_arrays[0])
        for i, feature in enumerate(feature_arrays):
            weighted_features += weights[i] * feature
        
        # 归一化
        weighted_features = weighted_features / np.linalg.norm(weighted_features)
        
        return weighted_features

    def _calculate_gate_weights(self, features):
        """
        计算门控权重
        
        Args:
            features: 特征列表
            
        Returns:
            np.ndarray: 权重数组
        """
        # 简单的相似度-based权重计算
        num_features = len(features)
        if num_features == 1:
            return np.array([1.0])
        
        # 计算特征之间的相似度矩阵
        similarity_matrix = np.zeros((num_features, num_features))
        for i in range(num_features):
            for j in range(num_features):
                similarity_matrix[i, j] = np.dot(features[i], features[j])
        
        # 计算每个特征的平均相似度作为权重
        weights = np.mean(similarity_matrix, axis=1)
        weights = weights / np.sum(weights)
        
        return weights

    def _calculate_confidence(self, features):
        """
        计算置信度
        
        Args:
            features: 特征列表
            
        Returns:
            float: 置信度分数
        """
        if len(features) < 2:
            return 0.5
        
        # 计算特征之间的平均相似度
        similarity_sum = 0
        count = 0
        
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                if features[i] is not None and features[j] is not None:
                    similarity = np.dot(features[i], features[j])
                    similarity_sum += similarity
                    count += 1
        
        if count == 0:
            return 0.0
        
        return similarity_sum / count

    def _calculate_consistency(self, features):
        """
        计算一致性分数
        
        Args:
            features: 特征列表
            
        Returns:
            float: 一致性分数
        """
        if len(features) < 2:
            return 0.5
        
        # 计算特征之间的方差
        feature_matrix = np.vstack([f for f in features if f is not None])
        if feature_matrix.shape[0] < 2:
            return 0.0
        
        # 计算特征向量之间的距离方差
        distances = []
        for i in range(feature_matrix.shape[0]):
            for j in range(i + 1, feature_matrix.shape[0]):
                distance = np.linalg.norm(feature_matrix[i] - feature_matrix[j])
                distances.append(distance)
        
        if not distances:
            return 0.0
        
        # 方差越小，一致性越高
        variance = np.var(distances)
        consistency = 1.0 / (1.0 + variance)
        
        return consistency

    def align_entity(self, entity_id, entity_type, image_paths=None, texts=None):
        """
        对齐单个实体
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            image_paths: 图像路径列表
            texts: 文本内容列表
            
        Returns:
            dict: 对齐结果
        """
        print(f"正在对齐实体: {entity_id} ({entity_type})")
        
        # 提取特征
        features = []
        
        # 提取图像特征
        if image_paths:
            for image_path in image_paths:
                if os.path.exists(image_path):
                    image_feature = self.extract_image_features(image_path)
                    if image_feature is not None:
                        features.append(image_feature)
        
        # 提取文本特征
        if texts:
            for text in texts:
                text_feature = self.extract_text_features(text)
                if text_feature is not None:
                    features.append(text_feature)
        
        # 生成对齐节点
        if features:
            result = self.generate_alignment_node(entity_id, entity_type, features)
            
            # 保存特征到本地
            save_path = f"./data/embeddings/{entity_id}_{entity_type}.npy"
            np.save(save_path, np.array(features))
            print(f"特征已保存到: {save_path}")
            
            return result
        else:
            print("未提取到有效特征，对齐失败")
            return None

    def batch_align_entities(self, entities):
        """
        批量对齐实体
        
        Args:
            entities: 实体列表，每个实体包含id、type、image_paths、texts
            
        Returns:
            list: 对齐结果列表
        """
        results = []
        
        for entity in entities:
            result = self.align_entity(
                entity["id"],
                entity["type"],
                entity.get("image_paths", []),
                entity.get("texts", [])
            )
            if result:
                results.append(result)
        
        return results

    def search_aligned_entities(self, query, top_k=5):
        """
        搜索对齐的实体
        
        Args:
            query: 查询文本或图像路径
            top_k: 返回结果数量
            
        Returns:
            list: 搜索结果
        """
        # 提取查询特征
        if os.path.exists(query):
            # 图像查询
            query_feature = self.extract_image_features(query)
        else:
            # 文本查询
            query_feature = self.extract_text_features(query)
        
        if query_feature is None:
            return []
        
        # 查询所有对齐节点
        query = """
        MATCH (a:AlignmentNode)
        RETURN a.id as id, a.entity_id as entity_id, a.entity_type as entity_type, 
               a.embedding as embedding, a.confidence as confidence
        """
        
        results = []
        for record in self.graph.run(query):
            embedding = np.array(record["embedding"])
            similarity = np.dot(query_feature, embedding)
            
            results.append({
                "id": record["id"],
                "entity_id": record["entity_id"],
                "entity_type": record["entity_type"],
                "similarity": similarity,
                "confidence": record["confidence"]
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]

# 测试代码
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 初始化服务
    service = LAClipAlignmentService(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "Zyr123456")
    )
    
    # 测试对齐单个实体
    print("测试对齐单个实体...")
    result = service.align_entity(
        "清明上河图",
        "Artwork",
        image_paths=["artwork_images/artworks/清明上河图.jpg"] if os.path.exists("artwork_images/artworks/清明上河图.jpg") else [],
        texts=["清明上河图是北宋画家张择端创作的风俗画，描绘了北宋都城汴京的繁华景象"]
    )
    print(f"对齐结果: {result}")
    
    # 测试搜索
    print("\n测试搜索对齐实体...")
    search_results = service.search_aligned_entities("清明上河图")
    print(f"搜索结果: {search_results}")
