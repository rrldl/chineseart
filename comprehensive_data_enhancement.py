#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
综合数据增强脚本 - 添加新节点类型并优化数据质量
"""
import os
import json
from py2neo import Graph, Node, Relationship
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 连接Neo4j
neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "Zyr123456")

graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))

class DataEnhancer:
    """数据增强类"""
    
    def __init__(self):
        """初始化"""
        self.added_nodes = 0
        self.added_relationships = 0
    
    def add_material_nodes(self):
        """添加材料类型节点"""
        print("=== 添加材料类型节点 ===")
        
        materials = [
            "纸本", "绢本", "麻纸", "宣纸", "皮纸", "竹纸", 
            "金笺", "银笺", "磁青纸", "藏经纸", "高丽纸", 
            "木板", "石壁", "陶瓷", "丝绸"
        ]
        
        for material in materials:
            node = Node("Material", name=material)
            graph.merge(node, "Material", "name")
            self.added_nodes += 1
            print(f"添加材料: {material}")
        
        print(f"\n添加材料节点: {len(materials)} 个")
        print()
    
    def add_technique_nodes(self):
        """添加技法类型节点"""
        print("=== 添加技法类型节点 ===")
        
        techniques = [
            "工笔", "写意", "兼工带写", "白描", "没骨", 
            "青绿", "浅绛", "水墨", "金碧", "界画", 
            "指头画", "减笔", "大写意", "小写意", "工笔重彩", 
            "工笔淡彩", "泼墨", "破墨", "积墨", "焦墨"
        ]
        
        for technique in techniques:
            node = Node("Technique", name=technique)
            graph.merge(node, "Technique", "name")
            self.added_nodes += 1
            print(f"添加技法: {technique}")
        
        print(f"\n添加技法节点: {len(techniques)} 个")
        print()
    
    def add_theme_nodes(self):
        """添加主题类型节点"""
        print("=== 添加主题类型节点 ===")
        
        themes = [
            "山水", "人物", "花鸟", "走兽", "鱼虫", 
            "楼阁", "车马", "历史故事", "神话传说", "宗教", 
            "风俗", "肖像", "仕女", "婴戏", "田园", 
            "边塞", "宫廷", "文人雅集", "四季景色", "晨昏景色"
        ]
        
        for theme in themes:
            node = Node("Theme", name=theme)
            graph.merge(node, "Theme", "name")
            self.added_nodes += 1
            print(f"添加主题: {theme}")
        
        print(f"\n添加主题节点: {len(themes)} 个")
        print()
    
    def add_period_nodes(self):
        """添加时期类型节点"""
        print("=== 添加时期类型节点 ===")
        
        periods = [
            "原始社会", "奴隶社会", "封建社会", "近代", "现代", "当代",
            "先秦", "秦汉", "魏晋南北朝", "隋唐", "五代", "宋元", "明清"
        ]
        
        for period in periods:
            node = Node("Period", name=period)
            graph.merge(node, "Period", "name")
            self.added_nodes += 1
            print(f"添加时期: {period}")
        
        print(f"\n添加时期节点: {len(periods)} 个")
        print()
    
    def enhance_artist_relationships(self):
        """增强艺术家关联关系"""
        print("=== 增强艺术家关联关系 ===")
        
        # 为艺术家添加代表作品关系
        artist_works = {
            "张择端": ["清明上河图"],
            "王希孟": ["千里江山图"],
            "黄公望": ["富春山居图"],
            "唐寅": ["汉宫春晓图", "步溪图"],
            "文徵明": ["墨竹图"],
            "仇英": ["汉宫春晓图"],
            "八大山人": ["荷花水鸟图"],
            "石涛": ["搜山图"],
            "郑板桥": ["墨竹图"],
            "顾恺之": ["洛神赋图", "女史箴图"],
            "吴道子": ["送子天王图"],
            "阎立本": ["步辇图"],
            "韩滉": ["五牛图"],
            "李思训": ["江帆楼阁图"],
            "李昭道": ["明皇幸蜀图"],
            "王维": ["辋川图"],
            "张萱": ["虢国夫人游春图"],
            "周昉": ["簪花仕女图"],
            "韩干": ["牧马图"],
            "董源": ["潇湘图"],
            "巨然": ["层岩丛树图"],
            "范宽": ["溪山行旅图"],
            "郭熙": ["早春图"],
            "李公麟": ["五马图"],
            "米芾": ["春山瑞松图"],
            "米友仁": ["潇湘奇观图"],
            "赵孟頫": ["鹊华秋色图", "秋郊饮马图"],
            "倪瓒": ["容膝斋图"],
            "王蒙": ["青卞隐居图"],
            "吴镇": ["渔父图"]
        }
        
        for artist_name, works in artist_works.items():
            # 查找艺术家节点
            artist = graph.run(f"MATCH (a:Artist {{name: '{artist_name}'}}) RETURN a").evaluate()
            if not artist:
                continue
            
            for work_title in works:
                # 查找或创建作品节点
                work = graph.run(f"MATCH (w:Artwork {{title: '{work_title}'}}) RETURN w").evaluate()
                if not work:
                    work = Node("Artwork", title=work_title)
                    graph.merge(work, "Artwork", "title")
                    self.added_nodes += 1
                
                # 创建创作关系
                rel = Relationship(work, "CREATED_BY", artist)
                graph.merge(rel)
                self.added_relationships += 1
                print(f"{artist_name} → {work_title}")
        
        print(f"\n增强艺术家关联: 添加 {self.added_relationships} 个关系")
        print()
    
    def enhance_style_relationships(self):
        """增强风格关联关系"""
        print("=== 增强风格关联关系 ===")
        
        # 为风格添加代表作品
        style_works = {
            "工笔画": ["清明上河图", "千里江山图", "汉宫春晓图"],
            "写意画": ["墨竹图", "泼墨仙人图"],
            "山水画": ["富春山居图", "溪山行旅图", "早春图"],
            "人物画": ["洛神赋图", "步辇图", "簪花仕女图"],
            "花鸟画": ["芙蓉锦鸡图"],
            "吴门画派": ["汉宫春晓图", "墨竹图"],
            "岭南画派": ["江山如此多娇"],
            "北方山水画派": ["溪山行旅图"],
            "南方山水画派": ["潇湘图"],
            "青绿山水": ["千里江山图", "江帆楼阁图"],
            "浅绛山水": ["富春山居图"],
            "水墨山水": ["渔父图"]
        }
        
        added_rels = 0
        for style_name, works in style_works.items():
            # 查找风格节点
            style = graph.run(f"MATCH (s:Style {{name: '{style_name}'}}) RETURN s").evaluate()
            if not style:
                continue
            
            for work_title in works:
                # 查找或创建作品节点
                work = graph.run(f"MATCH (w:Artwork {{title: '{work_title}'}}) RETURN w").evaluate()
                if not work:
                    work = Node("Artwork", title=work_title)
                    graph.merge(work, "Artwork", "title")
                    self.added_nodes += 1
                
                # 创建风格关系
                rel = Relationship(work, "HAS_STYLE", style)
                graph.merge(rel)
                added_rels += 1
                print(f"{work_title} → {style_name}")
        
        self.added_relationships += added_rels
        print(f"\n增强风格关联: 添加 {added_rels} 个关系")
        print()
    
    def add_historical_event_impacts(self):
        """添加历史事件对艺术的影响"""
        print("=== 添加历史事件影响 ===")
        
        event_impacts = {
            "靖康之变": ["宋代绘画", "文人画"],
            "乾隆盛世": ["宫廷绘画", "金石学"],
            "鸦片战争": ["海上画派", "近代绘画"],
            "洋务运动": ["西画东渐", "现代绘画"],
            "辛亥革命": ["新美术运动", "现代绘画"],
            "元祐党争": ["宋代绘画", "文人画"],
            "三藩之乱": ["清代绘画", "正统派"],
            "太平天国运动": ["民间绘画", "地方画派"],
            "戊戌变法": ["维新美术", "现代绘画"],
            "庚子事变": ["中西融合", "现代绘画"]
        }
        
        added_rels = 0
        for event_name, styles in event_impacts.items():
            # 查找历史事件节点
            event = graph.run(f"MATCH (e:HistoricalEvent {{name: '{event_name}'}}) RETURN e").evaluate()
            if not event:
                continue
            
            for style_name in styles:
                # 查找或创建风格节点
                style = graph.run(f"MATCH (s:Style {{name: '{style_name}'}}) RETURN s").evaluate()
                if not style:
                    style = Node("Style", name=style_name)
                    graph.merge(style, "Style", "name")
                    self.added_nodes += 1
                
                # 创建影响关系
                rel = Relationship(event, "INFLUENCED", style)
                graph.merge(rel)
                added_rels += 1
                print(f"{event_name} → {style_name}")
        
        self.added_relationships += added_rels
        print(f"\n添加历史事件影响: 添加 {added_rels} 个关系")
        print()
    
    def add_artwork_details(self):
        """添加艺术品详细信息"""
        print("=== 添加艺术品详细信息 ===")
        
        artwork_details = {
            "清明上河图": {
                "material": "绢本",
                "technique": "工笔",
                "theme": "风俗",
                "period": "宋代"
            },
            "千里江山图": {
                "material": "绢本",
                "technique": "青绿",
                "theme": "山水",
                "period": "宋代"
            },
            "富春山居图": {
                "material": "纸本",
                "technique": "水墨",
                "theme": "山水",
                "period": "元代"
            },
            "汉宫春晓图": {
                "material": "绢本",
                "technique": "工笔",
                "theme": "人物",
                "period": "明代"
            },
            "洛神赋图": {
                "material": "绢本",
                "technique": "工笔",
                "theme": "历史故事",
                "period": "魏晋南北朝"
            },
            "步辇图": {
                "material": "绢本",
                "technique": "工笔",
                "theme": "历史故事",
                "period": "唐代"
            },
            "五牛图": {
                "material": "纸本",
                "technique": "工笔",
                "theme": "走兽",
                "period": "唐代"
            },
            "韩熙载夜宴图": {
                "material": "绢本",
                "technique": "工笔",
                "theme": "风俗",
                "period": "五代"
            },
            "溪山行旅图": {
                "material": "绢本",
                "technique": "水墨",
                "theme": "山水",
                "period": "宋代"
            },
            "早春图": {
                "material": "绢本",
                "technique": "水墨",
                "theme": "山水",
                "period": "宋代"
            }
        }
        
        added_rels = 0
        for artwork_title, details in artwork_details.items():
            # 查找艺术品节点
            artwork = graph.run(f"MATCH (a:Artwork {{title: '{artwork_title}'}}) RETURN a").evaluate()
            if not artwork:
                continue
            
            # 添加材料关系
            if material := details.get('material'):
                material_node = graph.run(f"MATCH (m:Material {{name: '{material}'}}) RETURN m").evaluate()
                if material_node:
                    rel = Relationship(artwork, "MADE_OF", material_node)
                    graph.merge(rel)
                    added_rels += 1
            
            # 添加技法关系
            if technique := details.get('technique'):
                technique_node = graph.run(f"MATCH (t:Technique {{name: '{technique}'}}) RETURN t").evaluate()
                if technique_node:
                    rel = Relationship(artwork, "USES_TECHNIQUE", technique_node)
                    graph.merge(rel)
                    added_rels += 1
            
            # 添加主题关系
            if theme := details.get('theme'):
                theme_node = graph.run(f"MATCH (th:Theme {{name: '{theme}'}}) RETURN th").evaluate()
                if theme_node:
                    rel = Relationship(artwork, "HAS_THEME", theme_node)
                    graph.merge(rel)
                    added_rels += 1
            
            # 添加时期关系
            if period := details.get('period'):
                period_node = graph.run(f"MATCH (p:Period {{name: '{period}'}}) RETURN p").evaluate()
                if period_node:
                    rel = Relationship(artwork, "FROM_PERIOD", period_node)
                    graph.merge(rel)
                    added_rels += 1
            
            print(f"增强: {artwork_title}")
        
        self.added_relationships += added_rels
        print(f"\n添加艺术品详细信息: 添加 {added_rels} 个关系")
        print()
    
    def run_enhancement(self):
        """运行完整的数据增强"""
        print("=== 综合数据增强开始 ===")
        print()
        
        # 重置计数器
        self.added_nodes = 0
        self.added_relationships = 0
        
        # 添加新节点类型
        self.add_material_nodes()
        self.add_technique_nodes()
        self.add_theme_nodes()
        self.add_period_nodes()
        
        # 增强现有关系
        self.enhance_artist_relationships()
        self.enhance_style_relationships()
        self.add_historical_event_impacts()
        self.add_artwork_details()
        
        # 检查最终状态
        self.check_final_status()
        
        print("=== 综合数据增强完成 ===")
    
    def check_final_status(self):
        """检查最终状态"""
        print("=== 最终状态检查 ===")
        
        # 总节点数
        total_nodes = graph.run('MATCH (n) RETURN count(n)').evaluate()
        print(f"总节点数: {total_nodes}")
        
        # 总关系数
        total_rels = graph.run('MATCH ()-[r]->() RETURN count(r)').evaluate()
        print(f"总关系数: {total_rels}")
        
        # 新增统计
        print(f"\n本次增强:")
        print(f"- 新增节点: {self.added_nodes}")
        print(f"- 新增关系: {self.added_relationships}")
        
        # 节点类型分布
        print("\n=== 节点类型分布 ===")
        node_types = ["Artist", "Artwork", "Style", "HistoricalEvent", "Dynasty", "Collection", "Seal", "Inscription", "Person", "AlignmentNode", "Material", "Technique", "Theme", "Period"]
        
        for node_type in node_types:
            count = graph.run(f'MATCH (n:{node_type}) RETURN count(n)').evaluate()
            print(f"{node_type}: {count}")
        print()

if __name__ == "__main__":
    enhancer = DataEnhancer()
    enhancer.run_enhancement()
