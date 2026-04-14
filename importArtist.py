import os
import json
import logging
from py2neo import Graph, Node, Relationship, NodeMatcher
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class ArtistPortraitImporter:
    def __init__(self):
        # 1. 获取配置信息
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")
        self.image_dir = os.getenv("IMAGE_DIR", "./artists_pictures")
        
        # 定义需要加载的多个 JSON 文件路径
        self.json_files = [
            "detail_json/artist_details_cleaned.json", 
            "detail_json/artists_data_cleaned.json"
        ]
        
        # 2. 初始化数据库连接
        try:
            self.graph = Graph(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            self.matcher = NodeMatcher(self.graph)
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            exit(1)

        # 3. 加载并合并多源元数据
        self.artist_metadata = self.load_merged_metadata()
        logger.info(f"✅ 数据加载完成，内存中共有 {len(self.artist_metadata)} 位艺人信息")

    def load_merged_metadata(self):
        """兼容字典和列表两种格式的 JSON 加载"""
        merged_data = {}
        for file_path in self.json_files:
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                    # 关键逻辑：判断是字典还是列表
                    items_to_process = {}
                    if isinstance(raw_data, dict):
                        items_to_process = raw_data
                    elif isinstance(raw_data, list):
                        # 如果是列表，将其转换为以 Id 为 Key 的字典
                        for item in raw_data:
                            if isinstance(item, dict):
                                # 兼容 Id 或 id 两种写法
                                aid = item.get('Id') or item.get('id')
                                if aid:
                                    items_to_process[aid] = item
                    
                    # 合并到最终结果
                    for aid, info in items_to_process.items():
                        if info and isinstance(info, dict):
                            if aid not in merged_data:
                                merged_data[aid] = info
                            else:
                                # 补全缺失字段
                                for key, value in info.items():
                                    if value and not merged_data[aid].get(key):
                                        merged_data[aid][key] = value
                logger.info(f"📖 已成功处理文件: {file_path}")
            except Exception as e:
                logger.error(f"❌ 处理文件 {file_path} 失败: {e}")
        return merged_data


    def num_to_cn(self, num_str):
        mapping = {'1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九','10':'十'}
        return mapping.get(num_str, num_str)

    def validate_filename(self, filename):
        if '_' in filename:
            artist_id, suffix_part = filename.rsplit('_', 1)
            suffix_num = suffix_part.split('.')[0]
        else:
            artist_id = os.path.splitext(filename)[0]
            suffix_num = "1"
        return artist_id, suffix_num

    def run(self):
        # 1. 建立约束
        try:
            self.graph.run("CREATE CONSTRAINT artist_id_idx IF NOT EXISTS FOR (a:Artist) REQUIRE a.id IS UNIQUE")
            self.graph.run("CREATE CONSTRAINT portrait_path_idx IF NOT EXISTS FOR (p:ArtistPortrait) REQUIRE p.path IS UNIQUE")
            logger.info("✅ 节点约束检查完成")
        except Exception as e:
            logger.warning(f"⚠️ 约束提示: {e}")

        # 2. 扫描图片
        if not os.path.exists(self.image_dir):
            logger.error(f"❌ 图片目录不存在: {self.image_dir}")
            return

        files = [f for f in os.listdir(self.image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        logger.info(f"🚀 准备处理 {len(files)} 张图片...")

        # 统计变量
        p_count, skip_count, exist_count, err_count = 0, 0, 0, 0

        # 3. 循环导入
        for filename in files:
            try:
                artist_id, suffix_num = self.validate_filename(filename)
                
                # 获取数据并严谨校验
                data = self.artist_metadata.get(artist_id)
                if not data or not isinstance(data, dict):
                    skip_count += 1
                    continue

                # 提取核心属性，确保不为空
                name = data.get("name") or "未知"
                dynasty = data.get("age") or "不详"
                full_desc = data.get("desc") or "暂无详细生平介绍。"
                category_list = data.get("category")
                if not isinstance(category_list, list):
                    category_list = [category_list] if category_list else []

                # --- A. Artist 节点 (户口本) ---
                artist_node = self.matcher.match("Artist", id=artist_id).first()
                if not artist_node:
                    artist_node = Node("Artist", 
                        id=artist_id, 
                        name=name,
                        age=dynasty,
                        alias=data.get("alias") or "不详",
                        lifeTime=data.get("lifeTime") or "不详",
                        homeTown=data.get("homeTown") or "不详",
                        desc=full_desc,
                        category=category_list,
                        country=data.get("country") or "中国"
                    )
                    self.graph.create(artist_node)

                # --- B. ArtistPortrait 节点 (门面) ---
                portrait_node = self.matcher.match("ArtistPortrait", path=filename).first()
                if not portrait_node:
                    short_desc = (full_desc[:50] + '...') if len(full_desc) > 50 else full_desc
                    display_name = f"{name} - 画像{self.num_to_cn(suffix_num)}"

                    portrait_node = Node("ArtistPortrait", 
                        name=display_name,
                        dynasty=dynasty,
                        category=category_list,
                        short_desc=short_desc,
                        path=filename,
                        
                        # 后台及向量化所需冗余
                        artist_id=artist_id,
                        artist_name=name,
                        description=full_desc,
                        
                        node_type="ArtistPortrait",
                        image_url=f"/artist_image/{filename}"
                    )
                    self.graph.create(portrait_node)

                    # 建立关系
                    self.graph.create(Relationship(artist_node, "HAS_PORTRAIT", portrait_node))
                    
                    p_count += 1
                    if p_count % 100 == 0:
                        logger.info(f"   - 已同步 {p_count} 个节点...")
                else:
                    exist_count += 1

            except Exception as e:
                err_count += 1
                logger.error(f"❌ 处理 {filename} 异常: {e}")

        # 4. 最终汇总
        logger.info(f"\n📊 任务圆满完成统计:")
        logger.info(f"   - 新增画像节点: {p_count}")
        logger.info(f"   - 跳过已存在: {exist_count}")
        logger.info(f"   - 匹配失败(跳过): {skip_count}")
        logger.info(f"   - 运行错误: {err_count}")

if __name__ == "__main__":
    importer = ArtistPortraitImporter()
    importer.run() 