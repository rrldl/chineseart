#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量对齐实体脚本 - 增强版
支持多类型实体对齐、配置化处理、详细统计和报告
"""
from la_clip_alignment import LAClipAlignmentService
from dotenv import load_dotenv
import os
import time
import random
import argparse
from datetime import datetime

class EnhancedBatchAligner:
    """增强版批量对齐器"""
    
    def __init__(self, config=None):
        """初始化"""
        load_dotenv()
        
        # 配置参数
        self.config = config or {}
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "Zyr123456")
        
        # 初始化对齐服务
        self.service = LAClipAlignmentService(
            self.neo4j_uri,
            self.neo4j_user,
            self.neo4j_password
        )
        
        # 统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "entity_types": {}
        }
        
        # 支持的实体类型
        self.supported_entity_types = {
            "Artist": "艺术家",
            "Artwork": "艺术品",
            "Style": "艺术流派",
            "HistoricalEvent": "历史事件",
            "Material": "材料",
            "Technique": "技术",
            "Theme": "主题",
            "Period": "时期",
            "Museum": "博物馆",
            "Collector": "收藏家"
        }
    
    def generate_text_description(self, entity_id, entity_type):
        """生成更准确的文本描述"""
        descriptions = {
            "Artist": f"{entity_id}是中国古代著名书画家，擅长绘画和书法，在艺术史上具有重要地位。",
            "Artwork": f"{entity_id}是中国古代著名绘画作品，具有极高的艺术价值和历史意义。",
            "Style": f"{entity_id}是中国重要的艺术流派，对后世艺术发展产生了深远影响。",
            "HistoricalEvent": f"{entity_id}是中国历史上的重要事件，对文化艺术发展产生了重要影响。",
            "Material": f"{entity_id}是中国传统书画创作中使用的重要材料。",
            "Technique": f"{entity_id}是中国传统书画创作中的重要技法。",
            "Theme": f"{entity_id}是中国传统书画作品中的常见主题。",
            "Period": f"{entity_id}是中国历史上的重要时期，艺术发展繁荣。",
            "Museum": f"{entity_id}是收藏中国传统书画作品的重要机构。",
            "Collector": f"{entity_id}是中国历史上著名的艺术品收藏家。"
        }
        return descriptions.get(entity_type, f"{entity_id}，中国传统文化相关实体。")
    
    def find_image_paths(self, entity_id, entity_type):
        """更智能的图像查找"""
        image_paths = []
        
        # 定义不同实体类型的图像路径模式
        path_patterns = {
            "Artwork": [
                f"artwork_images/artworks/{entity_id}.jpg",
                f"artwork_images/artworks/{entity_id}.jpeg",
                f"artwork_images/artworks/{entity_id}.png",
                f"images/artworks/{entity_id}.jpg",
                f"data/images/{entity_id}.jpg"
            ],
            "Artist": [
                f"artwork_images/artists/{entity_id}.jpg",
                f"images/artists/{entity_id}.jpg",
                f"data/images/artists/{entity_id}.jpg"
            ]
        }
        
        # 获取当前实体类型的路径模式
        patterns = path_patterns.get(entity_type, [])
        
        # 遍历所有可能的路径
        for path in patterns:
            if os.path.exists(path):
                image_paths.append(path)
                # 最多添加3个图像路径
                if len(image_paths) >= 3:
                    break
        
        return image_paths
    
    def align_with_retry(self, entity_id, entity_type, texts=None, max_retries=3):
        """带重试的对齐"""
        if texts is None:
            texts = []
        
        # 生成文本描述
        if not texts:
            texts = [self.generate_text_description(entity_id, entity_type)]
        
        # 确保文本长度合理
        processed_texts = []
        for text in texts:
            # 限制文本长度，确保模型能有效处理
            if len(text) > 100:
                processed_texts.append(text[:100])
            else:
                processed_texts.append(text)
        
        # 初始化实体类型统计
        if entity_type not in self.stats["entity_types"]:
            self.stats["entity_types"][entity_type] = {"success": 0, "failure": 0}
        
        # 带重试的对齐
        for attempt in range(max_retries):
            try:
                # 查找图像路径
                image_paths = self.find_image_paths(entity_id, entity_type)
                
                # 进度显示
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 对齐 [{entity_type}]: {entity_id} (尝试 {attempt+1}/{max_retries})")
                print(f"  文本描述: {processed_texts[0][:50]}..." if len(processed_texts[0]) > 50 else f"  文本描述: {processed_texts[0]}")
                print(f"  图像数量: {len(image_paths)}")
                
                # 执行对齐
                result = self.service.align_entity(
                    entity_id,
                    entity_type,
                    image_paths=image_paths,
                    texts=processed_texts
                )
                
                if result:
                    # 更新统计
                    self.stats["success"] += 1
                    self.stats["entity_types"][entity_type]["success"] += 1
                    
                    # 输出成功信息
                    confidence = result.get('confidence', 'N/A')
                    consistency = result.get('consistency_score', 'N/A')
                    print(f"✓ 成功: {entity_id}")
                    print(f"  置信度: {confidence:.2f}" if isinstance(confidence, (int, float)) else f"  置信度: {confidence}")
                    print(f"  一致性: {consistency:.2f}" if isinstance(consistency, (int, float)) else f"  一致性: {consistency}")
                    return True
                else:
                    print(f"✗ 失败: {entity_id}")
                    
            except Exception as e:
                print(f"✗ 异常: {entity_id} - {str(e)}")
            
            # 随机延迟，避免请求过于频繁
            if attempt < max_retries - 1:
                delay = random.uniform(1, 3)
                print(f"等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
        
        # 更新失败统计
        self.stats["failure"] += 1
        self.stats["entity_types"][entity_type]["failure"] += 1
        return False
    
    def load_entities_from_directory(self, entity_type, directory_pattern):
        """从目录加载实体列表"""
        entities = []
        if os.path.exists("data/encyclopedia"):
            for filename in os.listdir("data/encyclopedia"):
                if directory_pattern in filename:
                    entity_name = filename.replace(directory_pattern, "")
                    entities.append(entity_name)
        return entities
    
    def align_artists(self, limit=None):
        """对齐艺术家"""
        print("\n=== 开始对齐艺术家 ===")
        
        # 从目录加载艺术家列表
        artists = self.load_entities_from_directory("Artist", "_Artist.json")
        
        # 如果目录中没有，使用默认列表
        if not artists:
            artists = [
                "顾恺之", "吴道子", "王维", "李思训", "荆浩", "关仝", "董源", "巨然",
                "李成", "范宽", "郭熙", "李唐", "刘松年", "马远", "夏圭", "赵孟頫",
                "黄公望", "吴镇", "倪瓒", "王蒙", "沈周", "文徵明", "唐寅", "仇英",
                "徐渭", "董其昌", "陈洪绶", "八大山人", "石涛", "郑板桥", "金农",
                "齐白石", "张大千", "徐悲鸿", "潘天寿", "傅抱石", "李可染"
            ]
        
        total = len(artists)
        if limit:
            artists = artists[:limit]
            total = limit
        
        print(f"准备对齐 {total} 位艺术家")
        self.stats["total"] += total
        
        for artist in artists:
            texts = [self.generate_text_description(artist, "Artist")]
            self.align_with_retry(artist, "Artist", texts)
        
        print(f"\n艺术家对齐完成: 成功 {self.stats['entity_types'].get('Artist', {}).get('success', 0)}, 失败 {self.stats['entity_types'].get('Artist', {}).get('failure', 0)}")
    
    def align_artworks(self, limit=None):
        """对齐艺术品"""
        print("\n=== 开始对齐艺术品 ===")
        
        # 常见艺术品列表
        artworks = [
            "清明上河图", "千里江山图", "富春山居图", "汉宫春晓图", "百骏图",
            "洛神赋图", "步辇图", "唐宫仕女图", "五牛图", "韩熙载夜宴图",
            "搜山图", "长江万里图", "黄河万里图", "华山图", "泰山图",
            "黄山图", "庐山图", "峨眉山图", "衡山图", "恒山图",
            "嵩山图", "溪山行旅图", "雪景寒林图", "早春图", "万壑松风图",
            "枯木怪石图", "芙蓉锦鸡图", "千里江山图卷", "富春山居图卷",
            "虢国夫人游春图", "捣练图", "挥扇仕女图", "簪花仕女图", "八十七神仙卷"
        ]
        
        total = len(artworks)
        if limit:
            artworks = artworks[:limit]
            total = limit
        
        print(f"准备对齐 {total} 件艺术品")
        self.stats["total"] += total
        
        for artwork in artworks:
            texts = [self.generate_text_description(artwork, "Artwork")]
            self.align_with_retry(artwork, "Artwork", texts)
        
        print(f"\n艺术品对齐完成: 成功 {self.stats['entity_types'].get('Artwork', {}).get('success', 0)}, 失败 {self.stats['entity_types'].get('Artwork', {}).get('failure', 0)}")
    
    def align_styles(self, limit=None):
        """对齐艺术流派"""
        print("\n=== 开始对齐艺术流派 ===")
        
        # 从目录加载艺术流派列表
        styles = self.load_entities_from_directory("Style", "_Style.json")
        
        # 如果目录中没有，使用默认列表
        if not styles:
            styles = [
                "吴门画派", "松江派", "娄东派", "虞山派", "新安画派",
                "金陵八家", "扬州八怪", "海上画派", "岭南画派", "京津画派",
                "院体画", "文人画", "青绿山水", "水墨山水", "工笔重彩",
                "写意画", "白描画", "没骨画", "界画", "减笔画"
            ]
        
        total = len(styles)
        if limit:
            styles = styles[:limit]
            total = limit
        
        print(f"准备对齐 {total} 个艺术流派")
        self.stats["total"] += total
        
        for style in styles:
            texts = [self.generate_text_description(style, "Style")]
            self.align_with_retry(style, "Style", texts)
        
        print(f"\n艺术流派对齐完成: 成功 {self.stats['entity_types'].get('Style', {}).get('success', 0)}, 失败 {self.stats['entity_types'].get('Style', {}).get('failure', 0)}")
    
    def align_historical_events(self, limit=None):
        """对齐历史事件"""
        print("\n=== 开始对齐历史事件 ===")
        
        # 重要历史事件列表
        events = [
            "元祐党争", "靖康之变", "乾嘉学派", "洋务运动", "戊戌变法",
            "辛亥革命", "新文化运动", "五四运动", "抗日战争", "解放战争",
            "贞观之治", "开元盛世", "安史之乱", "靖康之耻", "绍兴和议",
            "永乐盛世", "康乾盛世", "鸦片战争", "太平天国", "甲午战争"
        ]
        
        total = len(events)
        if limit:
            events = events[:limit]
            total = limit
        
        print(f"准备对齐 {total} 个历史事件")
        self.stats["total"] += total
        
        for event in events:
            texts = [self.generate_text_description(event, "HistoricalEvent")]
            self.align_with_retry(event, "HistoricalEvent", texts)
        
        print(f"\n历史事件对齐完成: 成功 {self.stats['entity_types'].get('HistoricalEvent', {}).get('success', 0)}, 失败 {self.stats['entity_types'].get('HistoricalEvent', {}).get('failure', 0)}")
    
    def align_materials_and_techniques(self):
        """对齐材料和技术"""
        print("\n=== 开始对齐材料和技术 ===")
        
        # 材料列表
        materials = ["宣纸", "绢帛", "毛笔", "墨锭", "颜料", "砚台", "印泥", "印章"]
        # 技术列表
        techniques = ["工笔", "写意", "没骨", "白描", "泼墨", "破墨", "积墨", "焦墨"]
        
        print(f"准备对齐 {len(materials)} 种材料和 {len(techniques)} 种技术")
        self.stats["total"] += len(materials) + len(techniques)
        
        # 对齐材料
        for material in materials:
            texts = [self.generate_text_description(material, "Material")]
            self.align_with_retry(material, "Material", texts)
        
        # 对齐技术
        for technique in techniques:
            texts = [self.generate_text_description(technique, "Technique")]
            self.align_with_retry(technique, "Technique", texts)
        
        print(f"\n材料和技术对齐完成")
    
    def generate_report(self):
        """生成详细报告"""
        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        print("\n" + "="*80)
        print("=== 批量对齐详细报告 ===")
        print("="*80)
        print(f"开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"总处理实体: {self.stats['total']}")
        print(f"成功: {self.stats['success']}")
        print(f"失败: {self.stats['failure']}")
        print(f"成功率: {self.stats['success']/self.stats['total']*100:.2f}%" if self.stats['total'] > 0 else "0.00%")
        print()
        print("各实体类型统计:")
        print("-"*40)
        
        for entity_type, counts in self.stats['entity_types'].items():
            success = counts.get('success', 0)
            failure = counts.get('failure', 0)
            total = success + failure
            if total > 0:
                rate = success/total*100
                print(f"{entity_type}: 成功 {success}, 失败 {failure}, 成功率 {rate:.2f}%")
        
        print("="*80)
        print("=== 报告结束 ===")
        print("="*80)
    
    def run_batch_align(self, entity_types=None, limit=None):
        """运行批量对齐"""
        print("=== 开始批量对齐实体 ===")
        print(f"目标实体类型: {entity_types or '所有类型'}")
        print(f"每类限制数量: {limit or '无限制'}")
        print()
        
        # 确定要对齐的实体类型
        target_types = entity_types or list(self.supported_entity_types.keys())
        
        # 执行对齐
        if "Artist" in target_types:
            self.align_artists(limit)
        
        if "Artwork" in target_types:
            self.align_artworks(limit)
        
        if "Style" in target_types:
            self.align_styles(limit)
        
        if "HistoricalEvent" in target_types:
            self.align_historical_events(limit)
        
        if any(t in target_types for t in ["Material", "Technique"]):
            self.align_materials_and_techniques()
        
        # 生成报告
        self.generate_report()
        
        print("\n=== 批量对齐完成 ===")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="批量对齐实体脚本")
    parser.add_argument("--types", nargs="*", choices=[
        "Artist", "Artwork", "Style", "HistoricalEvent", 
        "Material", "Technique", "Theme", "Period", 
        "Museum", "Collector"
    ], help="指定要对齐的实体类型")
    parser.add_argument("--limit", type=int, help="每类实体的处理数量限制")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    args = parser.parse_args()
    
    # 加载配置
    config = None
    if args.config and os.path.exists(args.config):
        import json
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 初始化对齐器
    aligner = EnhancedBatchAligner(config)
    
    # 运行批量对齐
    aligner.run_batch_align(entity_types=args.types, limit=args.limit)

if __name__ == "__main__":
    main()