
# -*- coding: utf-8 -*-
import torch.nn.functional as F
import os
import dashscope
from dashscope import MultiModalEmbedding
import numpy as np
import faiss
from py2neo import Graph, NodeMatcher
import concurrent.futures
import json
import threading
import logging
import urllib.parse

# 屏蔽 dashscope 库打印庞大的请求体
logging.getLogger("dashscope").setLevel(logging.WARNING)
# 屏蔽底层网络库的请求日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
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
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, index_path="art_index_1024.index", paths_path="art_paths.npy",
                 base_ids_path="art_base_ids.json"):
        """初始化图像搜索服务"""
        # 1. Neo4j连接配置 (保留你原有的KG图谱连接)
        self.neo4j_uri = "bolt://127.0.0.1:7687"
        self.neo4j_user = "neo4j"
        self.neo4j_password = "12345678"

        self.image_root_dir = os.getenv("LOCAL_PROJECT_ROOT")

        # 2. 通义千问 API 配置 (替换成你的真实 KEY)
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.api_key = getattr(dashscope, 'api_key', os.getenv("DASHSCOPE_API_KEY"))
        # 3. FAISS 向量库路径 (就是上一步 build_index.py 跑出来的两个文件)
        self.index_path = index_path
        self.paths_path = paths_path
        self.base_ids_path = base_ids_path

        # 存放加载后的数据
        self.index = None
        self.paths_array = None
        self.base_ids_list = None       # 🌟 新增
        self.kg_graph = None            # 🌟 新增：存放Neo4j连接对象
        
        # 4. 延迟加载标志
        self.resources_loaded = False
        self.database_connected = False
        self.model_loaded = False
        
        # 5. 特征缓存 (强烈建议保留！把API返回的特征存起来，下次搜同样的内容就不花钱了)
        self.text_embedding_cache = {}
        self.image_embedding_cache = {}
        self.cache_size = 1000  # 缓存大小限制
        
        # 6. 线程池 (保留)
        self.batch_size = 16
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        print("ImageSearchService 初始化完成，API配置和数据库将在首次使用时加载")

    def _load_model(self):
        """
        加载依赖资源 (原 _load_model 方法的升级版)
        【重大改变】：不再需要加载笨重且容易报错的本地 CLIP 模型！
        现在的任务是加载轻量级的 FAISS 1024维向量库。
        """
        print("正在加载 FAISS 1024维多模态向量库...")
        try:
            # 检查上一步的建库文件是否存在
            if not os.path.exists(self.index_path) or not os.path.exists(self.paths_path):
                error_msg = f"找不到向量库文件！请先运行建库脚本生成 {self.index_path} 和 {self.paths_path}"
                print(f"✗ {error_msg}")
                raise FileNotFoundError(error_msg)

            # 秒级加载本地向量索引
            self.index = faiss.read_index(self.index_path)
            self.paths_array = np.load(self.paths_path).tolist()
            with open(self.base_ids_path, 'r') as f:
                self.base_ids_list = json.load(f)
            
            self.model_loaded = True
            self.resources_loaded = True
            print(f"✓ 向量库加载成功！当前图库共包含 {self.index.ntotal} 张书画作品。")
            
        except Exception as e:
            print(f"✗ 向量库加载失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _connect_database(self):
        """连接Neo4j数据库 (完全保留你原来的优秀逻辑，无需修改)"""
        try:
            print(f"正在连接Neo4j数据库: {self.neo4j_uri}")
            print(f"用户名: {self.neo4j_user}")

            self.graph = Graph(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            self.matcher = NodeMatcher(self.graph)
            print("✓ Neo4j数据库连接成功")

            # 测试连接
            self.graph.run("RETURN 1")
            print("✓ Neo4j连接测试成功")
            self.database_connected = True
        except Exception as e:
            print(f"✗ 数据库连接失败: {e}")
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
        """确保向量库已加载（兼容旧代码的标志位）"""
        # 如果新标志位和旧标志位都没加载，才去执行加载
        if not getattr(self, 'resources_loaded', False) and not getattr(self, 'model_loaded', False):
            self._load_model()
            # 加载完成后，把新旧两个标志位都设为 True，防止别的函数报错
            self.resources_loaded = True
            self.model_loaded = True
    
    def _ensure_database_connected(self):
        """确保数据库已连接"""
        if not self.database_connected:
            self._connect_database()
            self.database_connected = True
    
    def extract_image_embedding(self, image_path):
        """调用千问API提取图像特征（带缓存）"""
        import threading
        import pathlib
        self._ensure_model_loaded()
        
        # 1. 统一路径格式（修复 Windows 下传入路径可能带错位斜杠的问题）
        image_path = os.path.abspath(image_path)
        
        if image_path in self.image_embedding_cache:
            return self.image_embedding_cache[image_path]
        
        temp_img_path = None
        try:
            if not os.path.exists(image_path):
                logger.error(f"文件不存在: {image_path}")
                return None

            from PIL import Image
            import base64, io

            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            max_size = 1024
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 直接编码成 base64，完全不依赖本地文件路径
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            image_data_url = f"data:image/jpeg;base64,{b64_data}"

            api_key = os.getenv("DASHSCOPE_API_KEY")

            response = MultiModalEmbedding.call(
                model="multimodal-embedding-v1",
                input=[{"image": image_data_url}],
                api_key=api_key
            )

            if response.status_code == 200:
                features_np = np.array(response.output["embeddings"][0]["embedding"], dtype=np.float32)
                features_np = features_np / np.linalg.norm(features_np)
                self._manage_cache(self.image_embedding_cache, image_path, features_np)
                return features_np
            else:
                logger.error(f"提取图像特征失败: {response.message} (代码: {response.status_code})")
                return None

        except Exception as e:
            logger.error(f"提取特征异常: {e}")
            return None
        
    def _extract_text_embedding_without_cache(self, text):
        """调用千问API提取文本特征"""
        try:
            enhanced_texts = self.enhance_text(text)
            rich_prompt = f"核心查询: {text}。相关场景与元素包含: {'，'.join(enhanced_texts[:8])}"
            
            # 修正：参数改为 input=[{"text": ...}]
            response = MultiModalEmbedding.call(
                model="multimodal-embedding-v1",
                input=[{"text": rich_prompt}],
                api_key=os.getenv("DASHSCOPE_API_KEY")
            )
            
            if response.status_code == 200:
                # 修正：读取嵌套结构
                features_np = np.array(response.output["embeddings"][0]["embedding"], dtype=np.float32)
                # 归一化
                return features_np / np.linalg.norm(features_np)
            else:
                logger.error(f"文本特征提取失败: {response.message}")
                return None
        except Exception as e:
            logger.error(f"文本特征提取异常: {e}")
            return None
    
    def extract_text_embedding(self, text):   #新增
        self._ensure_model_loaded()
        if text in self.text_embedding_cache:
            return self.text_embedding_cache[text]
        
        embedding = self._extract_text_embedding_without_cache(text)
        if embedding is not None:
            self._manage_cache(self.text_embedding_cache, text, embedding)
        return embedding

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
    """
    def _extract_text_embedding_without_cache(self, text):
        提取文本特征向量（无缓存版本）
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
                        outputs = self.model.get_text_features(**inputs)
                        
                        # 1. 核心修复：把真正的特征张量(Tensor)从返回的对象里剥离出来
                        if hasattr(outputs, 'text_embeds'):
                            text_features = outputs.text_embeds
                        elif hasattr(outputs, 'pooler_output'):
                            text_features = outputs.pooler_output
                        elif isinstance(outputs, torch.Tensor):
                            text_features = outputs
                        else:
                            text_features = outputs[0]
                            
                        # 2. 安全地进行归一化计算
                        text_features = F.normalize(text_features, p=2, dim=-1)
                        
                        # 3. 存入列表 (跟原来保持一致)
                        embeddings.append(text_features.cpu().numpy()[0])
                except Exception:
                    # 尝试更激进的截断
                    try:
                        truncated_text = enhanced_text[:30] + "..."
                        inputs = self.processor(text=[truncated_text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                        inputs = {k: v.to(self.device) for k, v in inputs.items()}
                        
                        with torch.no_grad():
                            outputs = self.model.get_text_features(**inputs)
                            # 万能提取法
                            if hasattr(outputs, 'text_embeds'):
                                text_features = outputs.text_embeds
                            elif hasattr(outputs, 'pooler_output'):
                                text_features = outputs.pooler_output
                            elif isinstance(outputs, torch.Tensor):
                                text_features = outputs
                            else:
                                text_features = outputs[0]
                                
                            # 安全归一化
                            text_features = F.normalize(text_features, p=2, dim=-1)
                            # 保持原本的结尾不变
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
                        outputs = self.model.get_text_features(**inputs)
                        # 万能提取法
                        if hasattr(outputs, 'text_embeds'):
                            text_features = outputs.text_embeds
                        elif hasattr(outputs, 'pooler_output'):
                            text_features = outputs.pooler_output
                        elif isinstance(outputs, torch.Tensor):
                            text_features = outputs
                        else:
                            text_features = outputs[0]
                            
                        # 安全归一化
                        text_features = F.normalize(text_features, p=2, dim=-1)
                        # 保持原本的结尾不变
                        features_np = text_features.cpu().numpy()[0]
                        
                    return features_np
                except Exception:
                    # 尝试更激进的截断
                    truncated_text = text[:30] + "..."
                    inputs = self.processor(text=[truncated_text], return_tensors="pt", padding=True, truncation=True, max_length=77)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = self.model.get_text_features(**inputs)
                        # 万能提取法
                        if hasattr(outputs, 'text_embeds'):
                            text_features = outputs.text_embeds
                        elif hasattr(outputs, 'pooler_output'):
                            text_features = outputs.pooler_output
                        elif isinstance(outputs, torch.Tensor):
                            text_features = outputs
                        else:
                            text_features = outputs[0]
                            
                        # 安全归一化
                        text_features = F.normalize(text_features, p=2, dim=-1)
                        # 保持原本的结尾不变
                        features_np = text_features.cpu().numpy()[0]
                        
                    return features_np
        except Exception as e:
            error_msg = f"文本特征提取失败: {e}"
            logger.error(error_msg)
            return None
    """
    """def extract_text_embedding(self, text):
        提取文本特征向量（带缓存）
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
    """
    def calculate_weighted_similarity(self, base_similarity, node_properties, query_text=None):
        """
        终极完整版：图谱加权打分算法
        保留所有精细场景词库 + 修复列表类型错误 + 强化作者朝代召回
        """
        import re
        import numpy as np

        # 1. 基础余弦相似度非线性映射 (保留你原有的阶梯逻辑)
        similarity = float(base_similarity)
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
        
        # 2. 确定权重分配 (保留你原有的权重比例)
        if query_text is None:  # 以图搜图
            weights = {'cosine': 0.95, 'dynasty': 0.01, 'style': 0.01, 'description': 0.01, 'title': 0.01, 'scene': 0.01}
        elif similarity > 0.95:
            weights = {'cosine': 0.6, 'dynasty': 0.1, 'style': 0.1, 'description': 0.1, 'title': 0.05, 'scene': 0.05}
        else:
            weights = {'cosine': 0.4, 'dynasty': 0.1, 'style': 0.1, 'description': 0.2, 'title': 0.05, 'scene': 0.15}
        
        weighted_similarity = base_similarity * weights['cosine']
        
        # 3. 文本相关性深度加权
        if query_text:
            query_text = str(query_text).lower()
            boost_score = 0.0  # 🌟 新增：暴击得分

            # --- A. 属性类型安全转换辅助 (解决 list 报错) ---
            def get_safe_str(val):
                if isinstance(val, list): return " ".join([str(i) for i in val]).lower()
                return str(val or "").lower()

            # --- B. 朝代匹配 (加固版) ---
            dynasty = get_safe_str(node_properties.get('dynasty', ''))
            dynasty_keywords = ['宋代', '唐朝', '元代', '明代', '清代', '魏晋', '汉代', '三国', '五代', '辽金', '民国']
            for dk in dynasty_keywords:
                if dk in query_text and dk in dynasty:
                    boost_score += 0.4 # 🌟 朝代暴击
                    weighted_similarity += weights['dynasty']
                    break
            
            # --- C. 风格匹配 (加固版) ---
            style = get_safe_str(node_properties.get('style', ''))
            style_keywords = ['山水', '人物', '花鸟', '工笔', '水墨', '写意', '青绿', '浅绛']
            for sk in style_keywords:
                if sk in query_text and sk in style:
                    boost_score += 0.2 # 🌟 风格暴击
                    weighted_similarity += weights['style']
                    break
            
            # --- D. 作者匹配 (🌟 核心修复点：解决仇英搜不到的关键) ---
            author = get_safe_str(node_properties.get('author', ''))
            if author and author != '未知作者':
                if author in query_text or query_text in author:
                    boost_score += 0.8 # 🌟 作者暴击，直接送上第一名

            # --- E. 描述匹配与复合关键词 (原封不动还原你的逻辑) ---
            if 'description' in node_properties:
                description = get_safe_str(node_properties['description'])
                desc_keywords = re.findall(r'\b\w+\b', query_text)
                matched_keywords = 0
                query_chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', query_text)
                
                compound_patterns = [
                    r'宏伟壮丽', r'气势磅礴', r'壮丽宏伟', r'雄伟壮阔',
                    r'宁静致远', r'清新淡雅', r'古朴典雅', r'富丽堂皇',
                    r'山水画', r'人物画', r'花鸟画', r'工笔画',
                    r'水墨画', r'写意画', r'青绿山水', r'浅绛山水'
                ]
                
                # 统计基础关键词匹配
                for keyword in query_chinese_words:
                    if len(keyword) > 1 and keyword in description:
                        matched_keywords += 1
                
                # 统计复合关键词匹配 (权重翻倍)
                for cp in compound_patterns:
                    if cp in query_text and cp in description:
                        matched_keywords += 2 
                
                if query_chinese_words:
                    match_ratio = matched_keywords / (len(query_chinese_words) + 1)
                    weighted_similarity += weights['description'] * match_ratio * 2.5 # 稍微调高了比例

            # --- F. 标题匹配 ---
            title = get_safe_str(node_properties.get('title', ''))
            if query_text in title or title in query_text:
                weighted_similarity += weights['title']
            
            # --- G. 完整场景词库匹配 (原封不动还原你最全的词典) ---
            scene_keywords = {
                '骑马': ['骑马', '马', '骑行', '坐骑', '策马', '马背上', '骏马', '马匹', '马群', '骑马图', '骑马场景'],
                '秋日': ['秋日', '秋天', '秋季', '秋景', '秋风', '秋意', '秋高气爽', '秋色', '金秋', '秋景图'],
                '春日': ['春日', '春天', '春季', '春景', '春风', '春意', '春暖花开', '春色', '春景图'],
                '夏日': ['夏日', '夏天', '夏季', '夏景', '夏风', '夏意', '夏日炎炎', '夏景图'],
                '冬日': ['冬日', '冬天', '冬季', '冬景', '冬风', '冬意', '冬日严寒', '冬景图'],
                '山林': ['山林', '森林', '树林', '林木', '山林幽寂', '山林寂静', '山林图'],
                '山石': ['山石', '岩石', '石头', '石块', '石壁', '山石图'],
                '雪景': ['雪景', '雪', '雪花', '雪地', '雪景图', '冬日雪景'],
                '达官贵人': ['达官贵人', '官员', '贵人', '贵族', '士大夫', '官人'],
                '山水': ['山水', '山峰', '溪流', '山林', '山涧', '瀑布', '山水图', '山水画'],
                '人物': ['人物', '人像', '人物画', '人物形象', '人物描绘'],
                '花鸟': ['花鸟', '花卉', '鸟类', '鸟语花香', '花团锦簇'],
                '文人雅士': ['文人雅士', '文人墨客', '雅士', '文人', '学士'],
                '信步闲游': ['信步闲游', '漫步', '闲游', '散步', '游览'],
                '山间溪边': ['山间溪边', '山涧', '溪边', '溪流', '山水之间'],
                '远山巍峨': ['远山巍峨', '远山', '巍峨', '高山', '山峰高耸']
            }
            
            matched_scenes = 0
            total_scene_score = 0
            for scene, keywords in scene_keywords.items():
                if scene in query_text or any(k in query_text for k in keywords):
                    # 检查图谱属性中是否包含这些场景词
                    if any(kw in description or kw in title or kw in style for kw in keywords):
                        scene_score = weights['scene']
                        if scene in ['骑马', '秋日', '秋天']: scene_score *= 2.0 # 重要场景双倍
                        total_scene_score += scene_score
                        matched_scenes += 1
                        if matched_scenes >= 3: break # 最多统计3个场景
            
            weighted_similarity += total_scene_score

            # --- H. 最终融合暴击得分 ---
            weighted_similarity += boost_score

        # 4. 增加区分度 (保留你原有的高分段膨胀逻辑)
        if weighted_similarity > 0.85:
            weighted_similarity += 0.18
        elif weighted_similarity > 0.75:
            weighted_similarity += 0.12
        elif weighted_similarity > 0.65:
            weighted_similarity += 0.08

        # 5. 最终范围控制
        return min(1.0, max(0.1, weighted_similarity))

    def filter_and_rank_results(self, results, query_text=None):
        """过滤和排序搜索结果"""
        if not results:
            return []
        
        def safe_lower(val):
            if isinstance(val, list):
                return " ".join([str(i) for i in val]).lower()
            return str(val or "").lower()
        filtered_results = [r for r in results if r.get('similarity', 0) >= 0.1]
        
        # 如果结果不足，降低阈值以确保有足够的结果
        if len(filtered_results) < 3:
            filtered_results = [r for r in results if r['similarity'] >= 0.5]
        
        # 2. 更精细的排序，增强区分度
        def rank_key(result):
            # 基础相似度（权重更高，使用平方来增强区分度）
            score = result['similarity'] ** 2 * 200
            query = query_text.lower() if query_text else ""
            
            # 标题匹配加分 - 增加权重
            if query_text and 'title' in result:
                title = safe_lower(result.get('title'))
                query = query_text.lower()
                if query in title:
                    score += 30  # 增加标题匹配权重
                elif any(keyword in title for keyword in query.split()):
                    score += 20  # 增加部分匹配权重
            
            # 朝代匹配加分 - 增加权重
            if query_text and 'dynasty' in result and result['dynasty']:
                dynasty = safe_lower(result.get('dynasty'))
                query = query_text.lower()
                if any(keyword in query for keyword in dynasty.split()):
                    score += 15  # 增加朝代匹配权重
            
            # 风格匹配加分 - 增加权重
            if query_text and 'style' in result and result['style']:
                style = safe_lower(result.get('style'))
                query = query_text.lower()
                if any(keyword in query for keyword in style.split()):
                    score += 15  # 增加风格匹配权重
            
            # 作者匹配加分 - 增加权重
            if query_text and 'author' in result and result['author'] != '未知作者':
                author = safe_lower(result.get('author'))
                query = query_text.lower()
                if author in query:
                    score += 25  # 增加作者匹配权重
            
            # 描述匹配加分 - 增加权重和计算精度
            if query_text and 'description' in result and result['description']:
                description = safe_lower(result.get('description'))
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
                    """
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
                """
        
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
    
    def search_similar_images(self, query_embedding, search_label="Artwork", top_k=10, min_similarity=0.1, query_text=None):
        """搜索相似的图像，确保返回精确数量并包含完整信息"""
        results = []

        try:
            # 确保数据库已连接
            self._ensure_database_connected()
            
            # 获取所有节点
            nodes = list(self.matcher.match(search_label))
            
            # 并行处理节点
            all_results = []
            
            # 使用线程池并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # 提交所有任务
                future_to_node = {
                    executor.submit(self._process_node, node, search_label, query_embedding, min_similarity, query_text): node 
                    for node in nodes
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_node):
                    result = future.result()
                    if result:
                        all_results.append(result)

            # 过滤和排序结果
            filtered_results = self.filter_and_rank_results(all_results, query_text)

            # 确保返回精确的 top_k 个结果
            if len(filtered_results) >= top_k:
                results = filtered_results[:top_k]
            else:
                # 如果结果不足，返回所有找到的
                results = filtered_results

            return results

        except Exception as e:
            logger.error(f"搜索过程中出错: {e}")
            return []

    """新增"""
    def _hybrid_search(self, query_emb, top_k=10, query_text=None):
        """
        聚类聚合版：图谱融合检索
        1. FAISS 海选 200 张图
        2. 按 ID 聚类，同一画作仅显示一个结果
        3. 内部携带所有关联局部图 URL
        """
        self._ensure_database_connected()
        self._ensure_model_loaded()
        
        # 1. FAISS 海选：池子扩大到 200，保证合并后依然有足够的画作种类
        query_vector = np.array([query_emb], dtype=np.float32)
        faiss.normalize_L2(query_vector) 
        distances, indices = self.index.search(query_vector, 200)
        
        # 用于聚合的容器
        # 结构: { "ID123": {"data": {主结果}, "related_paths": [其他路径...]} }
        grouped_results = {}
        
        # 2. 遍历海选结果进行“认亲”和“归类”
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx == -1: continue
            
            img_path = self.paths_array[idx]  
            base_id = self.base_ids_list[idx] 
            base_sim = float(distances[0][i])
            
            # --- 情况 A: 这个 ID 之前已经出现过了（处理小弟） ---
            if base_id in grouped_results:
                # 记录这个关联图片的路径
                if img_path not in grouped_results[base_id]['related_paths']:
                    # 注意：第一个进来的已经是最高分的了，剩下的按顺序加进去
                    grouped_results[base_id]['related_paths'].append(img_path)
                continue # 小弟不需要再查图谱和打分了
                
            # --- 情况 B: 这个 ID 是第一次出现（处理带头大哥） ---
            # 只有大哥需要查 Neo4j 拉取身世档案
            meta = self._get_graph_metadata(base_id)
            
            if meta:
                entity_type = meta.get('entity_type', 'Artwork')
                author_display = meta.get('author') or '未知'
                if entity_type == 'ArtistPortrait':
                    author_display = '无特定作者'
                
                # 准备属性给打分函数
                node_properties = {
                    'title': meta.get('title') or '未知',
                    'description': meta.get('description') or '',
                    'dynasty': meta.get('dynasty') or '',
                    'author': author_display,
                    'style': meta.get('style') or '',
                    'seal_content': meta.get('seal_content', ''),
                    'entity_type': entity_type
                }
                
                # 调用你的王牌加权打分算法 (包含了 0.8 作者暴击逻辑)
                final_similarity = self.calculate_weighted_similarity(base_sim, node_properties, query_text)
                
                # 只有及格的才准入选 (阈值可调)
                if final_similarity > 0.05:
                    grouped_results[base_id] = {
                        "main_result": {
                            'similarity': final_similarity,
                            'node_type': entity_type,
                            'title': node_properties['title'],
                            'author': node_properties['author'],
                            'dynasty': node_properties['dynasty'],
                            'style': node_properties['style'],
                            'description': node_properties['description'],
                            'content': meta.get('seal_content', ''),
                            # 大哥的封面图：就是 200 张里最像的那张
                            'image_url': self._get_artwork_image_url(img_path),
                            'properties': node_properties 
                        },
                        "related_paths": [img_path] # 把自己也放进路径池，方便展示
                    }

        # 3. 结果平铺与 URL 转化
        all_results = []
        for base_id, data in grouped_results.items():
            result_item = data["main_result"]
            
            # 🌟 把这一组里所有的局部图全部转化成 URL，发给前端
            # 我们按照 FAISS 返回的相似度顺序排好
            all_related_urls = []
            for p in data["related_paths"]:
                all_related_urls.append(self._get_artwork_image_url(p))
            
            result_item["related_images"] = all_related_urls 
            result_item["related_count"] = len(all_related_urls)
            
            all_results.append(result_item)
        
        # 4. 最终大排名：对“画作组”进行综合排序
        # 这样即使用户搜“仇英”，即便仇英的某张图排在 FAISS 第 100 名，
        # 它也会因为打分加权冲到 list 的第一名。
        final_ranked = self.filter_and_rank_results(all_results, query_text)
        
        return final_ranked[:top_k]

    def _get_graph_metadata(self, base_id):
        """拿着 ID 去图谱里拉取【全属性】档案 (适配属性化重构后的结构)"""
        self._ensure_database_connected()
        if not hasattr(self, 'graph') or not self.graph:
            return None
            
        # 🌟 极简查询：直接取节点身上的属性，速度比查连线快 10 倍
        query = """
        MATCH (node) 
        WHERE node.id = $base_id 
          AND (node:Artwork OR node:ArtistPortrait OR node:Inscription OR node:Seal)
        
        RETURN node.title AS title, 
               node.description AS description, 
               node.mediaType AS medium,
               node.content AS seal_content,
               node.shape AS seal_shape,
               node.author AS author, 
               node.dynasty AS dynasty, 
               // 🌟 注意：这里直接读 category 属性作为 style
               node.category AS style,
               node.entity_type AS entity_type
        """
        try:
            record = self.graph.run(query, base_id=base_id).data()
            if record:
                return record[0]
        except Exception as e:
            print(f"⚠️ 图谱查询异常: {e}")
        return None

    def _get_complete_artwork_info(self, artwork_title):
        """获取作品的完整信息，包括作者和朝代"""
        try:
            query = """
            MATCH (a:Artwork {title: $title})
            OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
            OPTIONAL MATCH (a)-[:PART_OF]->(dynasty:Dynasty)
            OPTIONAL MATCH (artist)-[:LIVED_IN]->(artist_dynasty:Dynasty)
            RETURN 
                artist.name as author,
                dynasty.name as artwork_dynasty,
                artist_dynasty.name as artist_dynasty,
                artist.style as artist_style
            """
            result = self.graph.run(query, title=artwork_title).data()

            info = {}
            if result:
                data = result[0]
                # 优先使用作品的朝代，如果没有则使用作者的朝代
                dynasty = data.get('artwork_dynasty') or data.get('artist_dynasty')
                author = data.get('author')

                if author:
                    info['author'] = author
                if dynasty:
                    info['dynasty'] = dynasty
                if data.get('artist_style'):
                    info['artist_style'] = data['artist_style']

            # 如果没有通过关系找到，尝试从节点属性中获取
            if not info.get('dynasty'):
                # 尝试直接查询Artwork节点的dynasty属性
                artwork_query = """
                MATCH (a:Artwork {title: $title})
                RETURN a.dynasty as dynasty
                """
                result = self.graph.run(artwork_query, title=artwork_title).data()
                if result and result[0].get('dynasty'):
                    info['dynasty'] = result[0]['dynasty']

            return info
        except Exception as e:
            logger.error(f"获取作品完整信息失败: {e}")
            return {}

    def _get_artwork_image_url(self, img_path):
        """
        根据向量库中记录的相对路径获取图片URL
        输入示例: "artworks/60d5bb8f6155e14a09d16681_0.jpg"
        """
        try:
            if not img_path:
                return None

            full_path = os.path.join(self.image_root_dir, img_path)

            if os.path.exists(full_path):
                safe_path = str(img_path).replace('\\', '/')
                return f"/artwork_image/{safe_path}"

            logger.warning(f"磁盘上找不到图片文件: {full_path}")
            return None
            
        except Exception as e:
            logger.error(f"获取图片URL失败: {e}")
            return None

    def search_by_image(self, image_path, top_k=5):
        """以图搜图接口"""
        logger.info(f"开始处理图片: {image_path}")
        query_emb = self.extract_image_embedding(image_path)
        if query_emb is None:
            return {"error": "图像特征提取失败"}

        # 直接调用重写后的融合搜索架构
        artwork_results = self._hybrid_search(query_emb, top_k, query_text=None)

        return {
            "artworks": artwork_results,
            "seals": [],         # 印章和题跋库如果没有建 FAISS，暂返空列表
            "inscriptions": []
        }

    def search_by_author(self, author, top_k=5):
        """按作者精确搜索"""
        try:
            logger.info(f"按作者搜索: {author}")
            
            # 精确匹配作者
            query = """
            MATCH (a:Artwork)-[:CREATED_BY]->(artist:Artist)
            WHERE artist.name CONTAINS $author OR $author CONTAINS artist.name
            RETURN a, artist.name as author_name
            ORDER BY artist.name
            """
            
            results = self.graph.run(query, author=author).data()
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
                    'image_url': self._find_image_url_by_id(node_properties.get('id', ''))
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
                    'image_url': self._find_image_url_by_id(node_properties.get('id', ''))
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

    def search_by_text(self, text, top_k=5):
        """以文搜图接口"""
        logger.info(f"以文搜图: {text}")
        query_emb = self.extract_text_embedding(text)
        if query_emb is None:
            return {"error": "文本特征提取失败"}

        # 直接调用重写后的融合搜索架构
        artwork_results = self._hybrid_search(query_emb, top_k, query_text=text)

        return {
            "artworks": artwork_results,
            "seals": [],
            "inscriptions": []
        }

    def _get_artwork_image_url(self, img_path):
        """
        带调试信息的图片 URL 生成器
        """
        # 如果路径是空的或者是字符串 "None"
        if not img_path or str(img_path) == "None" or str(img_path) == "不详":
            return "/static/default_art.png"
        
        try:
            # 🌟 调试打印：看看 FAISS 吐出来的原始路径到底是什么
            # print(f"DEBUG: FAISS 原始路径 ===> {img_path}")

            # 1. 统一斜杠
            safe_path = str(img_path).replace("\\", "/")
            
            # 2. URL 编码（处理中文）
            encoded_path = urllib.parse.quote(safe_path)
            
            # 3. 拼接路由
            final_url = f"/api/get_image?path={encoded_path}"
            return final_url
            
        except Exception as e:
            # 🌟 调试打印：如果这里报错，控制台会打印出具体原因
            print(f"❌ 路径转换失败！错误原因: {e}")
            return "/static/default_art.png"

