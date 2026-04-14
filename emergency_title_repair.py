from py2neo import Graph
import os
import re
from dotenv import load_dotenv

load_dotenv()
graph = Graph(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

def emergency_repair():
    print("【开始标题紧急清洗与修复】")
    
    # 1. 获取所有可能被污染的节点
    nodes = graph.run("MATCH (a:Artwork) RETURN id(a) as node_id, a.title as title, a.image_filename as filename").data()
    print(f"正在诊断 {len(nodes)} 个节点...")

    count = 0
    for node in nodes:
        node_id = node['node_id']
        current_title = node['title']
        filename = node['filename']
        
        if not filename: continue

        # --- 第一步：彻底清洗标题 ---
        # 使用正则：把所有的 " (局部 X)"（不管重复几次）全部删掉
        # 比如 "步辇图 (局部 2) (局部 2)" -> "步辇图"
        clean_base_title = re.sub(r'\s*\(局部\s*\d+\)', '', current_title).strip()

        # --- 第二步：从文件名重新提取正确的编号 ---
        suffix_match = re.search(r'_(\d+)\.(jpg|jpeg|png|bmp|JPG)$', filename)
        
        if suffix_match:
            suffix = suffix_match.group(1)
            # 重新构建完美的、唯一的标题
            final_title = f"{clean_base_title} (局部 {suffix})"
        else:
            # 如果文件名里没编号（如：捣练图.jpg），就保持清洗后的原样
            final_title = clean_base_title

        # --- 第三步：强制更新数据库 ---
        # 同时修正 title 和 original_title
        graph.run(
            """
            MATCH (a:Artwork) WHERE id(a) = $id 
            SET a.title = $new_t, 
                a.original_title = $base_t
            """,
            id=node_id, new_t=final_title, base_t=clean_base_title
        )
        count += 1

    print(f"\n✅ 标题清洗圆满完成！")
    print(f"   - 成功修正了 {count} 个节点的标题污染。")
    print(f"   - 现在的标题格式统一为: 步辇图 (局部 2)")

if __name__ == "__main__":
    emergency_repair()