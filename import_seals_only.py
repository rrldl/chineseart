import json
import os
from py2neo import Graph, Node, NodeMatcher

# ================= 配置区域 =================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # <--- 请填写你的数据库密码

# 文件路径
JSON_FILE = r"detail_json\signaturesInfo_cleaned.json"
IMAGE_FOLDER = r"F:\Chineseart\signature_pictures"
# ===========================================

class SealOnlyImporter:
    def __init__(self):
        try:
            self.graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            self.matcher = NodeMatcher(self.graph)
            print("✅ 成功连接 Neo4j 数据库")
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            exit()

    def run_import(self):
        if not os.path.exists(JSON_FILE):
            print(f"❌ 找不到 JSON 文件: {JSON_FILE}")
            return

        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            seals_data = json.load(f)

        print(f"🚀 开始处理 {len(seals_data)} 个印章数据...")

        count_new = 0
        count_update = 0

        for seal_info in seals_data:
            seal_id = str(seal_info.get('Id', ''))
            if not seal_id:
                continue

            # --- 核心修复：定义图片路径逻辑 ---
            image_path = "不详"
            for ext in ['.png', '.jpg', '.jpeg']:
                test_path = os.path.join(IMAGE_FOLDER, f"{seal_id}{ext}")
                if os.path.exists(test_path):
                    # 获取绝对路径，方便同步脚本读取
                    image_path = os.path.abspath(test_path)
                    break

            # --- 提取属性 ---
            content = seal_info.get('简体', '未知')
            author = seal_info.get('作者', '未知')
            style = seal_info.get('印文', '未知')
            shape = seal_info.get('印形', '未知')

            # --- 自动合成描述 (替代 API，省钱且精准) ---
            auto_desc = f"这是一枚由{author}篆刻的{style}{shape}印章，印文内容为“{content}”。"

            # --- 准备统一化属性 ---
            props = {
                "source_id": seal_id,
                "name": f"{author}刻“{content}”印",
                "artist": author,
                "content": content,
                "style": style,
                "shape": shape,
                "description": auto_desc,
                "path": image_path  # 现在 image_path 已经被正确定义了
            }

            # --- 执行合并/更新 ---
            # 建议先清空旧 Seal 节点确保属性名变整齐： MATCH (s:Seal) DETACH DELETE s
            existing = self.matcher.match("Seal", source_id=seal_id).first()
            if not existing:
                new_node = Node("Seal", **props)
                self.graph.create(new_node)
                count_new += 1
            else:
                existing.clear() 
                for key, value in props.items():
                    existing[key] = value
                self.graph.push(existing)
                count_update += 1
            if (count_new + count_update) % 500 == 0:
                print(f"已处理 {(count_new + count_update)} 条...")

        print("-" * 30)
        print(f"🎊 同步完成！")
        print(f"新增印章: {count_new}")
        print(f"更新印章: {count_update}")
        print(f"总计: {count_new + count_update}")

if __name__ == "__main__":
    importer = SealOnlyImporter()
    importer.run_import()