#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
应用服务模块 - 实现智能问答系统、跨模态检索引擎和有效性验证
"""
import os
import json
import requests
from data_collection import DataCollectionService
from la_clip_alignment import LAClipAlignmentService
from knowledge_graph import KnowledgeGraphManager

class ApplicationService:
    """应用服务类"""

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        """
        初始化应用服务
        
        Args:
            neo4j_uri: Neo4j数据库连接地址
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        # 初始化各服务
        self.data_service = DataCollectionService()
        self.alignment_service = LAClipAlignmentService(neo4j_uri, neo4j_user, neo4j_password)
        self.kg_manager = KnowledgeGraphManager(neo4j_uri, neo4j_user, neo4j_password)
        
        # 确保必要的目录存在
        os.makedirs("./data/application", exist_ok=True)
        os.makedirs("./data/test_set", exist_ok=True)
        os.makedirs("./data/evaluation", exist_ok=True)

    def rag_qa_system(self, question, top_k=5):
        """
        基于RAG的智能问答系统
        
        Args:
            question: 用户问题
            top_k: 检索结果数量
            
        Returns:
            dict: 回答结果
        """
        print(f"处理问题: {question}")
        
        # 步骤1: 提取问题中的实体
        entities = self._extract_entities(question)
        print(f"提取到的实体: {entities}")
        
        # 步骤2: 从知识图谱中检索相关信息
        kg_info = self._retrieve_from_kg(question, entities, top_k)
        
        # 步骤3: 从对齐节点中检索相关信息
        alignment_info = self._retrieve_from_alignment(question, top_k)
        
        # 步骤4: 融合信息并生成回答
        answer = self._generate_answer(question, kg_info, alignment_info)
        
        return {
            "question": question,
            "answer": answer,
            "entities": entities,
            "kg_info": kg_info,
            "alignment_info": alignment_info
        }

    def _extract_entities(self, text):
        """
        提取文本中的实体
        
        Args:
            text: 文本内容
            
        Returns:
            list: 实体列表
        """
        # 简单的实体提取
        entities = []
        
        # 提取艺术品名称（带《》的）
        import re
        artwork_pattern = r'《([^》]+)》'
        artworks = re.findall(artwork_pattern, text)
        for artwork in artworks:
            entities.append({"name": artwork, "type": "Artwork"})
        
        # 提取艺术家名称
        artist_keywords = ['张择端', '王希孟', '唐寅', '文徵明', '徐渭', '八大山人',
                           '齐白石', '徐悲鸿', '吴昌硕', '黄公望', '王羲之', '颜真卿']
        for keyword in artist_keywords:
            if keyword in text:
                entities.append({"name": keyword, "type": "Artist"})
        
        # 提取朝代
        dynasty_keywords = ['唐代', '宋朝', '元代', '明代', '清代', '唐', '宋', '元', '明', '清']
        for keyword in dynasty_keywords:
            if keyword in text:
                entities.append({"name": keyword, "type": "Dynasty"})
        
        # 提取艺术风格
        style_keywords = ['山水画', '水墨画', '工笔画', '写意画', '青绿山水', '文人画']
        for keyword in style_keywords:
            if keyword in text:
                entities.append({"name": keyword, "type": "Style"})
        
        return entities

    def _retrieve_from_kg(self, question, entities, top_k=5):
        """
        从知识图谱中检索信息
        
        Args:
            question: 用户问题
            entities: 提取的实体
            top_k: 检索结果数量
            
        Returns:
            list: 检索结果
        """
        results = []
        
        # 构建Cypher查询
        for entity in entities:
            entity_name = entity["name"]
            entity_type = entity["type"]
            
            # 根据实体类型构建不同的查询
            if entity_type == "Artwork":
                query = f"""
                MATCH (a:Artwork {{title: '{entity_name}'}})
                OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
                OPTIONAL MATCH (a)-[:PART_OF]->(dynasty:Dynasty)
                OPTIONAL MATCH (a)-[:HAS_STYLE]->(style:Style)
                RETURN a, artist, dynasty, style
                LIMIT {top_k}
                """
            elif entity_type == "Artist":
                query = f"""
                MATCH (a:Artist {{name: '{entity_name}'}})
                OPTIONAL MATCH (artwork:Artwork)-[:CREATED_BY]->(a)
                OPTIONAL MATCH (a)-[:LIVED_IN]->(dynasty:Dynasty)
                RETURN a, artwork, dynasty
                LIMIT {top_k}
                """
            else:
                query = f"""
                MATCH (n:{entity_type} {{name: '{entity_name}'}})
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT {top_k}
                """
            
            try:
                for record in self.kg_manager.graph.run(query):
                    results.append(dict(record))
            except Exception as e:
                print(f"知识图谱查询失败: {e}")
        
        return results

    def _retrieve_from_alignment(self, question, top_k=5):
        """
        从对齐节点中检索信息
        
        Args:
            question: 用户问题
            top_k: 检索结果数量
            
        Returns:
            list: 检索结果
        """
        return self.alignment_service.search_aligned_entities(question, top_k)

    def _generate_answer(self, question, kg_info, alignment_info):
        """
        生成回答
        
        Args:
            question: 用户问题
            kg_info: 知识图谱信息
            alignment_info: 对齐节点信息
            
        Returns:
            str: 回答
        """
        # 构建提示词
        prompt = f"""
        你是一位中国古代书画专家，请基于以下信息回答问题。
        
        问题: {question}
        
        知识图谱信息:
        {json.dumps(kg_info, ensure_ascii=False, indent=2)}
        
        对齐节点信息:
        {json.dumps(alignment_info, ensure_ascii=False, indent=2)}
        
        请用专业、准确、结构化的中文回答，使用Markdown格式美化回答。
        """
        
        # 调用Ollama API
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                return "抱歉，我无法回答这个问题。"
        except Exception as e:
            print(f"生成回答失败: {e}")
            return "抱歉，我无法回答这个问题。"

    def cross_modal_search(self, query, search_type="text_to_image", top_k=5):
        """
        跨模态检索
        
        Args:
            query: 查询文本或图像路径
            search_type: 检索类型 (text_to_image, image_to_image, image_to_text)
            top_k: 返回结果数量
            
        Returns:
            list: 检索结果
        """
        print(f"执行跨模态检索: {search_type}, 查询: {query}")
        
        if search_type == "text_to_image":
            # 文本到图像检索
            return self.alignment_service.search_aligned_entities(query, top_k)
        elif search_type == "image_to_image":
            # 图像到图像检索
            return self.alignment_service.search_aligned_entities(query, top_k)
        elif search_type == "image_to_text":
            # 图像到文本检索
            results = self.alignment_service.search_aligned_entities(query, top_k)
            # 对每个结果获取文本描述
            for result in results:
                entity_id = result["entity_id"]
                entity_type = result["entity_type"]
                # 从知识图谱中获取文本描述
                description = self._get_entity_description(entity_id, entity_type)
                result["description"] = description
            return results
        else:
            return []

    def _get_entity_description(self, entity_id, entity_type):
        """
        获取实体的文本描述
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            
        Returns:
            str: 实体描述
        """
        try:
            if entity_type == "Artwork":
                query = f"MATCH (a:Artwork {{title: '{entity_id}'}}) RETURN a.description as description"
            else:
                query = f"MATCH (e:{entity_type} {{name: '{entity_id}'}}) RETURN e.description as description"
            
            result = self.kg_manager.graph.run(query).data()
            if result and result[0].get("description"):
                return result[0]["description"]
            else:
                return ""
        except Exception as e:
            print(f"获取实体描述失败: {e}")
            return ""

    def build_test_set(self, test_cases):
        """
        构建测试集
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            str: 测试集保存路径
        """
        print(f"构建测试集，包含 {len(test_cases)} 个测试用例")
        
        # 保存测试集
        save_path = "./data/test_set/test_set.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        
        print(f"测试集已保存到: {save_path}")
        return save_path

    def evaluate_system(self, test_set_path):
        """
        评估系统性能
        
        Args:
            test_set_path: 测试集路径
            
        Returns:
            dict: 评估结果
        """
        print(f"评估系统性能，测试集: {test_set_path}")
        
        # 加载测试集
        with open(test_set_path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
        
        # 评估结果
        evaluation_results = {
            "total_cases": len(test_cases),
            "qa_results": [],
            "search_results": [],
            "metrics": {}
        }
        
        # 评估问答系统
        qa_correct = 0
        for case in test_cases:
            if case.get("type") == "qa":
                result = self.rag_qa_system(case["question"])
                # 简单的评估（基于是否包含关键词）
                correct = any(keyword in result["answer"] for keyword in case.get("keywords", []))
                if correct:
                    qa_correct += 1
                evaluation_results["qa_results"].append({
                    "question": case["question"],
                    "answer": result["answer"],
                    "correct": correct
                })
            elif case.get("type") == "search":
                result = self.cross_modal_search(case["query"], case["search_type"])
                evaluation_results["search_results"].append({
                    "query": case["query"],
                    "search_type": case["search_type"],
                    "results": result
                })
        
        # 计算指标
        if evaluation_results["qa_results"]:
            evaluation_results["metrics"]["qa_accuracy"] = qa_correct / len(evaluation_results["qa_results"])
        
        # 保存评估结果
        save_path = "./data/evaluation/evaluation_results.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, ensure_ascii=False, indent=2)
        
        print(f"评估结果已保存到: {save_path}")
        return evaluation_results

    def batch_process_artworks(self, artworks):
        """
        批量处理艺术品数据
        
        Args:
            artworks: 艺术品数据列表
            
        Returns:
            list: 处理结果
        """
        results = []
        
        for artwork in artworks:
            # 步骤1: 导入到知识图谱
            kg_result = self.kg_manager.import_artwork_data(artwork)
            
            # 步骤2: 对齐处理
            image_paths = artwork.get("image_paths", [])
            texts = [artwork.get("description", "")]
            alignment_result = self.alignment_service.align_entity(
                artwork.get("title"),
                "Artwork",
                image_paths,
                texts
            )
            
            results.append({
                "artwork": artwork.get("title"),
                "kg_imported": kg_result,
                "alignment_result": alignment_result
            })
        
        return results

# 测试代码
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 初始化应用服务
    app_service = ApplicationService(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "Zyr123456")
    )
    
    # 测试智能问答系统
    print("测试智能问答系统...")
    qa_result = app_service.rag_qa_system("清明上河图的作者是谁？")
    print(f"回答: {qa_result['answer']}")
    
    # 测试跨模态检索
    print("\n测试跨模态检索...")
    search_result = app_service.cross_modal_search("山水画", "text_to_image")
    print(f"检索结果: {len(search_result)} 个结果")
    
    # 测试构建测试集
    print("\n测试构建测试集...")
    test_cases = [
        {
            "type": "qa",
            "question": "清明上河图描绘了什么内容？",
            "keywords": ["汴京", "繁华", "市井生活"]
        },
        {
            "type": "qa",
            "question": "张择端是哪个朝代的画家？",
            "keywords": ["北宋"]
        },
        {
            "type": "search",
            "query": "青绿山水",
            "search_type": "text_to_image"
        }
    ]
    test_set_path = app_service.build_test_set(test_cases)
    
    # 测试评估系统
    print("\n测试评估系统...")
    evaluation_result = app_service.evaluate_system(test_set_path)
    print(f"评估结果: {evaluation_result['metrics']}")
