
# -*- coding: utf-8 -*-
"""
image_search_app.py - 为Flask应用封装的图像搜索服务
"""
print("开始导入模块...")

# 尝试导入必要的模块
try:
    import os
    print("os导入成功")
except Exception as e:
    print(f"os导入失败: {e}")

try:
    import numpy as np
    print("numpy导入成功")
except Exception as e:
    print(f"numpy导入失败: {e}")

try:
    from PIL import Image
    print("PIL导入成功")
except Exception as e:
    print(f"PIL导入失败: {e}")

try:
    import torch
    print("torch导入成功")
except Exception as e:
    print(f"torch导入失败: {e}")

try:
    from transformers import CLIPProcessor, CLIPModel
    print("transformers导入成功")
except Exception as e:
    print(f"transformers导入失败: {e}")

try:
    from py2neo import Graph, NodeMatcher
    print("py2neo导入成功")
except Exception as e:
    print(f"py2neo导入失败: {e}")

try:
    import logging
    print("logging导入成功")
except Exception as e:
    print(f"logging导入失败: {e}")

try:
    import re
    print("re导入成功")
except Exception as e:
    print(f"re导入失败: {e}")

try:
    from collections import defaultdict
    print("collections导入成功")
except Exception as e:
    print(f"collections导入失败: {e}")

try:
    import concurrent.futures
    print("concurrent.futures导入成功")
except Exception as e:
    print(f"concurrent.futures导入失败: {e}")

try:
    from functools import lru_cache
    print("functools导入成功")
except Exception as e:
    print(f"functools导入失败: {e}")

print("模块导入完成")

logger = logging.getLogger(__name__)


