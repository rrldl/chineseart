#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据采集与预处理模块 - 多源异构数据的采集、清洗和标准化处理
"""
import os
import json
import requests
import re
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class DataCollectionService:
    """数据采集与预处理服务类"""

    def __init__(self):
        """初始化数据采集服务"""
        # 确保必要的目录存在
        os.makedirs("./data/encyclopedia", exist_ok=True)
        os.makedirs("./data/artists", exist_ok=True)
        os.makedirs("./data/artworks", exist_ok=True)
        os.makedirs("./data/events", exist_ok=True)
        os.makedirs("./data/styles", exist_ok=True)

    def crawl_encyclopedia_data(self, query, entity_type):
        """
        爬取百科网站数据
        
        Args:
            query: 搜索关键词
            entity_type: 实体类型 (Artist, Artwork, HistoricalEvent, Style)
            
        Returns:
            dict: 爬取的数据
        """
        print(f"正在爬取关于 {query} 的百科数据...")
        
        # 百度百科爬取
        baidu_data = self._crawl_baidu_baike(query)
        
        # 维基百科爬取
        wiki_data = self._crawl_wikipedia(query)
        
        # 合并数据
        merged_data = {
            "query": query,
            "entity_type": entity_type,
            "baidu_baike": baidu_data,
            "wikipedia": wiki_data,
            "timestamp": os.path.getmtime(__file__)
        }
        
        # 保存数据
        save_path = f"./data/encyclopedia/{query}_{entity_type}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print(f"数据已保存到: {save_path}")
        return merged_data

    def _crawl_baidu_baike(self, query):
        """爬取百度百科数据"""
        url = f"https://baike.baidu.com/item/{requests.utils.quote(query)}"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取基本信息
            basic_info = {}
            
            # 提取摘要
            summary = soup.select_one(".lemma-summary")
            if summary:
                basic_info["summary"] = "".join([p.text.strip() for p in summary.find_all("p")])
            
            # 提取信息框
            info_box = soup.select_one(".basic-info")
            if info_box:
                for item in info_box.select(".item"):
                    label = item.select_one(".label")
                    value = item.select_one(".value")
                    if label and value:
                        key = label.text.strip().replace("\n", "").replace(":", "")
                        val = value.text.strip().replace("\n", "; ")
                        basic_info[key] = val
            
            # 提取目录
            catalog = soup.select_one(".lemma-catalog")
            if catalog:
                basic_info["catalog"] = [li.text.strip() for li in catalog.find_all("li")]
            
            return basic_info
        except Exception as e:
            print(f"百度百科爬取失败: {e}")
            return {}

    def _crawl_wikipedia(self, query):
        """爬取维基百科数据"""
        url = f"https://zh.wikipedia.org/wiki/{requests.utils.quote(query)}"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取基本信息
            basic_info = {}
            
            # 提取摘要
            summary = soup.select_one(".mw-parser-output > p:not(.mw-empty-elt)")
            if summary:
                basic_info["summary"] = summary.text.strip()
            
            # 提取信息框
            info_box = soup.select_one(".infobox")
            if info_box:
                basic_info["infobox"] = info_box.text.strip()
            
            # 提取目录
            catalog = soup.select_one("#toc")
            if catalog:
                basic_info["catalog"] = [li.text.strip() for li in catalog.find_all("li")]
            
            return basic_info
        except Exception as e:
            print(f"维基百科爬取失败: {e}")
            return {}

    def process_text_data(self, text, chunk_size=500, chunk_overlap=50):
        """
        处理文本数据，使用LangChain进行智能分块
        
        Args:
            text: 原始文本
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            
        Returns:
            list: 分块后的文档列表
        """
        # 创建文本分割器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # 清洗文本
        cleaned_text = self._clean_text(text)
        
        # 分块
        documents = text_splitter.create_documents([cleaned_text])
        
        return documents

    def _clean_text(self, text):
        """清洗文本数据"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)
        
        return text.strip()

    def build_artist_knowledge_base(self, artists):
        """
        构建历代书画家知识库
        
        Args:
            artists: 书画家列表
            
        Returns:
            dict: 知识库数据
        """
        knowledge_base = {}
        
        for artist in artists:
            # 爬取数据
            data = self.crawl_encyclopedia_data(artist, "Artist")
            
            # 提取关键信息
            artist_info = {
                "name": artist,
                "basic_info": {},
                "artworks": [],
                "style": [],
                "teacher": [],
                "students": [],
                "era": ""
            }
            
            # 从百度百科提取信息
            if data.get("baidu_baike"):
                baidu_data = data["baidu_baike"]
                artist_info["basic_info"].update(baidu_data)
                
                # 提取生卒年
                for key, value in baidu_data.items():
                    if "生卒" in key or "年" in key:
                        artist_info["years"] = value
                    elif "朝代" in key or "时期" in key:
                        artist_info["era"] = value
                    elif "风格" in key:
                        artist_info["style"].append(value)
                    elif "师承" in key or "老师" in key:
                        artist_info["teacher"].append(value)
            
            knowledge_base[artist] = artist_info
            
            # 保存数据
            save_path = f"./data/artists/{artist}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(artist_info, f, ensure_ascii=False, indent=2)
        
        return knowledge_base

    def build_event_knowledge_base(self, events):
        """
        构建历史事件知识库
        
        Args:
            events: 历史事件列表
            
        Returns:
            dict: 知识库数据
        """
        knowledge_base = {}
        
        for event in events:
            # 爬取数据
            data = self.crawl_encyclopedia_data(event, "HistoricalEvent")
            
            # 提取关键信息
            event_info = {
                "name": event,
                "basic_info": {},
                "time": "",
                "description": "",
                "influence": []
            }
            
            # 从百度百科提取信息
            if data.get("baidu_baike"):
                baidu_data = data["baidu_baike"]
                event_info["basic_info"].update(baidu_data)
                
                # 提取时间
                for key, value in baidu_data.items():
                    if "时间" in key or "年" in key:
                        event_info["time"] = value
                    elif "影响" in key:
                        event_info["influence"].append(value)
            
            knowledge_base[event] = event_info
            
            # 保存数据
            save_path = f"./data/events/{event}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(event_info, f, ensure_ascii=False, indent=2)
        
        return knowledge_base

    def build_style_knowledge_base(self, styles):
        """
        构建艺术流派知识库
        
        Args:
            styles: 艺术流派列表
            
        Returns:
            dict: 知识库数据
        """
        knowledge_base = {}
        
        for style in styles:
            # 爬取数据
            data = self.crawl_encyclopedia_data(style, "Style")
            
            # 提取关键信息
            style_info = {
                "name": style,
                "basic_info": {},
                "origin": "",
                "characteristics": [],
                "representative_artists": [],
                "representative_artworks": []
            }
            
            # 从百度百科提取信息
            if data.get("baidu_baike"):
                baidu_data = data["baidu_baike"]
                style_info["basic_info"].update(baidu_data)
                
                # 提取特征
                for key, value in baidu_data.items():
                    if "特点" in key or "特征" in key:
                        style_info["characteristics"].append(value)
                    elif "代表" in key:
                        if "画家" in key or "艺术家" in key:
                            style_info["representative_artists"].append(value)
                        elif "作品" in key:
                            style_info["representative_artworks"].append(value)
            
            knowledge_base[style] = style_info
            
            # 保存数据
            save_path = f"./data/styles/{style}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(style_info, f, ensure_ascii=False, indent=2)
        
        return knowledge_base

