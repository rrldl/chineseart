#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入JSON数据到Neo4j数据库
"""

import json
import os
from py2neo import Graph, Node, Relationship, NodeMatcher

class JSONDataImporter:
    def __init__(self, uri, user, password):
        self.graph = Graph(uri, auth=(user, password))
        self.matcher = NodeMatcher(self.graph)
    
    def close(self):
        # py2neo的Graph对象不需要显式关闭
        pass
    
    def get_value(self, value, default="不详"):
        """处理空值，将空值替换为默认值"""
        if value is None or value == "":
            return default
        # 处理空列表
        if isinstance(value, list) and len(value) == 0:
            return ["不详"]
        return value
    
    def import_artists(self, json_file, image_folder=None):
        """导入艺术家数据"""
        # 读取主要艺术家数据文件
        with open(json_file, 'r', encoding='utf-8') as f:
            artists_data = json.load(f)
        
        # 读取备用艺术家数据文件
        backup_data = {}
        backup_file = "detail_json/artists_data_cleaned.json"
        if os.path.exists(backup_file):
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_list = json.load(f)
                for item in backup_list:
                    artist_id = item.get('Id')
                    if artist_id:
                        backup_data[artist_id] = item
        
        # 收集所有图片文件，建立ID到图片路径的映射
        image_map = {}
        if image_folder and os.path.exists(image_folder):
            for file in os.listdir(image_folder):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    # 提取ID部分（去掉后缀和序号）
                    id_part = file.split('_')[0]
                    if id_part not in image_map:
                        image_map[id_part] = os.path.join(image_folder, file)
        
        for artist_id, artist_info in artists_data.items():
            # 调试信息
            print(f"处理艺术家: ID={artist_id}")
            
            # 如果艺术家信息为None，尝试从备用数据中获取
            if not artist_info:
                print(f"  艺术家信息为None，尝试从备用数据中获取")
                if artist_id in backup_data:
                    artist_info = backup_data[artist_id]
                    print(f"  从备用数据中获取到信息: 名称={artist_info.get('name', 'NOT FOUND')}")
                else:
                    print(f"  备用数据中也不存在该艺术家信息")
            else:
                print(f"  艺术家信息: {artist_info.keys()}")
                print(f"  名称: {artist_info.get('name', 'NOT FOUND')}")
            
            # 检查艺术家是否已存在
            existing = self.matcher.match("Artist", id=artist_id).first()
            
            # 构建图像路径
            image_path = None
            if image_folder and os.path.exists(image_folder):
                # 优先使用ID匹配
                if artist_id in image_map:
                    image_path = image_map[artist_id]
                    print(f"  通过ID匹配到图片: {artist_id} -> {image_path}")
                else:
                    # 尝试使用艺术家姓名作为文件名
                    artist_name = artist_info.get('name', '') if artist_info else ''
                    if artist_name:
                        image_file = f"{artist_name}.jpg"
                        image_path = os.path.join(image_folder, image_file)
                        if not os.path.exists(image_path):
                            # 尝试其他可能的文件名格式
                            for ext in ['.jpg', '.jpeg', '.png']:
                                test_file = f"{artist_name}{ext}"
                                test_path = os.path.join(image_folder, test_file)
                                if os.path.exists(test_path):
                                    image_path = test_path
                                    break
            
            if not existing:
                # 创建艺术家节点
                artist = Node("Artist", 
                    id=artist_id,
                    name=self.get_value(artist_info.get('name') if artist_info else ''),
                    age=self.get_value(artist_info.get('age') if artist_info else ''),
                    alias=self.get_value(artist_info.get('alias') if artist_info else ''),
                    lifeTime=self.get_value(artist_info.get('lifeTime') if artist_info else ''),
                    startAge=self.get_value(artist_info.get('startAge') if artist_info else ''),
                    endAge=self.get_value(artist_info.get('endAge') if artist_info else ''),
                    homeTown=self.get_value(artist_info.get('homeTown') if artist_info else ''),
                    desc=self.get_value(artist_info.get('desc') if artist_info else ''),
                    category=self.get_value(artist_info.get('category', []) if artist_info else []),
                    country=self.get_value(artist_info.get('country') if artist_info else ''),
                    imagePath=image_path if image_path else "不详"
                )
                self.graph.create(artist)
                print(f"导入艺术家: {self.get_value(artist_info.get('name') if artist_info else '')}")
            else:
                # 更新现有节点
                existing['name'] = self.get_value(artist_info.get('name') if artist_info else '')
                existing['age'] = self.get_value(artist_info.get('age') if artist_info else '')
                existing['alias'] = self.get_value(artist_info.get('alias') if artist_info else '')
                existing['lifeTime'] = self.get_value(artist_info.get('lifeTime') if artist_info else '')
                existing['startAge'] = self.get_value(artist_info.get('startAge') if artist_info else '')
                existing['endAge'] = self.get_value(artist_info.get('endAge') if artist_info else '')
                existing['homeTown'] = self.get_value(artist_info.get('homeTown') if artist_info else '')
                existing['desc'] = self.get_value(artist_info.get('desc') if artist_info else '')
                existing['category'] = self.get_value(artist_info.get('category', []) if artist_info else [])
                existing['country'] = self.get_value(artist_info.get('country') if artist_info else '')
                if image_path:
                    existing['imagePath'] = image_path
                else:
                    existing['imagePath'] = "不详"
                self.graph.push(existing)
                print(f"更新艺术家: {self.get_value(artist_info.get('name') if artist_info else '')}")
    
    def import_artworks(self, json_file, image_folder=None):
        """导入艺术品数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            artworks_data = json.load(f)
        
        # 获取所有图片文件列表
        image_files = []
        if image_folder and os.path.exists(image_folder):
            print(f"正在扫描图片文件夹: {image_folder}")
            image_files = [f for f in os.listdir(image_folder) if f.lower().endswith('.bmp')]
            print(f"收集到 {len(image_files)} 个图片文件")
        
        # 统计有图片的艺术品数量
        artwork_with_image = 0
        total_artworks = len(artworks_data)
        
        print(f"\n开始导入 {total_artworks} 个艺术品...")
        
        # 为每个艺术品分配一个图片文件（按顺序）
        for i, (artwork_id, artwork_info) in enumerate(artworks_data.items()):
            # 检查艺术品是否已存在
            existing = self.matcher.match("Artwork", id=artwork_id).first()
            
            # 构建图像路径
            image_path = None
            if image_folder and os.path.exists(image_folder) and len(image_files) > 0:
                # 按顺序分配图片文件
                image_index = i % len(image_files)
                image_path = os.path.join(image_folder, image_files[image_index])
                print(f"  分配图片: {image_path}")
            
            if not existing:
                # 创建艺术品节点
                artwork = Node("Artwork", 
                    id=artwork_id,
                    name=artwork_info.get('suha', {}).get('name', ''),
                    age=artwork_info.get('suha', {}).get('age', ''),
                    author=artwork_info.get('suha', {}).get('author', ''),
                    desc=artwork_info.get('suha', {}).get('desc', ''),
                    mediaType=artwork_info.get('suha', {}).get('mediaType', ''),
                    materialType=artwork_info.get('suha', {}).get('materialType', ''),
                    styleType=artwork_info.get('suha', {}).get('styleType', ''),
                    size=artwork_info.get('suha', {}).get('size', ''),
                    owner=artwork_info.get('suha', {}).get('owner', ''),
                    tags=artwork_info.get('suha', {}).get('tags', []),
                    subjects=artwork_info.get('suha', {}).get('subjects', []),
                    technique=artwork_info.get('suha', {}).get('technique', []),
                    imagePath=image_path if image_path else "不详"
                )
                self.graph.create(artwork)
                artwork_with_image += 1
                
                # 建立与艺术家的关联
                author_name = artwork_info.get('suha', {}).get('author', '')
                if author_name:
                    artist = self.matcher.match("Artist", name=author_name).first()
                    if artist:
                        relationship = Relationship(artist, "CREATED", artwork)
                        self.graph.create(relationship)
                
                print(f"导入艺术品: {artwork_info.get('suha', {}).get('name', '')}")
            else:
                # 更新现有艺术品的图片路径
                existing['imagePath'] = image_path if image_path else "不详"
                self.graph.push(existing)
                artwork_with_image += 1
                print(f"更新艺术品图片: {artwork_info.get('suha', {}).get('name', '')} -> {image_path}")
        
        print(f"\n导入完成：共导入 {total_artworks} 个艺术品，其中 {artwork_with_image} 个有对应图片")
    
    def import_seals(self, json_file, image_folder=None):
        """导入印章数据：只保留核心 5 个字段，确保属性完全对齐"""
        with open(json_file, 'r', encoding='utf-8') as f:
            seals_data = json.load(f)
        
        print(f"正在同步 {len(seals_data)} 个印章节点...")
        
        for seal_info in seals_data:
            seal_id = str(seal_info.get('Id', ''))
            
            # 1. 确定图片路径
            image_path = "不详"
            if image_folder:
                # 你的图片主要是 .png
                test_path = os.path.join(image_folder, f"{seal_id}.png")
                if os.path.exists(test_path):
                    image_path = test_path

            # 2. 定义统一的 5 个核心属性
            # 如果 JSON 里没有对应字段，则填充“未知”或“不详”
            props = {
                "id": seal_id,
                "text": seal_info.get('简体', '未知'),
                "author": seal_info.get('作者', '未知'),
                "sealType": seal_info.get('印文', '未知'),
                "imagePath": image_path
            }

            # 3. 匹配并操作
            existing = self.matcher.match("Seal", id=seal_id).first()
            
            if not existing:
                # 创建新节点
                new_node = Node("Seal", **props)
                self.graph.create(new_node)
            else:
                # 更新现有节点：先清除所有旧属性，再赋予新的 5 个核心属性
                # 这样可以确保旧节点里多余的字段（比如“朱色比例”）被清空
                existing.clear() 
                for key, value in props.items():
                    existing[key] = value
                self.graph.push(existing)

        print("印章同步完成。")
    def import_inscriptions(self, json_file, image_folder=None):
        """导入题跋数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            inscriptions_data = json.load(f)
        
        for inscription_id, inscription_info in inscriptions_data.items():
            # 检查题跋是否已存在
            existing = self.matcher.match("Inscription", id=inscription_id).first()
            
            if not existing:
                # 构建图像路径
                image_path = None
                if image_folder and os.path.exists(image_folder):
                    image_file = f"{inscription_id}.jpg"  # 假设图片文件名为ID.jpg
                    image_path = os.path.join(image_folder, image_file)
                    if not os.path.exists(image_path):
                        # 尝试其他可能的文件名格式
                        image_file = f"{inscription_id}.png"
                        image_path = os.path.join(image_folder, image_file)
                        if not os.path.exists(image_path):
                            image_path = None
                
                # 创建题跋节点
                inscription = Node("Inscription", 
                    id=inscription_id,
                    name=inscription_info.get('suha', {}).get('name', ''),
                    age=inscription_info.get('suha', {}).get('age', ''),
                    author=inscription_info.get('suha', {}).get('author', ''),
                    desc=inscription_info.get('suha', {}).get('desc', ''),
                    tags=inscription_info.get('suha', {}).get('tags', []),
                    imagePath=image_path
                )
                self.graph.create(inscription)
                
                # 建立与艺术品的关联（假设题跋ID与艺术品ID相同）
                artwork = self.matcher.match("Artwork", id=inscription_id).first()
                if artwork:
                    relationship = Relationship(artwork, "HAS_INSCRIPTION", inscription)
                    self.graph.create(relationship)
                
                print(f"导入题跋: {inscription_info.get('suha', {}).get('name', '')}")
    
    def create_seal_artwork_relationships(self):
        """建立印章与艺术品的关联"""
        # 这里可以根据实际情况建立关联
        # 例如，如果有艺术品的印章信息，可以从艺术品的stampInfo字段中提取
        pass

def main():
    # 配置Neo4j连接
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345678"  # 使用正确的密码
    
    # JSON文件路径 - 使用最完整的艺术家数据文件
    artist_json = "detail_json/artist_details_cleaned.json"  # 最完整的艺术家数据
    artwork_json = "detail_json/works_details_artworks_cleaned.json"
    seal_json = "detail_json/signaturesInfo_cleaned.json"
    inscription_json = "detail_json/works_details_inscriptions_cleaned.json"
    
    # 图片文件夹路径
    artists_images = "artists_pictures"
    artworks_images = "artworks"
    signatures_images = "signature_pictures"
    inscriptions_images = "inscriptions"
    
    importer = JSONDataImporter(uri, user, password)
    
    try:
        # print("开始导入艺术家数据...")
        # importer.import_artists(artist_json, artists_images)
        
        # print("开始导入艺术品数据...")
        # importer.import_artworks(artwork_json, artworks_images)
        
        print("开始导入印章数据...")
        importer.import_seals(seal_json, signatures_images)
        
        # print("开始导入题跋数据...")
        # importer.import_inscriptions(inscription_json, inscriptions_images)
        
        print("数据导入完成！")
    finally:
        importer.close()

if __name__ == "__main__":
    main()
