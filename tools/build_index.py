import os
import time
import dashscope
import numpy as np
import faiss
import json
import random
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from PIL import Image

# ================= 配置区 =================
dashscope.api_key = "sk-18e0af55804c4829ae1bea3fb95c4aa9" 
IMAGE_ROOT_DIR = r"D:\shuhua_picture\work"

# 结果保存路径
INDEX_PATH = os.path.join(IMAGE_ROOT_DIR, "art_index_1024.index")
PATHS_PATH = os.path.join(IMAGE_ROOT_DIR, "art_paths.npy")
BASE_IDS_PATH = os.path.join(IMAGE_ROOT_DIR, "art_base_ids.json")
PROGRESS_CACHE = os.path.join(IMAGE_ROOT_DIR, "embedding_cache.json") # 断点续传记录

IMAGE_EXTENSIONS = {'.bmp', '.jpg', '.jpeg', '.png', '.webp'}

# 🚀 阿里云多模态模型 QPS 很低，建议设为 1-2
MAX_WORKERS = 2 
# 每次请求后的强制冷却时间 (秒)
REQUEST_DELAY = 1.0 
# ==========================================

# 🌟 全局锁与全局内存缓存（解决高并发下硬盘读写崩溃问题）
cache_lock = threading.Lock()
global_cache = {}

def load_cache():
    global global_cache
    if os.path.exists(PROGRESS_CACHE):
        try:
            with open(PROGRESS_CACHE, 'r', encoding='utf-8') as f:
                global_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ 缓存读取失败，将重建: {e}")
            global_cache = {}
    return global_cache

def save_to_cache(rel_path, vector, base_id):
    """只更新内存并直接覆写，不再重新 read 整个文件"""
    with cache_lock:
        global_cache[rel_path] = {"vector": vector.tolist(), "base_id": base_id}
        # 使用临时文件写入后替换，防止写入中途断电导致文件损坏
        temp_cache = PROGRESS_CACHE + ".tmp"
        with open(temp_cache, 'w', encoding='utf-8') as f:
            json.dump(global_cache, f)
        os.replace(temp_cache, PROGRESS_CACHE)

def compress_image_for_api(image_path, max_size=1024):
    try:
        img = Image.open(image_path).convert('RGB')
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        thread_id = threading.get_ident()
        temp_path = f"temp_{thread_id}.jpg"
        img.save(temp_path, format="JPEG", quality=80)
        return temp_path
    except Exception as e:
        print(f"压缩失败 {image_path}: {e}")
        return None

def get_image_embedding_with_retry(image_path, max_retries=10):
    temp_img = None
    for attempt in range(max_retries):
        try:
            temp_img = compress_image_for_api(image_path)
            if not temp_img: return None

            # 保持你原来的、能跑通的路径处理方式
            response = dashscope.MultiModalEmbedding.call(
                model="multimodal-embedding-v1",
                input=[{"image": f"file://{os.path.abspath(temp_img)}"}]
            )
            
            # 强制休眠，防止请求过快
            time.sleep(REQUEST_DELAY + random.uniform(0, 0.5))

            if response.status_code == 200:
                embedding = response.output['embeddings'][0]['embedding']
                return np.array(embedding, dtype=np.float32)
            
            elif response.status_code == 429:
                wait_time = (2 ** attempt) + random.random() * 2
                print(f"\n⚠️ 触发限流(429)，等待 {wait_time:.1f}s 后重试...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ API 错误 [{image_path}]: {response.message}")
                return None
                    
        except Exception as e:
            time.sleep(2)
        finally:
            if temp_img and os.path.exists(temp_img):
                try: os.remove(temp_img)
                except: pass
    return None

def process_single_image(img_path):
    rel_path = str(img_path.relative_to(IMAGE_ROOT_DIR)).replace("\\", "/")
    
    if rel_path in global_cache:
        item = global_cache[rel_path]
        return (np.array(item["vector"], dtype=np.float32), rel_path, item["base_id"])

    vector = get_image_embedding_with_retry(str(img_path))
    if vector is not None:
        base_id = img_path.stem.split('_')[0].strip().lower()
        save_to_cache(rel_path, vector, base_id)
        return (vector, rel_path, base_id)
    return None

def build_faiss_database():
    print("🚀 启动特征提取 (支持断点续传增量模式)...")
    
    # --- 🌟 终极去重扫描逻辑 ---
    unique_images_dict = {} # 使用字典，以绝对路径字符串为 Key 强制去重
    
    for f in Path(IMAGE_ROOT_DIR).rglob("*"):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            # 过滤掉以 . 开头的隐藏垃圾文件
            if f.name.startswith('.'):
                continue
                
            # 提取绝对路径并统一将反斜杠转为正斜杠，确保 Windows 下判定一致
            abs_path_str = str(f.resolve()).replace('\\', '/')
            unique_images_dict[abs_path_str] = f

    all_images = list(unique_images_dict.values())
    # --- 修改结束 ---
    
    print(f"📸 目录中共发现 {len(all_images)} 张真实有效的图片。")
    
    # 2. 加载进度到全局内存
    load_cache()
    print(f"🔄 已从缓存加载 {len(global_cache)} 条历史记录。")
    
    vectors_list = []
    paths_list = []
    base_ids_list = []
    
    # 3. 多线程处理
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 移除了传参 processed_cache，直接使用全局缓存
        future_to_img = {executor.submit(process_single_image, path): path for path in all_images}
        
        for future in tqdm(as_completed(future_to_img), total=len(all_images), desc="提特征进度"):
            result = future.result()
            if result is not None:
                vector, rel_path, base_id = result
                vectors_list.append(vector)
                paths_list.append(rel_path)
                base_ids_list.append(base_id)

    if not vectors_list:
        print("⚠️ 未能提取到任何向量。")
        return

    # 4. 构建索引
    print(f"\n🔨 正在构建 FAISS 索引 (总计: {len(vectors_list)} 条)...")
    dimension = 1024
    vectors_matrix = np.vstack(vectors_list)
    faiss.normalize_L2(vectors_matrix)
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors_matrix)
    
    faiss.write_index(index, INDEX_PATH)
    np.save(PATHS_PATH, np.array(paths_list))
    with open(BASE_IDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(base_ids_list, f, indent=4)
        
    print(f"🎉 任务完成！索引已保存至: {INDEX_PATH}")

if __name__ == "__main__":
    build_faiss_database()