# 测试代码
if __name__ == "__main__":
    service = DataCollectionService()
    
    # 测试爬取百科数据
    print("测试爬取百科数据...")
    data = service.crawl_encyclopedia_data("张择端", "Artist")
    print(f"爬取结果: {data.keys()}")
    
    # 测试文本处理
    print("\n测试文本处理...")
    test_text = "张择端（1085年—1145年），字正道，又字文友，东武（今山东诸城）人，北宋末年画家。他的代表作品是《清明上河图》，描绘了北宋都城汴京的繁华景象。"
    documents = service.process_text_data(test_text)
    print(f"分块结果: {len(documents)} 块")
    for i, doc in enumerate(documents):
        print(f"块 {i+1}: {doc.page_content[:100]}...")
    
    # 测试构建知识库
    print("\n测试构建书画家知识库...")
    artists = ["张择端", "王希孟", "唐寅"]
    artist_kb = service.build_artist_knowledge_base(artists)
    print(f"书画家知识库大小: {len(artist_kb)}")
    
    print("\n测试构建历史事件知识库...")
    events = ["元祐党争"]
    event_kb = service.build_event_knowledge_base(events)
    print(f"历史事件知识库大小: {len(event_kb)}")
    
    print("\n测试构建艺术流派知识库...")
    styles = ["吴门画派"]
    style_kb = service.build_style_knowledge_base(styles)
    print(f"艺术流派知识库大小: {len(style_kb)}")
