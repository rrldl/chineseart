#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量图像数据收集脚本
从网络上搜索并下载与书画家、艺术品相关的图像
"""
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random
import threading
from queue import Queue

class ImageCollector:
    """图像收集器"""
    
    def __init__(self):
        """初始化"""
        # 创建必要的目录
        self.base_dir = "artwork_images"
        self.artworks_dir = os.path.join(self.base_dir, "artworks")
        self.artists_dir = os.path.join(self.base_dir, "artists")
        self.inscriptions_dir = os.path.join(self.base_dir, "inscriptions")
        self.seals_dir = os.path.join(self.base_dir, "seals")
        
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.artworks_dir, exist_ok=True)
        os.makedirs(self.artists_dir, exist_ok=True)
        os.makedirs(self.inscriptions_dir, exist_ok=True)
        os.makedirs(self.seals_dir, exist_ok=True)
        
        # 搜索关键词列表
        self.search_terms = {
            "artworks": [
                "清明上河图", "千里江山图", "富春山居图", "汉宫春晓图", "百骏图",
                "洛神赋图", "步辇图", "唐宫仕女图", "五牛图", "韩熙载夜宴图",
                "千里江山图", "富春山居图", "汉宫春晓图", "百骏图", "搜山图",
                "长江万里图", "黄河万里图", "华山图", "泰山图", "黄山图",
                "庐山图", "峨眉山图", "衡山图", "恒山图", "嵩山图",
                "潇湘奇观图", "溪山行旅图", "早春图", "万壑松风图", "渔庄秋霁图",
                "青卞隐居图", "容膝斋图", "夏日山居图", "秋山问道图", "寒江独钓图",
                "雪景寒林图", "赤壁图", "清明上河图局部", "千里江山图局部", "富春山居图局部"
            ],
            "artists": [
                "张择端", "王希孟", "黄公望", "仇英", "唐寅", "文徵明", "沈周", "八大山人", "石涛", "郑板桥",
                "顾恺之", "吴道子", "阎立本", "韩滉", "李思训", "李昭道", "王维", "张萱", "周昉", "韩干",
                "董源", "巨然", "范宽", "郭熙", "李公麟", "米芾", "米友仁", "赵孟頫", "倪瓒", "王蒙",
                "吴镇", "戴进", "吴伟", "董其昌", "陈洪绶", "崔子忠", "龚贤", "髡残", "王原祁", "王时敏"
            ],
            "inscriptions": [
                "清明上河图题跋", "千里江山图题跋", "富春山居图题跋", "兰亭序题跋", "祭侄文稿题跋",
                "寒食帖题跋", "伯远帖题跋", "中秋帖题跋", "快雪时晴帖题跋", "鸭头丸帖题跋"
            ],
            "seals": [
                "乾隆御览之宝", "石渠宝笈", "三希堂精鉴玺", "宜子孙", "养心殿鉴藏宝",
                "嘉庆御览之宝", "宣统御览之宝", "御书房鉴藏宝", "内府图书", "天禄琳琅"
            ]
        }
        
        # 线程池大小
        self.threads = 5
        self.queue = Queue()
        self.lock = threading.Lock()
        self.download_count = 0
        self.failure_count = 0
    
    def search_bing_images(self, query, num_images=10):
        """从必应搜索图像"""
        try:
            # 构建搜索URL
            search_url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&count={num_images}"
            
            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # 发送请求
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取图像URL
            image_urls = []
            for img in soup.find_all('img', class_='mimg'):
                if 'src' in img.attrs:
                    image_urls.append(img['src'])
                elif 'data-src' in img.attrs:
                    image_urls.append(img['data-src'])
            
            return image_urls[:num_images]
            
        except Exception as e:
            print(f"搜索失败: {query} - {str(e)}")
            return []
    
    def download_image(self, url, save_path):
        """下载图像"""
        try:
            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # 发送请求
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # 检查文件类型
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                print(f"不是图像文件: {url}")
                return False
            
            # 保存图像
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 验证文件大小
            if os.path.getsize(save_path) < 1024:  # 小于1KB的文件可能是错误的
                os.remove(save_path)
                return False
            
            with self.lock:
                self.download_count += 1
                print(f"✓ 下载成功: {os.path.basename(save_path)} ({self.download_count})")
            
            return True
            
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                print(f"✗ 下载失败: {url} - {str(e)}")
            return False
    
    def worker(self):
        """工作线程"""
        while not self.queue.empty():
            item = self.queue.get()
            try:
                query, category, save_dir = item
                
                print(f"\n搜索: {query} ({category})")
                
                # 搜索图像
                image_urls = self.search_bing_images(query, num_images=10)
                
                if not image_urls:
                    print(f"未找到图像: {query}")
                    continue
                
                # 下载图像
                for i, url in enumerate(image_urls):
                    # 生成文件名
                    filename = f"{query}_{i+1}.jpg"
                    save_path = os.path.join(save_dir, filename)
                    
                    # 下载图像
                    self.download_image(url, save_path)
                    
                    # 随机延迟，避免被反爬
                    time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"工作线程异常: {str(e)}")
            finally:
                self.queue.task_done()
    
    def collect_images(self):
        """开始收集图像"""
        print("=== 开始批量收集图像数据 ===")
        print(f"目标: 收集 {len(self.search_terms['artworks']) + len(self.search_terms['artists']) + len(self.search_terms['inscriptions']) + len(self.search_terms['seals'])} 个关键词的图像")
        print(f"线程数: {self.threads}")
        print(f"保存目录: {self.base_dir}")
        print()
        
        # 填充队列
        for category, terms in self.search_terms.items():
            if category == "artworks":
                save_dir = self.artworks_dir
            elif category == "artists":
                save_dir = self.artists_dir
            elif category == "inscriptions":
                save_dir = self.inscriptions_dir
            elif category == "seals":
                save_dir = self.seals_dir
            else:
                continue
            
            for term in terms:
                self.queue.put((term, category, save_dir))
        
        # 启动线程
        threads = []
        for i in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待所有任务完成
        self.queue.join()
        
        # 统计结果
        print("\n=== 图像收集完成 ===")
        print(f"成功下载: {self.download_count} 张图像")
        print(f"失败: {self.failure_count} 张图像")
        print(f"总尝试: {self.download_count + self.failure_count} 次")
        print(f"保存位置: {self.base_dir}")

if __name__ == "__main__":
    collector = ImageCollector()
    collector.collect_images()