# -*- coding: utf-8 -*-
"""
image_search_app_simple.py - 简化版图像搜索服务
"""
import os
import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from py2neo import Graph, NodeMatcher
import logging

logger = logging.getLogger(__name__)

class ImageSearchService:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        """初始化图像搜索服务"""
        # Neo4j连接配置
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        # 模型配置
        self.model_name = "openai/clip-vit-base-patch32"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 延迟加载标志
        self.model_loaded = False
        self.database_connected = False
        
        print("ImageSearchService 初始化完成，模型和数据库将在首次使用时加载")

    def _load_model(self):
        """加载CLIP模型"""
        print(f"正在加载CLIP模型: {self.model_name}")
        try:
            print(f"设备: {self.device}")
            
            # 加载模型
            self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            print("✓ 模型加载成功")
            
            # 加载处理器
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            print("✓ 处理器加载成功")
            
            print(f"✓ 模型加载完成，使用设备: {self.device}")
            
        except Exception as e:
            print(f"✗ 模型加载失败: {e}")
            raise

    def _connect_database(self):
        """连接Neo4j数据库"""
        try:
            print(f"正在连接Neo4j数据库: {self.neo4j_uri}")
            print(f"用户名: {self.neo4j_user}")

            self.graph = Graph(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            self.matcher = NodeMatcher(self.graph)
            print("Neo4j数据库连接成功")

            # 测试连接
            self.graph.run("RETURN 1")
            print("Neo4j连接测试成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise
    
    def _ensure_model_loaded(self):
        """确保模型已加载"""
        if not self.model_loaded:
            self._load_model()
            self.model_loaded = True
    
    def _ensure_database_connected(self):
        """确保数据库已连接"""
        if not self.database_connected:
            self._connect_database()
            self.database_connected = True
    
    def extract_image_embedding(self, image_path):
        """提取图像特征向量"""
        # 确保模型已加载
        self._ensure_model_loaded()
        
        try:
            print(f"\n提取图像特征: {image_path}")
            if not os.path.exists(image_path):
                error_msg = f"图片文件不存在: {image_path}"
                print(f"✗ {error_msg}")
                logger.error(error_msg)
                return None

            print("✓ 图片文件存在")
            image = Image.open(image_path).convert("RGB")
            print("✓ 图像加载成功")
            
            print("✓ 图像预处理中...")
            inputs = self.processor(images=image, return_tensors="pt", padding=True)
            print("✓ 图像预处理成功")
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            print("✓ 输入转移到设备成功")

            with torch.no_grad():
                print("✓ 提取特征中...")
                image_features = self.model.get_image_features(**inputs)
                print("✓ 特征提取成功")

            # 归一化
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            print("✓ 特征归一化成功")
            
            features_np = image_features.cpu().numpy()[0]
            print(f"✓ 特征转换为numpy成功，维度: {features_np.shape}")
            
            return features_np
        except Exception as e:
            error_msg = f"特征提取失败: {e}"
            print(f"✗ {error_msg}")
            logger.error(error_msg)
            return None

    def calculate_weighted_similarity(self, query_embedding, db_embedding, node_properties, query_text=None):
        """计算加权相似度"""
        # 基础余弦相似度
        similarity = float(np.dot(query_embedding, db_embedding))
        
        # 调整基础相似度 - 非线性映射
        if similarity > 0.99:
            base_similarity = 0.85 + (similarity - 0.99) * 3.0
        elif similarity > 0.95:
            base_similarity = 0.75 + (similarity - 0.95) * 2.0
        elif similarity > 0.9:
            base_similarity = 0.65 + (similarity - 0.9) * 1.5
        elif similarity > 0.8:
            base_similarity = 0.55 + (similarity - 0.8) * 1.0
        elif similarity > 0.6:
            base_similarity = 0.4 + (similarity - 0.6) * 0.75
        else:
            base_similarity = 0.2 + similarity * 0.4
        
        # 加权因子 - 以图搜图时，大幅增加余弦相似度权重
        if query_text is None:  # 以图搜图
            weights = {
                'cosine': 0.9,  # 基础相似度权重（以图搜图时大幅增加）
                'dynasty': 0.02,  # 朝代匹配权重（以图搜图时减少）
                'style': 0.02,  # 风格匹配权重（以图搜图时减少）
                'description': 0.02,  # 描述匹配权重（以图搜图时减少）
                'title': 0.02,  # 标题匹配权重（以图搜图时减少）
                'scene': 0.02  # 场景匹配权重（以图搜图时减少）
            }
        else:
            weights = {
                'cosine': 0.6,  # 基础相似度权重
                'dynasty': 0.1,  # 朝代匹配权重
                'style': 0.1,  # 风格匹配权重
                'description': 0.1,  # 描述匹配权重
                'title': 0.05,  # 标题匹配权重
                'scene': 0.05  # 场景匹配权重
            }
        
        # 计算加权相似度
        weighted_similarity = base_similarity * weights['cosine']
        
        # 增加相似度的区分度
        if weighted_similarity > 0.85:
            weighted_similarity += 0.18  # 高相似度额外加分
        elif weighted_similarity > 0.75:
            weighted_similarity += 0.12  # 中高相似度额外加分
        elif weighted_similarity > 0.65:
            weighted_similarity += 0.08  # 中等相似度额外加分
        elif weighted_similarity > 0.55:
            weighted_similarity += 0.04  # 低相似度额外加分
        
        # 确保相似度在合理范围内
        weighted_similarity = min(0.99, max(0.3, weighted_similarity))  # 最低相似度30%，最高99%
        return weighted_similarity

    def _process_node(self, node, search_label, query_embedding, min_similarity, query_text):
        """处理单个节点的相似度计算"""
        try:
            # 获取节点所有属性
            node_properties = dict(node)
            
            # 尝试获取图像嵌入
            db_embedding = None
            
            # 首先检查节点是否有image_embedding属性
            if 'image_embedding' in node:
                try:
                    db_embedding = np.array(node['image_embedding'])
                except Exception:
                    pass
            
            # 如果没有image_embedding属性，尝试从图片文件中提取特征
            if db_embedding is None and search_label == "Artwork":
                title = node_properties.get('title', '')
                if title:
                    # 尝试获取图片路径
                    extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
                    image_path = None
                    
                    # 清理标题，去除括号等特殊字符
                    clean_title = title.split('（')[0].split('(')[0].strip()
                    
                    # 尝试不同的图片扩展名
                    for ext in extensions:
                        temp_path = os.path.join('artwork_images', 'artworks', clean_title + ext)
                        if os.path.exists(temp_path):
                            image_path = temp_path
                            break
                    
                    # 如果找不到，尝试原始标题
                    if image_path is None:
                        for ext in extensions:
                            temp_path = os.path.join('artwork_images', 'artworks', title + ext)
                            if os.path.exists(temp_path):
                                image_path = temp_path
                                break
                    
                    # 如果找到图片文件，提取特征
                    if image_path:
                        try:
                            db_embedding = self.extract_image_embedding(image_path)
                        except Exception as e:
                            logger.error(f"提取图片特征失败: {e}")
                            pass
            
            # 如果成功获取到嵌入向量，计算相似度
            if db_embedding is not None:
                # 计算加权相似度
                similarity = self.calculate_weighted_similarity(query_embedding, db_embedding, node_properties, query_text)

                # 只保留相似度大于阈值的
                if similarity >= min_similarity:
                    # 构建结果项
                    result_item = {
                        'similarity': similarity,
                        'node_type': search_label,
                        'node_id': node.identity,
                        'properties': node_properties
                    }

                    # 根据节点类型添加信息
                    if search_label == "Artwork":
                        title = node_properties.get('title', '')
                        if not title:  # 如果没有title，跳过
                            return None

                        # 合并节点属性
                        result_item.update({
                            'title': title,
                            'author': node_properties.get('author', '未知作者'),
                            'dynasty': node_properties.get('dynasty', ''),
                            'medium': node_properties.get('medium', ''),
                            'description': node_properties.get('description', ''),
                            'style': node_properties.get('style', ''),
                            'date': node_properties.get('date', ''),
                            'dimensions': node_properties.get('dimensions', ''),
                            'collection': node_properties.get('collection', ''),
                            'created_by': node_properties.get('author', '')
                        })

                        # 图片URL - 直接从artwork_images目录获取
                        result_item['image_url'] = self._get_artwork_image_url(title)

                    return result_item
        except Exception as e:
            # 记录错误但不中断处理
            logger.error(f"处理节点失败: {e}")
        return None

    def search_similar_images(self, query_embedding, search_label="Artwork", top_k=10, min_similarity=0.1, query_text=None):
        """搜索相似的图像"""
        results = []

        try:
            # 确保数据库已连接
            self._ensure_database_connected()
            
            # 获取所有节点
            nodes = list(self.matcher.match(search_label))
            print(f"找到 {len(nodes)} 个节点")
            
            # 处理节点
            all_results = []
            for node in nodes:
                result = self._process_node(node, search_label, query_embedding, min_similarity, query_text)
                if result:
                    all_results.append(result)

            # 按相似度排序
            all_results.sort(key=lambda x: x['similarity'], reverse=True)

            # 确保返回精确的 top_k 个结果
            if len(all_results) >= top_k:
                results = all_results[:top_k]
            else:
                # 如果结果不足，返回所有找到的
                results = all_results

            print(f"返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"搜索过程中出错: {e}")
            return []

    def _get_artwork_image_url(self, title):
        """根据画作标题获取图片URL"""
        try:
            if not title:
                return None

            # 清理标题，去除括号等特殊字符
            clean_title = title.split('（')[0].split('(')[0].strip()
            if not clean_title:
                return None

            # 尝试不同的图片扩展名
            extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']

            # 检查图片是否在artwork_images/artworks目录下
            for ext in extensions:
                image_path = os.path.join('artwork_images', 'artworks', clean_title + ext)
                if os.path.exists(image_path):
                    # 直接返回artwork_images目录的路径
                    return f"/artwork_image/{clean_title}{ext}"

            # 如果找不到，尝试查找原始标题（不带清理）
            for ext in extensions:
                image_path = os.path.join('artwork_images', 'artworks', title + ext)
                if os.path.exists(image_path):
                    return f"/artwork_image/{title}{ext}"

            # 如果还找不到，记录日志
            logger.warning(f"找不到画作图片: {title} (清理后: {clean_title})")
            return None
        except Exception as e:
            logger.error(f"获取图片URL失败: {e}")
            return None

    def search_by_image(self, image_path, top_k=5, min_similarity=0.1):
        """以图搜图"""
        # 提取图像特征
        print(f"开始处理图片: {image_path}")
        query_emb = self.extract_image_embedding(image_path)
        if query_emb is None:
            print("图像特征提取失败")
            return {"error": "图像特征提取失败"}

        print(f"特征提取成功，维度: {query_emb.shape}")

        # 搜索各类节点，设置更低的相似度阈值以确保找到足够的结果
        artwork_results = self.search_similar_images(query_emb, "Artwork", top_k * 3, 0.01, query_text=None)

        print(f"搜索完成: {len(artwork_results)} 个画作")

        # 确保返回足够数量的结果
        if len(artwork_results) < top_k:
            # 如果结果不足，降低阈值再次搜索
            additional_results = self.search_similar_images(query_emb, "Artwork", top_k - len(artwork_results), 0.001, query_text=None)
            # 去重并添加额外结果
            existing_titles = set(result['title'] for result in artwork_results)
            for result in additional_results:
                if result['title'] not in existing_titles and len(artwork_results) < top_k:
                    artwork_results.append(result)
                    existing_titles.add(result['title'])

        # 确保返回数量符合要求
        if len(artwork_results) > top_k:
            artwork_results = artwork_results[:top_k]

        return {
            "artworks": artwork_results,
            "seals": [],
            "inscriptions": []
        }