class ImageSearchService:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        """初始化图像搜索服务"""
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        try:
            # 统一使用 py2neo
            self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self.matcher = NodeMatcher(self.graph)
            self.database_connected = True
            print("Neo4j 连接成功 (Py2neo 模式)")
        except Exception as e:
            print(f"Neo4j 连接失败: {e}")
            self.database_connected = False

        self.model_loaded = True 
    def _load_model(self):
        """【云端版】无需加载任何本地模型"""
        # 直接什么都不做，或者打印一行提示
        # print("云端模式下跳过本地 CLIP 模型加载")
        self.model_loaded = True
        return True

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
    
    def _preload_common_embeddings(self):
        """预加载常用文本特征"""
        print("预加载常用文本特征...")
        common_queries = [
            "山水画", "人物画", "花鸟画", "工笔画", "水墨画",
            "宋代山水画", "唐代人物画", "元代花鸟画",
            "文人雅士", "山水风光", "人物肖像"
        ]
        
        for query in common_queries:
            try:
                embedding = self._extract_text_embedding_without_cache(query)
                if embedding is not None:
                    self.text_embedding_cache[query] = embedding
            except Exception:
                pass
        print(f"预加载完成，缓存了 {len(self.text_embedding_cache)} 个常用特征")
    
    def _manage_cache(self, cache, key, value):
        """管理缓存大小"""
        if len(cache) >= self.cache_size:
            # 移除最旧的项
            oldest_key = next(iter(cache))
            del cache[oldest_key]
        cache[key] = value

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
        """【云端版】提取图片特征 (1024维)"""
        try:
            import dashscope
            from dashscope import MultiModalEmbedding
            dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

            abs_path = os.path.abspath(image_path)
            result = MultiModalEmbedding.call(
                model='multimodal-embedding-v1',
                input=[{'image': f"file://{abs_path}"}]
            )

            if result.status_code == 200:
                embedding_data = result.output['embeddings'][0]['embedding']
                return np.array(embedding_data, dtype=np.float32)
            else:
                logger.error(f"图片特征提取失败: {result.message}")
                return None
        except Exception as e:
            logger.error(f"提取图片特征出错: {e}")
            return None
    def enhance_text(self, text):
        """增强文本，提高搜索准确性"""
        # 1. 关键词提取和扩展
        enhanced_texts = []
        
        # 基础文本
        enhanced_texts.append(text)
        
        # 朝代映射
        dynasty_map = {
            '宋代': ['宋朝', '宋'],
            '唐代': ['唐朝', '唐'],
            '元代': ['元朝', '元'],
            '明代': ['明朝', '明'],
            '清代': ['清朝', '清'],
            '魏晋': ['魏晋南北朝'],
            '汉代': ['汉朝', '汉'],
            '三国': ['魏', '蜀', '吴'],
            '五代': ['五代十国'],
            '辽金': ['辽', '金'],
            '民国': ['中华民国']
        }
        
        # 风格映射
        style_map = {
            '山水画': ['山水', '山水图'],
            '山水图': ['山水', '山水画'],
            '人物画': ['人物', '人物图'],
            '人物图': ['人物', '人物画'],
            '花鸟画': ['花鸟', '花鸟图'],
            '花鸟图': ['花鸟', '花鸟画'],
            '工笔画': ['工笔', '工笔重彩'],
            '水墨画': ['水墨', '水墨画'],
            '写意画': ['写意', '大写意'],
            '青绿山水': ['青绿'],
            '浅绛山水': ['浅绛']
        }
        
        # 描述性词汇映射 - 增强场景相关词汇
        description_map = {
            # 自然景观
            '山石林立': ['峰峦叠嶂', '层峦叠翠', '山石', '岩石', '山峰'],
            '远山巍峨': ['高山巍峨', '远山耸立', '远山', '巍峨', '高山'],
            '近景树石': ['近景树木', '山石坚实', '树石', '树木', '岩石'],
            '山间溪边': ['山涧溪流', '溪水潺潺', '山涧', '溪边', '溪流'],
            '信步闲游': ['漫步游览', '悠闲漫步', '漫步', '闲游', '散步'],
            '山水': ['山水', '山峰', '溪流', '山林', '山涧', '瀑布', '山水图', '山水画'],
            '山林': ['山林', '森林', '树林', '林木', '山林幽寂', '山林寂静'],
            '山石': ['山石', '岩石', '石头', '石块', '石壁'],
            '雪景': ['雪景', '雪', '雪花', '雪地', '雪景图', '冬日雪景'],
            
            # 意境氛围
            '意境萧瑟': ['萧瑟意境', '苍凉意境', '萧瑟', '苍凉'],
            '雄伟壮阔': ['气势磅礴', '壮丽宏伟', '雄伟', '壮阔', '磅礴'],
            '宏伟壮丽': ['气势磅礴', '壮丽宏伟', '雄伟', '壮阔', '磅礴'],
            '宁静致远': ['宁静祥和', '平和宁静', '宁静', '祥和', '平和'],
            '清新淡雅': ['淡雅清新', '清爽雅致', '清新', '淡雅', '清爽'],
            '古朴典雅': ['典雅古朴', '古雅风格', '古朴', '典雅', '古雅'],
            '富丽堂皇': ['华丽堂皇', '金碧辉煌', '富丽', '堂皇', '华丽'],
            '简约留白': ['留白简约', '简洁留白', '简约', '留白', '简洁'],
            
            # 人物活动
            '文人雅士': ['文人墨客', '雅士闲人', '文人', '雅士', '墨客'],
            '信步闲游': ['漫步游览', '悠闲漫步', '漫步', '闲游', '散步'],
            '溪边漫步': ['溪边行走', '漫步溪边', '溪边', '漫步', '行走'],
            '骑马': ['骑马', '马', '骑行', '坐骑', '策马', '马背上', '骏马', '马匹', '马群', '骑马图', '骑马场景'],
            
            # 季节时间
            '秋日': ['秋日', '秋天', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋', '秋天的', '秋季的', '秋景图'],
            '秋天': ['秋日', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
            '秋季': ['秋日', '秋天', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
            '春日': ['春日', '春天', '春季', '春景', '春风', '春意', '春暖花开', '春色', '春季的', '春天的', '春景图'],
            '春天': ['春日', '春季', '春景', '春风', '春意', '春暖花开', '春色'],
            '春季': ['春日', '春天', '春景', '春风', '春意', '春暖花开', '春色'],
            '夏日': ['夏日', '夏天', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色', '夏季的', '夏天的', '夏景图'],
            '夏天': ['夏日', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
            '夏季': ['夏日', '夏天', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
            '冬日': ['冬日', '冬天', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色', '冬季的', '冬天的', '冬景图'],
            '冬天': ['冬日', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
            '冬季': ['冬日', '冬天', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
            
            # 画面元素
            '树石坚实': ['树木挺拔', '岩石坚固', '树木', '岩石', '坚实'],
            '溪水潺潺': ['溪流淙淙', '溪水流动', '溪水', '溪流', '潺潺'],
            '山林幽寂': ['山林寂静', '幽静山林', '山林', '幽寂', '寂静']
        }
        
        # 提取关键词并扩展
        for dynasty, variants in dynasty_map.items():
            if dynasty in text:
                enhanced_texts.extend(variants[:2])  # 只取前2个变体
                break
        
        for style, variants in style_map.items():
            if style in text:
                enhanced_texts.extend(variants[:2])  # 只取前2个变体
                break
        
        # 处理描述性词汇 - 增强场景词汇的匹配
        matched_descriptions = 0
        # 优先处理重要的场景词汇
        important_scenes = ['骑马', '秋日', '秋天', '秋季']
        for scene in important_scenes:
            if scene in text:
                if scene in description_map:
                    enhanced_texts.extend(description_map[scene])
                    matched_descriptions += 1
        
        # 处理其他描述性词汇
        for desc, variants in description_map.items():
            if desc in text and matched_descriptions < 5:  # 最多匹配5个描述性词汇
                if desc not in important_scenes:  # 避免重复处理
                    enhanced_texts.extend(variants[:2])  # 只取前2个变体
                    matched_descriptions += 1
        
        # 2. 语义重写
        # 对于常见搜索模式进行重写
        patterns = {
            r'(.*)的(山水|人物|花鸟)画': r'\1的\2绘画作品',
            r'(.*)的(画家|艺术家)': r'\1时期的著名画家',
            r'(.*)风格的(.*)': r'具有\1艺术风格的\2',
            r'(.*)的图片': r'具有\1特征的绘画作品',
            r'(.*)在(.*)': r'描绘\1在\2的场景',
            r'(秋日|秋天|秋季).*骑马': r'秋日骑马场景',
            r'骑马.*(秋日|秋天|秋季)': r'秋日骑马场景',
            r'(.*)骑马图': r'描绘\1骑马的绘画作品',
            r'(秋日|秋天|秋季).*图': r'秋日景色的绘画作品',
            r'(山水|人物|花鸟).*图': r'\1绘画作品',
            r'(山水|人物|花鸟)图': r'\1绘画作品'
        }
        
        # 优先处理重要的场景模式
        # 检查是否包含山水相关的词汇
        if any(term in text for term in ['山水', '山水画', '山水图']):
            # 添加山水相关的重写变体
            enhanced_texts.append('山水画作品')
            enhanced_texts.append('山水绘画')
            enhanced_texts.append('山水景色')
        
        # 处理语义重写
        for pattern, replacement in patterns.items():
            if re.search(pattern, text):
                rewritten = re.sub(pattern, replacement, text)
                enhanced_texts.append(rewritten)
                # 对于重要的场景模式，添加多个重写变体
                if '骑马' in text and ('秋日' in text or '秋天' in text or '秋季' in text):
                    enhanced_texts.append('秋日骑马场景')
                    enhanced_texts.append('秋天骑马图')
                    enhanced_texts.append('秋季骑马场景')
                # 对于山水相关的场景，添加多个重写变体
                elif any(term in text for term in ['山水', '山水画', '山水图']):
                    enhanced_texts.append('山水绘画作品')
                    enhanced_texts.append('山水景色')
                    enhanced_texts.append('山水画')
                break  # 只重写一次
        
        # 3. 提取关键词
        # 提取所有2个字符以上的中文词汇
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        important_keywords = [kw for kw in keywords if len(kw) > 1]
        
        # 提取重要的复合关键词
        compound_keywords = []
        # 检查常见的复合关键词模式
        compound_patterns = [
            r'宏伟壮丽', r'气势磅礴', r'壮丽宏伟', r'雄伟壮阔',
            r'宁静致远', r'清新淡雅', r'古朴典雅', r'富丽堂皇',
            r'山水画', r'人物画', r'花鸟画', r'工笔画',
            r'水墨画', r'写意画', r'青绿山水', r'浅绛山水'
        ]
        
        for pattern in compound_patterns:
            if pattern in text:
                compound_keywords.append(pattern)
        
        # 合并关键词并去重
        all_keywords = important_keywords + compound_keywords
        all_keywords = list(set(all_keywords))
        
        # 优先添加复合关键词，然后添加其他关键词
        enhanced_texts.extend(compound_keywords[:3])  # 最多添加3个复合关键词
        # 添加其他关键词，确保总数不超过5个
        remaining_keywords = [kw for kw in all_keywords if kw not in compound_keywords]
        enhanced_texts.extend(remaining_keywords[:5 - len(compound_keywords)])
        
        # 4. 针对特定场景的增强
        if '骑马' in text:
            enhanced_texts.extend(['骑马', '马', '骑行', '坐骑', '策马', '马背上'])
        if '秋日' in text or '秋天' in text or '秋季' in text:
            enhanced_texts.extend(['秋日', '秋天', '秋季', '秋景', '秋风', '秋意'])
        if '山水' in text or '山水图' in text or '山水画' in text:
            enhanced_texts.extend(['山水', '山峰', '溪流', '山林', '山涧', '瀑布'])
        
        # 5. 去重
        enhanced_texts = list(set(enhanced_texts))
        # 限制增强文本数量，最多15个
        enhanced_texts = enhanced_texts[:15]
        print(f"✓ 文本增强完成，生成 {len(enhanced_texts)} 个增强文本")
        return enhanced_texts

    def _extract_text_embedding_without_cache(self, text):
        """提取文本特征向量（无缓存版本）"""
        try:
            # 文本增强
            enhanced_texts = self.enhance_text(text)
            
            # 提取多个增强文本的特征并平均
            embeddings = []
            
            # 处理增强文本
            for enhanced_text in enhanced_texts:
                # 处理长文本 - 截断到模型最大长度
                try:
                    # 尝试处理文本
                    inputs = self.processor(text=[enhanced_text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                    
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        text_features = self.model.get_text_features(**inputs)
                        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                        embeddings.append(text_features.cpu().numpy()[0])
                except Exception:
                    # 尝试更激进的截断
                    try:
                        truncated_text = enhanced_text[:30] + "..."
                        inputs = self.processor(text=[truncated_text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                        inputs = {k: v.to(self.device) for k, v in inputs.items()}
                        
                        with torch.no_grad():
                            text_features = self.model.get_text_features(**inputs)
                            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                            embeddings.append(text_features.cpu().numpy()[0])
                    except Exception:
                        continue  # 跳过这个增强文本
            
            # 平均多个嵌入向量
            if embeddings:
                # 加权平均 - 给原始文本更高的权重
                weights = []
                for emb_text in enhanced_texts:
                    if emb_text == text:
                        weights.append(2.0)
                    else:
                        weights.append(1.0)
                weights = np.array(weights) / sum(weights)
                avg_embedding = np.average(embeddings, axis=0, weights=weights)
                # 重新归一化
                avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
                return avg_embedding
            else:
                # 如果增强失败，使用原始文本
                # 处理长文本
                try:
                    inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        text_features = self.model.get_text_features(**inputs)
                        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                        features_np = text_features.cpu().numpy()[0]
                    return features_np
                except Exception:
                    # 尝试更激进的截断
                    truncated_text = text[:30] + "..."
                    inputs = self.processor(text=[truncated_text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        text_features = self.model.get_text_features(**inputs)
                        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                        features_np = text_features.cpu().numpy()[0]
                    return features_np
        except Exception as e:
            error_msg = f"文本特征提取失败: {e}"
            logger.error(error_msg)
            return None
    
    def extract_text_embedding(self, text):
        """提取文本特征向量（带缓存）"""
        # 确保模型已加载
        self._ensure_model_loaded()
        
        # 检查缓存
        if text in self.text_embedding_cache:
            print(f"✓ 从缓存中获取文本特征")
            return self.text_embedding_cache[text]
        
        # 提取特征
        embedding = self._extract_text_embedding_without_cache(text)
        
        # 存入缓存
        if embedding is not None:
            self._manage_cache(self.text_embedding_cache, text, embedding)
        
        return embedding

    def calculate_weighted_similarity(self, query_embedding, db_embedding, node_properties, query_text=None):
        """计算加权相似度"""
        # 基础余弦相似度
        similarity = float(np.dot(query_embedding, db_embedding))
        
        # 调整基础相似度 - 非线性映射，大幅增强区分度
        # 使用更平缓的映射，让高相似度区域的结果不会过早达到最大值
        # 原始余弦相似度从 [-1, 1] 映射到 [0.2, 0.9]，并使用非线性变换
        # 这样可以让相似的结果分数更高，不相似的结果分数更低，同时保持区分度
        if similarity > 0.99:
            # 极高相似度区域
            base_similarity = 0.85 + (similarity - 0.99) * 3.0
        elif similarity > 0.95:
            # 高相似度区域
            base_similarity = 0.75 + (similarity - 0.95) * 2.0
        elif similarity > 0.9:
            # 中高相似度区域
            base_similarity = 0.65 + (similarity - 0.9) * 1.5
        elif similarity > 0.8:
            # 中等相似度区域
            base_similarity = 0.55 + (similarity - 0.8) * 1.0
        elif similarity > 0.6:
            # 低相似度区域
            base_similarity = 0.4 + (similarity - 0.6) * 0.75
        else:
            # 极低相似度区域
            base_similarity = 0.2 + similarity * 0.4
        
        # 加权因子 - 优化权重分配，大幅增加区分度
        # 根据基础相似度动态调整权重，让高相似度区域的基础相似度有更大影响
        # 以图搜图时，大幅增加余弦相似度权重
        if query_text is None:  # 以图搜图
            weights = {
                'cosine': 0.95,  # 基础相似度权重（以图搜图时大幅增加）
                'dynasty': 0.01,  # 朝代匹配权重（以图搜图时减少）
                'style': 0.01,  # 风格匹配权重（以图搜图时减少）
                'description': 0.01,  # 描述匹配权重（以图搜图时减少）
                'title': 0.01,  # 标题匹配权重（以图搜图时减少）
                'scene': 0.01  # 场景匹配权重（以图搜图时减少）
            }
        elif similarity > 0.95:
            # 高相似度区域，增加基础相似度权重
            weights = {
                'cosine': 0.6,  # 基础相似度权重
                'dynasty': 0.1,  # 朝代匹配权重
                'style': 0.1,  # 风格匹配权重
                'description': 0.1,  # 描述匹配权重
                'title': 0.05,  # 标题匹配权重
                'scene': 0.05  # 场景匹配权重
            }
        else:
            # 低相似度区域，让其他因素有更大影响
            weights = {
                'cosine': 0.4,  # 基础相似度权重
                'dynasty': 0.1,  # 朝代匹配权重
                'style': 0.1,  # 风格匹配权重
                'description': 0.2,  # 描述匹配权重
                'title': 0.05,  # 标题匹配权重
                'scene': 0.15  # 场景匹配权重
            }
        
        # 计算加权相似度
        weighted_similarity = base_similarity * weights['cosine']
        
        # 只有当query_text不为None时，才进行文本相关的匹配加分
        if query_text:
            # 朝代匹配加分
            if 'dynasty' in node_properties:
                dynasty = node_properties['dynasty']
                dynasty_keywords = ['宋代', '唐朝', '元代', '明代', '清代', '魏晋', '汉代', '三国', '五代', '辽金', '民国']
                for keyword in dynasty_keywords:
                    if keyword in query_text and keyword in dynasty:
                        weighted_similarity += weights['dynasty']
                        break
            
            # 风格匹配加分
            if 'style' in node_properties:
                style = node_properties['style']
                style_keywords = ['山水', '人物', '花鸟', '工笔', '水墨', '写意', '青绿', '浅绛']
                for keyword in style_keywords:
                    if keyword in query_text and keyword in style:
                        weighted_similarity += weights['style']
                        break
            
            # 描述匹配加分 - 大幅增强长段描述的匹配
            if 'description' in node_properties:
                description = node_properties['description']
                # 提取描述中的关键词
                desc_keywords = re.findall(r'\b\w+\b', query_text)
                # 计算匹配的关键词数量
                matched_keywords = 0
                total_keywords = len([kw for kw in desc_keywords if len(kw) > 1])
                
                # 提取复合关键词
                compound_keywords = []
                compound_patterns = [
                    r'宏伟壮丽', r'气势磅礴', r'壮丽宏伟', r'雄伟壮阔',
                    r'宁静致远', r'清新淡雅', r'古朴典雅', r'富丽堂皇',
                    r'山水画', r'人物画', r'花鸟画', r'工笔画',
                    r'水墨画', r'写意画', r'青绿山水', r'浅绛山水'
                ]
                
                for pattern in compound_patterns:
                    if pattern in query_text:
                        compound_keywords.append(pattern)
                
                if total_keywords > 0:
                    for keyword in desc_keywords:
                        if len(keyword) > 1 and keyword in description:
                            matched_keywords += 1
                    
                    # 额外匹配复合关键词
                    for compound_keyword in compound_keywords:
                        if compound_keyword in description:
                            matched_keywords += 2  # 复合关键词匹配权重更高
                            total_keywords += 1
                    
                    # 根据匹配比例加分，大幅增加权重
                    match_ratio = matched_keywords / total_keywords
                    # 描述匹配权重大幅增加，最高可达0.7
                    weighted_similarity += weights['description'] * match_ratio * 2.0
            
            # 标题匹配加分
            if 'title' in node_properties:
                title = node_properties['title']
                if query_text in title or title in query_text:
                    weighted_similarity += weights['title']
                # 标题部分匹配加分
                elif any(keyword in title for keyword in query_text.split() if len(keyword) > 1):
                    weighted_similarity += weights['title'] * 0.5
            
            # 场景匹配加分 - 大幅增强场景匹配的权重和精确度
            # 场景关键词 - 扩展更多场景
            scene_keywords = {
                '骑马': ['骑马', '马', '骑行', '坐骑', '策马', '马背上', '骏马', '马匹', '马群', '骑马图', '骑马场景'],
                '秋日': ['秋日', '秋天', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋', '秋天的', '秋季的', '秋景图'],
                '秋天': ['秋日', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
                '秋季': ['秋日', '秋天', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
                '春日': ['春日', '春天', '春季', '春景', '春风', '春意', '春暖花开', '春色', '春季的', '春天的', '春景图'],
                '春天': ['春日', '春季', '春景', '春风', '春意', '春暖花开', '春色'],
                '春季': ['春日', '春天', '春景', '春风', '春意', '春暖花开', '春色'],
                '夏日': ['夏日', '夏天', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色', '夏季的', '夏天的', '夏景图'],
                '夏天': ['夏日', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
                '夏季': ['夏日', '夏天', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
                '冬日': ['冬日', '冬天', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色', '冬季的', '冬天的', '冬景图'],
                '冬天': ['冬日', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
                '冬季': ['冬日', '冬天', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
                '山林': ['山林', '森林', '树林', '林木', '山林幽寂', '山林寂静', '山林图'],
                '山石': ['山石', '岩石', '石头', '石块', '石壁', '山石图'],
                '雪景': ['雪景', '雪', '雪花', '雪地', '雪景图', '冬日雪景'],
                '达官贵人': ['达官贵人', '官员', '贵人', '贵族', '官员', '士大夫', '官人', '贵人'],
                '山水': ['山水', '山峰', '溪流', '山林', '山涧', '瀑布', '山水图', '山水画'],
                '人物': ['人物', '人像', '人物画', '人物形象', '人物描绘'],
                '花鸟': ['花鸟', '花卉', '鸟类', '鸟语花香', '花团锦簇'],
                '文人雅士': ['文人雅士', '文人墨客', '雅士', '文人', '学士'],
                '信步闲游': ['信步闲游', '漫步', '闲游', '散步', '游览'],
                '山间溪边': ['山间溪边', '山涧', '溪边', '溪流', '山水之间'],
                '远山巍峨': ['远山巍峨', '远山', '巍峨', '高山', '山峰高耸']
            }
            
            # 检查场景匹配，允许多个场景匹配
            matched_scenes = 0
            total_scene_score = 0
            
            # 优先检查重要场景
            important_scenes = ['骑马', '秋日', '秋天', '秋季', '春日', '春天', '春季', '夏日', '夏天', '夏季', '冬日', '冬天', '冬季', '山林', '山石', '雪景', '山水']
            for scene in important_scenes:
                if scene in scene_keywords:
                    keywords = scene_keywords[scene]
                    # 检查查询文本中是否包含场景关键词
                    query_matched = any(keyword in query_text for keyword in keywords)
                    if query_matched:
                        # 检查描述中是否包含场景关键词
                        desc_matched = False
                        if 'description' in node_properties:
                            description = node_properties['description']
                            desc_matched = any(keyword in description for keyword in keywords)
                        
                        # 检查标题中是否包含场景关键词
                        title_matched = False
                        if 'title' in node_properties:
                            title = node_properties['title']
                            title_matched = any(keyword in title for keyword in keywords)
                        
                        # 如果描述或标题中包含场景关键词，则加分
                        if desc_matched or title_matched:
                            # 为重要场景提供更高的权重
                            if scene in ['骑马', '秋日', '秋天', '秋季']:
                                # 大幅提高骑马和秋日场景的权重
                                scene_score = weights['scene'] * 2.0
                            else:
                                scene_score = weights['scene']
                            
                            # 累加场景分数
                            total_scene_score += scene_score
                            matched_scenes += 1
            
            # 检查其他场景
            for scene, keywords in scene_keywords.items():
                if scene not in important_scenes and matched_scenes < 3:
                    # 检查查询文本中是否包含场景关键词
                    query_matched = any(keyword in query_text for keyword in keywords)
                    if query_matched:
                        # 检查描述中是否包含场景关键词
                        desc_matched = False
                        if 'description' in node_properties:
                            description = node_properties['description']
                            desc_matched = any(keyword in description for keyword in keywords)
                        
                        # 检查标题中是否包含场景关键词
                        title_matched = False
                        if 'title' in node_properties:
                            title = node_properties['title']
                            title_matched = any(keyword in title for keyword in keywords)
                        
                        # 如果描述或标题中包含场景关键词，则加分
                        if desc_matched or title_matched:
                            scene_score = weights['scene']
                            total_scene_score += scene_score
                            matched_scenes += 1
            
            # 应用场景匹配分数
            weighted_similarity += total_scene_score
            
            # 额外的语义匹配加分
            if 'style' in node_properties:
                style = node_properties['style']
                # 检查风格关键词匹配
                style_keywords = style.split()
                query_keywords = query_text.split()
                for sk in style_keywords:
                    if sk in query_keywords:
                        weighted_similarity += 0.12  # 增加语义匹配权重
                        break
        
        # 增加相似度的区分度
        # 对高相似度的结果进行额外加分，使用更激进的加分策略
        if weighted_similarity > 0.85:
            weighted_similarity += 0.18  # 高相似度额外加分
        elif weighted_similarity > 0.75:
            weighted_similarity += 0.12  # 中高相似度额外加分
        elif weighted_similarity > 0.65:
            weighted_similarity += 0.08  # 中等相似度额外加分
        elif weighted_similarity > 0.55:
            weighted_similarity += 0.04  # 低相似度额外加分
        
        # 确保相似度在合理范围内，非标题完全匹配时不超过99%
        # 只有在搜索结束后的结果处理阶段才会设置100%相似度（标题完全匹配）
        weighted_similarity = min(0.99, max(0.3, weighted_similarity))  # 最低相似度30%，最高99%
        return weighted_similarity

    def filter_and_rank_results(self, results, query_text=None):
        """过滤和排序搜索结果"""
        if not results:
            return []
        
        # 1. 过滤掉相似度过低的结果 - 使用55%作为最低阈值
        filtered_results = [r for r in results if r['similarity'] >= 0.55]
        
        # 如果结果不足，降低阈值以确保有足够的结果
        if len(filtered_results) < 3:
            filtered_results = [r for r in results if r['similarity'] >= 0.5]
        
        # 2. 更精细的排序，增强区分度
        def rank_key(result):
            # 基础相似度（权重更高，使用平方来增强区分度）
            score = result['similarity'] ** 2 * 200
            
            # 标题匹配加分 - 增加权重
            if query_text and 'title' in result:
                title = result['title'].lower()
                query = query_text.lower()
                if query in title:
                    score += 30  # 增加标题匹配权重
                elif any(keyword in title for keyword in query.split()):
                    score += 20  # 增加部分匹配权重
            
            # 朝代匹配加分 - 增加权重
            if query_text and 'dynasty' in result and result['dynasty']:
                dynasty = result['dynasty'].lower()
                query = query_text.lower()
                if any(keyword in query for keyword in dynasty.split()):
                    score += 15  # 增加朝代匹配权重
            
            # 风格匹配加分 - 增加权重
            if query_text and 'style' in result and result['style']:
                style = result['style'].lower()
                query = query_text.lower()
                if any(keyword in query for keyword in style.split()):
                    score += 15  # 增加风格匹配权重
            
            # 作者匹配加分 - 增加权重
            if query_text and 'author' in result and result['author'] != '未知作者':
                author = result['author'].lower()
                query = query_text.lower()
                if author in query:
                    score += 25  # 增加作者匹配权重
            
            # 描述匹配加分 - 增加权重和计算精度
            if query_text and 'description' in result and result['description']:
                description = result['description'].lower()
                query = query_text.lower()
                # 提取有意义的关键词
                query_keywords = [kw for kw in query.split() if len(kw) > 1]
                matched_keywords = sum(1 for keyword in query_keywords if keyword in description)
                total_keywords = len(query_keywords)
                if total_keywords > 0:
                    match_ratio = matched_keywords / total_keywords
                    # 增加描述匹配权重，最高可达30分
                    score += match_ratio * 30
            
            # 场景匹配加分 - 大幅增强场景匹配权重
            if query_text:
                # 场景关键词 - 扩展更多场景
                scene_keywords = {
                    '骑马': ['骑马', '马', '骑行', '坐骑', '策马', '马背上', '骏马', '马匹', '马群', '骑马图', '骑马场景'],
                    '秋日': ['秋日', '秋天', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋', '秋天的', '秋季的', '秋景图'],
                    '秋天': ['秋日', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
                    '秋季': ['秋日', '秋天', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋'],
                    '春日': ['春日', '春天', '春季', '春景', '春风', '春意', '春暖花开', '春色', '春季的', '春天的', '春景图'],
                    '春天': ['春日', '春季', '春景', '春风', '春意', '春暖花开', '春色'],
                    '春季': ['春日', '春天', '春景', '春风', '春意', '春暖花开', '春色'],
                    '夏日': ['夏日', '夏天', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色', '夏季的', '夏天的', '夏景图'],
                    '夏天': ['夏日', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
                    '夏季': ['夏日', '夏天', '夏景', '夏风', '夏意', '夏日炎炎', '夏色'],
                    '冬日': ['冬日', '冬天', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色', '冬季的', '冬天的', '冬景图'],
                    '冬天': ['冬日', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
                    '冬季': ['冬日', '冬天', '冬景', '冬风', '冬意', '冬日严寒', '冬色'],
                    '山林': ['山林', '森林', '树林', '林木', '山林幽寂', '山林寂静', '山林图'],
                    '山石': ['山石', '岩石', '石头', '石块', '石壁', '山石图'],
                    '雪景': ['雪景', '雪', '雪花', '雪地', '雪景图', '冬日雪景'],
                    '达官贵人': ['达官贵人', '官员', '贵人', '贵族', '官员', '士大夫', '官人', '贵人'],
                    '山水': ['山水', '山峰', '溪流', '山林', '山涧', '瀑布', '山水图', '山水画'],
                    '人物': ['人物', '人像', '人物画', '人物形象', '人物描绘'],
                    '花鸟': ['花鸟', '花卉', '鸟类', '鸟语花香', '花团锦簇'],
                    '文人雅士': ['文人雅士', '文人墨客', '雅士', '文人', '学士'],
                    '信步闲游': ['信步闲游', '漫步', '闲游', '散步', '游览'],
                    '山间溪边': ['山间溪边', '山涧', '溪边', '溪流', '山水之间'],
                    '远山巍峨': ['远山巍峨', '远山', '巍峨', '高山', '山峰高耸']
                }
                
                # 检查场景匹配
                scene_matches = 0
                total_scene_score = 0
                
                # 优先检查重要场景
                important_scenes = ['骑马', '秋日', '秋天', '秋季', '春日', '春天', '春季', '夏日', '夏天', '夏季', '冬日', '冬天', '冬季', '山林', '山石', '雪景']
                for scene in important_scenes:
                    if scene in scene_keywords:
                        keywords = scene_keywords[scene]
                        if any(keyword in query_text for keyword in keywords):
                            # 检查描述中是否包含场景关键词
                            desc_matched = False
                            if 'description' in result and result['description']:
                                description = result['description'].lower()
                                desc_matched = any(keyword in description for keyword in keywords)
                            
                            # 检查标题中是否包含场景关键词
                            title_matched = False
                            if 'title' in result and result['title']:
                                title = result['title'].lower()
                                title_matched = any(keyword in title for keyword in keywords)
                            
                            if desc_matched or title_matched:
                                # 为重要场景提供更高的权重
                                if scene in ['骑马', '秋日', '秋天', '秋季']:
                                    total_scene_score += 25  # 每个重要场景匹配加25分
                                else:
                                    total_scene_score += 15  # 每个普通场景匹配加15分
                                scene_matches += 1
                
                # 检查其他场景
                for scene, keywords in scene_keywords.items():
                    if scene not in important_scenes and scene_matches < 3:
                        if any(keyword in query_text for keyword in keywords):
                            # 检查描述中是否包含场景关键词
                            desc_matched = False
                            if 'description' in result and result['description']:
                                description = result['description'].lower()
                                desc_matched = any(keyword in description for keyword in keywords)
                            
                            # 检查标题中是否包含场景关键词
                            title_matched = False
                            if 'title' in result and result['title']:
                                title = result['title'].lower()
                                title_matched = any(keyword in title for keyword in keywords)
                            
                            if desc_matched or title_matched:
                                total_scene_score += 10  # 每个其他场景匹配加10分
                                scene_matches += 1
                
                # 应用场景匹配分数
                if total_scene_score > 0:
                    score += total_scene_score
            
            return score
        
        # 按综合得分排序
        filtered_results.sort(key=rank_key, reverse=True)
        
        # 3. 对排序后的结果进行相似度调整，确保有明显的差距
        if filtered_results:
            # 对前几个结果进行相似度提升
            for i, result in enumerate(filtered_results):
                # 检查是否是标题完全匹配
                title_match = False
                if query_text and 'title' in result:
                    title = result['title']
                    # 检查标题是否完全匹配（严格相等）
                    if title == query_text:
                        title_match = True
                        result['similarity'] = 1.0  # 只有标题完全匹配时才返回100%相似度
                
                # 如果不是标题完全匹配，限制相似度不超过99%，并创建合理的相似度阶梯
                if not title_match:
                    # 基于原始相似度创建更合理的阶梯
                    base_similarity = result['similarity']
                    
                    # 为不同排名的结果创建更自然的相似度梯度
                    if i == 0:
                        # 第一个结果：85-95%
                        result['similarity'] = min(0.95, max(0.85, base_similarity * 1.15))
                    elif i == 1:
                        # 第二个结果：80-90%
                        result['similarity'] = min(0.90, max(0.80, base_similarity * 1.1))
                    elif i == 2:
                        # 第三个结果：75-85%
                        result['similarity'] = min(0.85, max(0.75, base_similarity * 1.05))
                    elif i == 3:
                        # 第四个结果：70-80%
                        result['similarity'] = min(0.80, max(0.70, base_similarity * 1.02))
                    elif i == 4:
                        # 第五个结果：65-75%
                        result['similarity'] = min(0.75, max(0.65, base_similarity * 1.0))
                    else:
                        # 后续结果：60-70%
                        result['similarity'] = min(0.70, max(0.60, base_similarity))
                # 后续结果保持原有相似度
        
        return filtered_results

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

                        # 获取完整的作品信息，包括作者和朝代
                        artwork_info = self._get_complete_artwork_info(title)
                        
                        # 合并节点属性和完整信息
                        result_item.update({
                            'title': title,
                            'author': artwork_info.get('author', node_properties.get('author', '未知作者')),
                            'dynasty': artwork_info.get('dynasty', node_properties.get('dynasty', '')),
                            'medium': node_properties.get('medium', ''),
                            'description': node_properties.get('description', ''),
                            'style': node_properties.get('style', ''),
                            'date': node_properties.get('date', ''),
                            'dimensions': node_properties.get('dimensions', ''),
                            'collection': node_properties.get('collection', ''),
                            'created_by': artwork_info.get('author', node_properties.get('author', ''))
                        })

                        # 图片URL - 直接从artwork_images目录获取
                        result_item['image_url'] = self._get_artwork_image_url(title)

                    elif search_label == "Seal":
                        result_item.update({
                            'text': node_properties.get('text', node_properties.get('name', '无文')),
                            'owner': node_properties.get('owner', '未知藏家'),
                            'type': node_properties.get('type', '')
                        })
                    elif search_label == "Inscription":
                        result_item.update({
                            'text': node_properties.get('text', ''),
                            'author': node_properties.get('author', '佚名'),
                            'type': node_properties.get('type', '')
                        })

                    return result_item
        except Exception as e:
            # 记录错误但不中断处理
            logger.error(f"处理节点失败: {e}")
        return None
    
    def search_similar_images(self, query_vector, label="Artwork", top_k=5, min_similarity=0.01):
        """在数据库中进行向量余弦相似度计算"""
        # 将 numpy 数组转为 list 供 Cypher 使用
        vector_list = query_vector.tolist() if hasattr(query_vector, 'tolist') else query_vector

        # 核心 Cypher：通过数学公式计算余弦相似度
        query = f"""
        MATCH (n:{label})
        WHERE n.image_embedding IS NOT NULL
        WITH n, n.image_embedding AS vece
        WITH n, 
            reduce(s=0.0, i in range(0, size(vece)-1) | s + vece[i] * $vector[i]) /
            (sqrt(reduce(s=0.0, i in range(0, size(vece)-1) | s + vece[i]^2)) * 
            sqrt(reduce(s=0.0, i in range(0, size($vector)-1) | s + $vector[i]^2)) + 0.00001) AS score
        WHERE score > $min_score
        RETURN n.title AS title, score AS similarity
        ORDER BY similarity DESC
        LIMIT $limit
        """
        try:
            # 使用 py2neo 的 run
            results = self.graph.run(query, vector=vector_list, min_score=min_similarity, limit=top_k).data()
            return results
        except Exception as e:
            logger.error(f"数据库查询出错: {e}")
            return []
    def _get_complete_artwork_info(self, title):
        """获取作品完整信息：支持关系节点和属性双重读取"""
        try:
            # 这里的 query 变量就是我之前说的 info_query 逻辑
            query = """
            MATCH (n:Artwork)
            WHERE n.title = $title OR n.name = $title OR n.image_filename STARTS WITH $title
            
            // 1. 优先找连着的【作者】节点
            OPTIONAL MATCH (n)-[:CREATED_BY]->(a:Artist)
            
            // 2. 优先找连着的【朝代】节点 (你刚才建立的 PART_OF 关系在这里生效)
            OPTIONAL MATCH (n)-[:PART_OF]->(d:Dynasty)
            
            // 3. 优先找连着的【风格】节点 (适配你截图里的“属于流派”)
            OPTIONAL MATCH (n)-[:属于流派|HAS_STYLE]->(s:Style)
            
            RETURN 
                coalesce(a.name, n.author, '无确切作者') AS author,
                coalesce(d.name, n.dynasty, '未知朝代') AS dynasty,
                coalesce(s.name, n.style, '未知风格') AS style,
                coalesce(n.description, n.info, '暂无描述') AS detail
            LIMIT 1
            """
            result = self.graph.run(query, title=title).data()
            if result:
                return result[0]
            # 如果彻底没找到，返回默认值
            return {'author': '无确切作者', 'dynasty': '未知朝代', 'style': '未知风格', 'detail': '暂无描述'}
        except Exception as e:
            logger.error(f"获取完整信息失败: {e}")
            return {'author': '无确切作者', 'dynasty': '未知朝代', 'style': '未知风格', 'detail': '暂无描述'}
    def _get_artwork_image_url(self, title):
        """根据画作标题获取图片URL - 直接访问artwork_images目录"""
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
        try:
            query_emb = self.extract_image_embedding(image_path)
            if query_emb is None: return {"error": "特征提取失败"}

            # 1. 多请求一个结果 (top_k + 1)，防止过滤掉“自己”后数量不足
            artwork_results = self.search_similar_images(query_emb, "Artwork", top_k + 1, min_similarity)
            
            final_artworks = []
            for res in artwork_results:
                # 如果结果已经凑够了 top_k 个，就停止
                if len(final_artworks) >= top_k:
                    break
                    
                title = res.get('title', '未知')
                raw_score = float(res.get('similarity', 0))

                # 2. 过滤掉几乎完全一样的原图 (相似度 > 99.8%)
                if raw_score > 0.998:
                    continue

                # 正常处理逻辑 - 返回0-1之间的数值，让前端乘以100显示百分比
                display_score = raw_score
                display_score = min(1.0, max(0.0, display_score))

                artwork_info = self._get_complete_artwork_info(title)
                final_artworks.append({
                    'title': title,
                    'similarity': display_score, 
                    'author': artwork_info.get('author', '未知作者'),
                    'dynasty': artwork_info.get('dynasty', '未知'),
                    'style': artwork_info.get('style', '未知'),     # 【新增】
                    'description': artwork_info.get('detail', '暂无描述'), # 【新增】
                    'image_url': self._get_artwork_image_url(title)
                })

            return {"success": True, "artworks": final_artworks}
        except Exception as e:
            return {"error": str(e)}   
    def search_by_author(self, author, top_k=5):
        try:
            # 改为直接查询 Artwork 节点的 author 属性
            query = """
            MATCH (a:Artwork)
            WHERE a.author CONTAINS $author
            RETURN a, a.author as author_name
            LIMIT $top_k
            """
            results = self.graph.run(query, author=author, top_k=top_k).data()
            
            logger.info(f"找到 {len(results)} 个作者匹配的作品")
            
            # 构建结果
            artwork_results = []
            for result in results:
                node = result['a']
                node_properties = dict(node)
                author_name = result.get('author_name', '未知作者')
                
                # 计算作者匹配度
                author_similarity = 1.0
                if author == author_name:
                    author_similarity = 1.0  # 完全匹配
                elif author in author_name:
                    author_similarity = 0.9  # 部分匹配
                elif author_name in author:
                    author_similarity = 0.8  # 反向部分匹配
                
                # 获取完整信息
                artwork_info = self._get_complete_artwork_info(node_properties.get('title', ''))
                
                result_item = {
                    'similarity': author_similarity,  # 根据匹配程度设置相似度
                    'node_type': "Artwork",
                    'node_id': node.identity,
                    'properties': node_properties,
                    'title': node_properties.get('title', ''),
                    'author': author_name,
                    'dynasty': artwork_info.get('dynasty', node_properties.get('dynasty', '')),
                    'medium': node_properties.get('medium', ''),
                    'description': node_properties.get('description', ''),
                    'style': node_properties.get('style', ''),
                    'date': node_properties.get('date', ''),
                    'dimensions': node_properties.get('dimensions', ''),
                    'collection': node_properties.get('collection', ''),
                    'created_by': author_name,
                    'image_url': self._get_artwork_image_url(node_properties.get('title', ''))
                }
                artwork_results.append(result_item)
            
            # 按相似度排序
            artwork_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 限制返回数量
            if len(artwork_results) > top_k:
                artwork_results = artwork_results[:top_k]
            
            return artwork_results
        except Exception as e:
            logger.error(f"作者搜索失败: {e}")
            return []

    def search_by_title(self, title, top_k=5):
        """按标题精确搜索"""
        try:
            logger.info(f"按标题搜索: {title}")
            
            # 精确匹配标题 - 改进查询逻辑
            query = """
            MATCH (a:Artwork) 
            WHERE a.title CONTAINS $title OR $title CONTAINS a.title
            RETURN a
            ORDER BY a.title
            """
            
            results = self.graph.run(query, title=title).data()
            logger.info(f"找到 {len(results)} 个标题匹配的作品")
            
            # 构建结果
            artwork_results = []
            for result in results:
                node = result['a']
                node_properties = dict(node)
                
                # 获取完整信息
                artwork_info = self._get_complete_artwork_info(node_properties.get('title', ''))
                
                # 计算标题匹配度
                title_similarity = 1.0
                if title == node_properties.get('title', ''):
                    title_similarity = 1.0  # 完全匹配
                elif title in node_properties.get('title', ''):
                    title_similarity = 0.9  # 部分匹配
                elif node_properties.get('title', '') in title:
                    title_similarity = 0.8  # 反向部分匹配
                
                result_item = {
                    'similarity': title_similarity,  # 根据匹配程度设置相似度
                    'node_type': "Artwork",
                    'node_id': node.identity,
                    'properties': node_properties,
                    'title': node_properties.get('title', ''),
                    'author': artwork_info.get('author', node_properties.get('author', '未知作者')),
                    'dynasty': artwork_info.get('dynasty', node_properties.get('dynasty', '')),
                    'medium': node_properties.get('medium', ''),
                    'description': node_properties.get('description', ''),
                    'style': node_properties.get('style', ''),
                    'date': node_properties.get('date', ''),
                    'dimensions': node_properties.get('dimensions', ''),
                    'collection': node_properties.get('collection', ''),
                    'created_by': artwork_info.get('author', ''),
                    'image_url': self._get_artwork_image_url(node_properties.get('title', ''))
                }
                artwork_results.append(result_item)
            
            # 按相似度排序
            artwork_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 限制返回数量
            if len(artwork_results) > top_k:
                artwork_results = artwork_results[:top_k]
            
            return artwork_results
        except Exception as e:
            logger.error(f"标题搜索失败: {e}")
            return []

    def search_by_text(self, text, top_k=5, min_similarity=0.01):
        """【最终修正版】以文搜图：带知识增强与高兼容性"""
        try:
            import dashscope
            from dashscope import MultiModalEmbedding
            dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

            # 1. 语义特征提取
            result = MultiModalEmbedding.call(
                model='multimodal-embedding-v1',
                input=[{'text': text}]
            )
            if result.status_code != 200:
                logger.error(f"特征提取失败: {result.message}")
                return {"success": False, "error": "特征提取失败", "results": [], "artworks": []}
            
            query_emb = result.output['embeddings'][0]['embedding']

            # 2. 向量初筛 
            # 注意：这里把 min_similarity 设得很低（0.01），防止初筛就把好苗子过滤掉了
            artwork_results = self.search_similar_images(query_emb, "Artwork", top_k * 3, 0.01)
            
            if not artwork_results:
                logger.warning("数据库未匹配到任何相似向量")
                return {"success": True, "results": [], "artworks": [], "count": 0}

            temp_list = []
            for res in artwork_results:
                title = res.get('title', '未知')
                raw_score = float(res.get('similarity', 0))
                
                # 获取该画作的完整知识
                info = self._get_complete_artwork_info(title)
                
                # --- 核心：知识权重提升 (Boosting) ---
                # 保持0-1之间的数值
                boosted_score = raw_score 
                
                # A. 朝代匹配加分（权重最高）
                # 如果用户搜“宋”，画作朝代是“北宋”或“南宋”，加分
                dynasty_keywords = ["宋", "唐", "元", "明", "清", "五代", "晋", "汉"]
                for dk in dynasty_keywords:
                    if dk in text: # 用户搜了某个朝代
                        actual_dynasty = info.get('dynasty', '')
                        if dk in actual_dynasty:
                            boosted_score += 0.3  # 匹配到朝代，大幅加分
                            break # 匹配一个朝代就够了

                # B. 风格/类型匹配加分
                style_keywords = ["山水", "人物", "花鸟", "工笔", "写意"]
                for sk in style_keywords:
                    if sk in text and sk in info.get('style', ''):
                        boosted_score += 0.1

                temp_list.append({
                    'title': title,
                    'similarity': boosted_score,
                    'author': info.get('author'),
                    'dynasty': info.get('dynasty'),
                    'style': info.get('style'),
                    'description': info.get('detail'),
                    'image_url': self._get_artwork_image_url(title)
                })

            # 3. 根据加成后的分值重新排序
            temp_list.sort(key=lambda x: x['similarity'], reverse=True)

            # 4. 截取前 top_k 个，并格式化分值
            final_artworks = []
            for item in temp_list[:top_k]:
                # 确保分值在合理范围（不超过1.0，不低于0）
                item['similarity'] = min(1.0, max(0.0, item['similarity']))
                final_artworks.append(item)

            # 5. 【关键】同时返回 results 和 artworks 两个键，确保前端能接到
            return {
                "success": True, 
                "results": final_artworks,
                "artworks": final_artworks,
                "count": len(final_artworks)
            }

        except Exception as e:
            logger.error(f"search_by_text 异常: {e}", exc_info=True)
            return {"success": False, "error": str(e), "results": [], "artworks": []}