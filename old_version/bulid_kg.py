from knowledge_graph import KnowledgeGraphManager
from dotenv import load_dotenv
import os

load_dotenv()

kg_manager = KnowledgeGraphManager(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    os.getenv("NEO4J_USER", "neo4j"),
    os.getenv("NEO4J_PASSWORD")
)

# 构建本体
ontology = kg_manager.build_ontology()
print(f"本体构建完成，包含 {len(ontology['entity_types'])} 个实体类型")

# 构建向量索引
kg_manager.build_vector_index()
print("向量索引构建完成")