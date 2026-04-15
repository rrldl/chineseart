#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import re
from typing import Dict, List, Any
from dotenv import load_dotenv
from py2neo import Graph
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
import argparse
import numpy as np

import requests
import os
from langchain_community.chat_models import ChatTongyi  # 阿里云
from langchain_community.llms import Ollama             # 本地


# 尝试导入sentence_transformers，如果失败则给出提示
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("=" * 80)
    print("警告: sentence-transformers 库未安装。语义相似度计算将不可用。")
    print("请运行: pip install sentence-transformers")
    print("=" * 80)
    SentenceTransformer = None
    util = None

# 加载环境变量
load_dotenv()
console = Console()


class OllamaConnectionError(Exception):
    """自定义异常，用于表示Ollama连接失败"""
    pass


class Neo4jRAGSystem:
    """中国古代书画问答系统 (优先使用Ollama直接回答)"""

    BUDGET_MODES = {
        "详细": {
            "entity_limit": 5, "relation_limit": 20, "top_k_triples": 10,
        },
        "标准": {
            "entity_limit": 3, "relation_limit": 15, "top_k_triples": 7,
        }
    }

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 llm_mode: str = "cloud",            # 默认云端模式
                 dashscope_api_key: str = None,      # 阿里云 API Key
                 ali_model: str = "qwen-plus",       # 阿里云模型名
                 ollama_model: str = "qwen2.5:3b",   # 本地模型名
                 enable_multi_hop: bool = True,
                 search_budget_mode: str = "标准", 
                 ollama_host: str = None):
        """
        初始化书画问答系统 (已优化: 支持云端API/本地Ollama双模切换)
        """
        self.console = console
        self.llm_mode = llm_mode
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # 统一大模型对象及状态标记
        self.llm = None
        self.llm_available = False
        self.ollama_available = False # 保持原变量名以兼容后续代码逻辑

        # 1. 搜索预算设置 (保持原逻辑)
        if search_budget_mode not in self.BUDGET_MODES:
            self.console.print(f"[bold red]警告：未知的搜索预算模式 '{search_budget_mode}'。使用 '标准'。[/bold red]")
            search_budget_mode = "标准"
        self.search_budget = self.BUDGET_MODES[search_budget_mode]
        self.enable_multi_hop = enable_multi_hop

        self.console.print(f"模式: [bold green]{'云端API' if llm_mode == 'cloud' else '本地Ollama'}[/bold green]")
        self.console.print(f"搜索预算模式: [bold magenta]{search_budget_mode}[/bold magenta]")

        with self.console.status("[bold green]正在初始化中国古代书画问答系统...", spinner="dots"):
            # 2. 连接 Neo4j 数据库
            try:
                self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
                self.console.print("✅ Neo4j数据库连接成功", style="green")
            except Exception as e:
                self.console.print(f"❌ Neo4j连接失败: {e}", style="bold red")
                raise

            # 3. 初始化 LLM 引擎 (优先云端，回退本地)
            self._init_llm_engine(dashscope_api_key, ali_model)

            # 4. 如果大模型不可用，执行降级逻辑 (加载 SentenceTransformer 和实体列表)
            # 注意：后续代码通常检查 self.ollama_available，这里我们同步状态
            if not self.llm_available:
                self.console.print("[bold yellow]⚠ 大模型引擎不可用，将回退到知识图谱基础查询模式[/bold yellow]")

                # 动态获取实体和关系类型
                try:
                    self.ENTITY_TYPES = [record["label"] for record in self.graph.run("CALL db.labels()")]
                    self.RELATION_TYPES = [record["relationshipType"] for record in
                                           self.graph.run("CALL db.relationshipTypes()")]
                    self.console.print("✅ 动态获取实体和关系类型成功", style="green")
                except Exception:
                    self.console.print("⚠ 无法动态获取类型，将使用预定义列表", style="yellow")
                    self.ENTITY_TYPES = ['Artwork', 'Artist', 'Dynasty', 'Style', 'Collection', 'Seal', 'Inscription', 'Person']
                    self.RELATION_TYPES = ['CREATED_BY', 'PART_OF', 'LIVED_IN', 'HAS_STYLE', 'STORED_IN', 'HAS_SEAL', 'OWNED_BY']

                # 加载语义模型用于相似度计算
                if SentenceTransformer:
                    try:
                        self.embedding_model = SentenceTransformer('moka-ai/m3e-base')
                        self.console.print("✅ 语义相似度模型 (m3e-base) 加载成功", style="green")
                    except Exception as e:
                        self.console.print(f"❌ 语义相似度模型加载失败: {e}", style="bold red")
                        self.embedding_model = None
                else:
                    self.embedding_model = None

                self.entity_extraction_prompt = self._get_entity_extraction_prompt()

            self.console.print("✅ 中国古代书画问答系统初始化完成!", style="bold green")
    def _init_llm_engine(self, api_key, ali_model):
        """
        内部函数：根据模式初始化具体的LLM
        支持云端 ChatTongyi 和 本地 Ollama 的统一封装
        """
        self.llm_available = False
        self.ollama_available = False  # 此变量在后续逻辑中作为“模型是否可用”的全局开关

        # --- A. 尝试云端模式 ---
        if self.llm_mode == "cloud":
            if not api_key:
                self.console.print("❌ 错误: 云端模式缺少 API Key，请检查 .env 文件或参数", style="bold red")
            else:
                try:
                    self.console.print(f"🚀 正在连接阿里云 Qwen API ({ali_model})...", style="blue")
                    from langchain_community.chat_models import ChatTongyi
                    
                    # 初始化云端模型
                    self.llm = ChatTongyi(
                        dashscope_api_key="sk-18e0af55804c4829ae1bea3fb95c4aa9", 
                        model_name=ali_model,
                        streaming=False
                    )
                    
                    # 进行一次简单的连通性测试
                    # 注意：如果网络不通或 API Key 错误，这里会抛出异常
                    self.llm.invoke("connection test")
                    
                    self.llm_available = True
                    self.ollama_available = True # 设置为 True 兼容后续代码逻辑
                    self.console.print(f"✅ 云端模型 '{ali_model}' 已成功挂载并就绪", style="bold green")
                    return # 云端成功直接返回，不再尝试本地
                except Exception as e:
                    self.console.print(f"⚠ 云端连接失败: {e}", style="yellow")
                    self.console.print("尝试回退到本地 Ollama 模式...", style="dim")

        # --- B. 尝试本地 Ollama 模式 ---
        # 只有当云端模式未启用，或云端初始化失败时才会执行到这里
        try:
            self.console.print(f"📡 探测本地 Ollama 服务 ({self.ollama_host})...", style="blue")
            from langchain_community.llms import Ollama
            
            # 1. 首先探测端口是否开放 (超时时间设短一点，避免卡死)
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=3)
            
            if response.status_code == 200:
                self.llm = Ollama(
                    base_url=self.ollama_host, 
                    model=self.ollama_model,
                    timeout=60 # 本地运行较慢，增加超时
                )
                # 2. 预热模型测试
                self.llm.invoke("Hi")
                
                self.llm_available = True
                self.ollama_available = True
                self.console.print(f"✅ 本地模型 '{self.ollama_model}' 已就绪", style="green")
            else:
                self.console.print(f"❌ Ollama 服务返回状态码: {response.status_code}", style="red")
                self.llm_available = False
                self.ollama_available = False
        except Exception as e:
            self.console.print(f"❌ 本地 Ollama 连接失败: {e}", style="red")
            self.console.print("[dim]提示：如果不需要本地模型，请确保云端 API 配置正确[/dim]")
            self.llm_available = False
            self.ollama_available = False
    


    # def _test_ollama_connection(self):
    #     """测试Ollama连接"""
    #     try:
    #         self.console.print("测试Ollama连接...", style="blue")
    #         ollama_url = f"{self.ollama_host}/api/tags"
    #         response = requests.get(ollama_url, timeout=10)
    #         if response.status_code == 200:
    #             models = response.json().get('models', [])
    #             model_names = [model.get('name', '未知') for model in models]
    #             self.console.print(f"✅ Ollama连接成功，可用模型: {', '.join(model_names)}", style="green")
    #             self.ollama_available = True

    #             # 测试模型是否能正常响应
    #             test_prompt = "你好，请回复'连接测试成功'"
    #             try:
    #                 test_response = requests.post(
    #                     f"{self.ollama_host}/api/generate",
    #                     json={"model": self.ollama_model, "prompt": test_prompt, "stream": False},
    #                     timeout=15
    #                 )
    #                 if test_response.status_code == 200:
    #                     self.console.print(f"✅ Ollama模型 '{self.ollama_model}' 响应正常", style="green")
    #                 else:
    #                     self.console.print(f"⚠ 模型测试响应状态码: {test_response.status_code}", style="yellow")
    #             except Exception as e:
    #                 self.console.print(f"⚠ 模型测试失败: {e}", style="yellow")
    #         else:
    #             self.console.print(f"❌ Ollama连接测试返回状态码: {response.status_code}", style="red")
    #             self.ollama_available = False
    #     except requests.exceptions.ConnectionError:
    #         self.console.print(f"❌ 无法连接到Ollama服务 ({self.ollama_host})", style="bold red")
    #         self.console.print("请确保Ollama正在运行且地址正确", style="yellow")
    #         self.ollama_available = False
    #     except Exception as e:
    #         self.console.print(f"❌ Ollama连接测试失败: {e}", style="red")
    #         self.ollama_available = False

    def _get_entity_extraction_prompt(self) -> str:
        # return f"""
        # 你是一个专业的中国古代书画实体关系抽取助手。你的任务是从用户关于中国古代书画的问题中提取关键实体。

        # 可识别的实体类型: {self.ENTITY_TYPES}

        # 请仅提取文本中明确提到的实体。你的输出必须是严格的JSON格式，并用Markdown的json代码块包裹，只包含一个 "entities" 键。

        # ### ⚠️ 重要指令
        # 1. 必须使用 "title" 作为实体名称的键。禁止使用 "name"。
        # 2. 实体类型必须从以下列表中选择: {self.ENTITY_TYPES}

        # 实体格式: {{"title": "实体名称", "type": "实体类型"}}

        # 示例:
        # 输入: 《清明上河图》的作者是谁？
        # 输出:
        # ```json
        # {{
        #   "entities": [
        #     {{"title": "清明上河图", "type": "Artwork"}}
        #   ]
        # }}
        # ```

        # 请严格按照此格式输出，不要添加任何解释。
        # """
        return """
        你是一个书画领域的知识图谱专家。
        任务：从用户的问题中提取【核心实体】（人名、画名、流派名、朝代等）。
        
        【约束条件】：
        1. 严禁输出任何解释、开场白、标点符号。
        2. 只输出实体名称，多个实体用英文逗号分隔。
        3. 如果没有实体，只输出“无”。

        【示例】：
        问：张择端的清明上河图在哪？
        答：张择端,清明上河图

        问：介绍一下青绿山水。
        答：青绿山水

        问：{query}
        答："""

    def _get_direct_answer_prompt(self) -> str:
        """直接回答问题的提示词"""
        return """
        你是一个专业的中国古代书画问答助手，知识渊博、严谨且富有文采。
        请用专业、准确、结构化的中文回答用户关于中国古代书画的问题。

        **重要格式要求**:
        1. **使用Markdown格式**: 请使用Markdown格式来美化回答，包括标题、列表、加粗等
        2. **结构清晰**: 使用分级标题(###)来组织不同部分
        3. **美观列表**: 使用有序列表(1., 2., 3.)或无序列表(-)来展示多项内容
        4. **适当空行**: 在段落、标题和列表之间添加适当的空行
        5. **专业术语**: 使用专业的书画术语（如朝代、技法、风格等）
        6. **优雅表达**: 语言要流畅，符合中文语境，可适当带有一些书卷气

        **回答格式示例**:
        ### 张大千的艺术成就
        张大千是20世纪中国画坛的重要画家之一，他在山水、花鸟、人物等多个领域均有卓越成就。

        ### 代表作品
        1. **《爱痕湖》** - 1968年作于美国加州，描绘了南美安第斯山脉的风光
        2. **《庐山图》** - 创作风格融合中西技法，展现了庐山的雄奇秀丽
        3. **《墨荷图》** - 擅用水墨技巧表现荷花，尤显其高超技艺

        ### 艺术特点
        - **创新精神**: 融合中西绘画技法
        - **技法全面**: 山水、花鸟、人物均有建树
        - **市场价值**: 作品在拍卖市场上屡创天价

        请按照这种清晰美观的格式来组织你的回答。
        """

    def _format_ollama_response(self, content: str) -> str:
        """
        格式化Ollama返回的文本，使其更美观
        """
        if not content:
            return content

        # 1. 清理多余的空白字符
        content = content.strip()

        # 2. 移除所有加粗标记
        content = content.replace('**', '')

        # 3. 处理标题标记，将#标题转换为HTML标题
        lines = content.split('\n')
        formatted_lines = []
        empty_line_count = 0

        for line in lines:
            line = line.strip()
            if line:
                # 检查是否是标题行（以1-3个#开头，或者看起来像标题）
                is_title = False
                
                # 检查是否以#开头
                title_match = re.match(r'^(#{1,3})\s*(.+)$', line)
                if title_match:
                    title_text = title_match.group(2)
                    formatted_lines.append(f'<h3>{title_text}</h3>')
                    is_title = True
                # 检查是否是短文本且后面有冒号，或者看起来像标题
                elif len(line) < 15 and (line.endswith('：') or line.endswith(':') or 
                                        line.endswith('说明') or line.endswith('定位') or 
                                        line.endswith('宗旨') or line.endswith('基')):
                    title_text = line.rstrip('：:')
                    formatted_lines.append(f'<h3>{title_text}</h3>')
                    is_title = True
                else:
                    formatted_lines.append(line)
                
                empty_line_count = 0
            else:
                empty_line_count += 1
                if empty_line_count == 1 and formatted_lines:
                    formatted_lines.append('')

        # 4. 清理开头和结尾的空行
        while formatted_lines and not formatted_lines[0]:
            formatted_lines.pop(0)
        while formatted_lines and not formatted_lines[-1]:
            formatted_lines.pop()

        # 5. 合并处理好的行
        result = '\n'.join(formatted_lines)

        return result

    def call_ollama_direct_answer(self, question: str) -> str:
        """统一调用大模型（云端或本地）直接回答问题"""
        try:
            # 这里的 self.llm 已经在 _init_llm_engine 中根据模式（cloud/local）初始化好了
            if not self.llm:
                raise OllamaConnectionError("模型引擎未初始化")

            self.console.print(f"[dim]正在调用 {'云端' if self.llm_mode == 'cloud' else '本地'} 模型回答问题...[/dim]")
            
            # 1. 构造提示词
            system_prompt = self._get_direct_answer_prompt()
            
            # 2. 调用模型 (LangChain 统一接口)
            # 云端 Qwen 返回的是 BaseMessage 对象，本地 Ollama 可能返回字符串
            response = self.llm.invoke(f"{system_prompt}\n\n用户问题：{question}")
            
            # 3. 提取内容
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)

            if not content:
                raise OllamaConnectionError("模型返回了空内容")

            # 4. 格式化处理回答内容（美化 Markdown）
            formatted_content = self._format_ollama_response(content)
            return formatted_content

        except Exception as e:
            self.console.print(f"[red]模型调用出错: {e}[/red]")
            raise OllamaConnectionError(f"调用失败: {e}")

    def answer_question(self, question: str) -> str:
        try:
            self.console.print(Panel(f"[bold]问题[/bold]: {question}", title="中国古代书画问答", border_style="cyan"))

            # 优先使用Ollama直接回答问题
            if self.ollama_available:
                self.console.print("[bold green]✅ Ollama可用，优先使用Ollama回答问题[/bold green]")
                with self.console.status("[bold green]Ollama正在思考...", spinner="dots"):
                    try:
                        answer = self.call_ollama_direct_answer(question)
                        self.console.print(Panel(Markdown(answer), title="Ollama回答", border_style="green"))
                        return answer
                    except OllamaConnectionError as e:
                        self.console.print(f"[yellow]⚠ Ollama回答失败: {e}[/yellow]")
                        self.console.print("[yellow]回退到知识图谱查询模式...[/yellow]")
                        self.ollama_available = False  # 标记为不可用
            else:
                self.console.print("[bold yellow]⚠ Ollama不可用，使用知识图谱查询[/bold yellow]")

            # 回退到知识图谱查询
            return self._answer_with_knowledge_graph(question)

        except Exception as e:
            error_msg = f"系统处理时出现严重错误: {e}"
            self.console.print(Panel(error_msg, title="错误", border_style="bold red"))
            import traceback
            self.console.print(f"[red]详细错误信息:\n{traceback.format_exc()}[/red]")
            return error_msg

    def _answer_with_knowledge_graph(self, question: str) -> str:
        """使用知识图谱回答问题"""
        self.console.print("[bold blue]正在使用知识图谱查询...[/bold blue]")

        # 1. 提取实体
        extraction_result = self.extract_entities_relations(question)

        # 2. 查询知识图谱
        knowledge = self.query_neo4j(question, extraction_result.get("entities", []))

        # 3. 检查是否有信息
        has_knowledge = knowledge['entity_properties'] or knowledge['related_triples']

        if not has_knowledge:
            self.console.print("[yellow]⚠ 知识图谱中未找到相关信息。[/yellow]")
            return "抱歉，我在知识图谱中未能找到关于这个问题的相关信息。"

        # 4. 生成基于知识图谱的回答
        answer = self._generate_knowledge_based_answer(question, knowledge)
        self.console.print(Panel(Markdown(answer), title="知识图谱回答", border_style="yellow"))
        return answer

    def extract_entities_relations(self, text: str) -> Dict:
        self.console.print(Panel(f"[bold blue]问题分析[/bold blue]：\n{text}", border_style="blue"))
        with self.console.status("[bold green]正在分析问题，提取实体...", spinner="dots"):
            try:
                # 简单的基于规则的实体提取
                return self._simple_entity_extraction(text)
            except Exception as e:
                self.console.print(f"[red]实体抽取出错: {e}[/red]", style="bold red")
                return {"entities": []}
    def extract_entities_relations(self, text: str) -> Dict:
        """利用 LLM 提取实体，而不是靠正则"""
        if not self.llm_available:
            return self._simple_entity_extraction(text)
            
        with self.console.status("[bold green]正在分析实体...", spinner="dots"):
            prompt = self._get_entity_extraction_prompt().format(query=text)
            try:
                # 让 LLM 返回逗号分隔的实体名
                res = self.llm.invoke(prompt)
                content = res.content if hasattr(res, 'content') else str(res)
                
                if "无" in content:
                    return {"entities": []}
                
                entity_names = [e.strip() for e in content.split(',')]
                entities = [{"title": name, "type": "Unknown"} for name in entity_names]
                
                self._display_extraction_results(entities)
                return {"entities": entities}
            except:
                return self._simple_entity_extraction(text)

    # def _simple_entity_extraction(self, text: str) -> Dict:
    #     """简单的基于规则的实体提取"""
    #     entities = []

    #     # 提取可能的画作名称（带《》的）
    #     artwork_pattern = r'《([^》]+)》'
    #     artworks = re.findall(artwork_pattern, text)
    #     for artwork in artworks:
    #         entities.append({"title": artwork, "type": "Artwork"})

    #     # 提取可能的朝代
    #     dynasty_keywords = ['唐代', '唐朝', '宋代', '宋朝', '元代', '元朝', '明代', '明朝',
    #                         '清代', '清朝', '唐', '宋', '元', '明', '清', '五代', '魏晋', '秦汉']
    #     for dynasty in dynasty_keywords:
    #         if dynasty in text:
    #             entities.append({"title": dynasty, "type": "Dynasty"})

    #     # 提取可能的画家/作者关键词
    #     artist_keywords = ['画家', '作者', '张择端', '唐寅', '文徵明', '徐渭', '八大山人',
    #                        '齐白石', '徐悲鸿', '吴昌硕', '黄公望', '王羲之', '颜真卿']
    #     for keyword in artist_keywords:
    #         if keyword in text:
    #             entities.append({"title": keyword, "type": "Artist"})

    #     # 提取风格关键词
    #     style_keywords = ['山水画', '水墨画', '工笔画', '写意画', '青绿山水', '文人画', '花鸟画']
    #     for keyword in style_keywords:
    #         if keyword in text:
    #             entities.append({"title": keyword, "type": "Style"})

    #     self._display_extraction_results(entities)
    #     return {"entities": entities}

    def _display_extraction_results(self, entities: List[Dict]):
        if not entities:
            self.console.print("[yellow]未从问题中提取到明确的实体。[/yellow]")
            return

        entity_table = Table(title="提取的书画实体", show_header=True, header_style="bold green")
        entity_table.add_column("实体名称", style="cyan")
        entity_table.add_column("实体类型", style="magenta")
        for entity in entities:
            entity_name = entity.get("title") or entity.get("name") or "未知"
            entity_type = entity.get("type", "未知")
            entity_table.add_row(entity_name, entity_type)

        self.console.print(entity_table)

    def query_neo4j(self, question: str, entities: List[Dict]) -> Dict:
        self.console.print(Panel("[bold green]知识图谱查询[/bold green]", border_style="green"))
        result = {"entity_properties": [], "related_triples": []}

        if not entities:
            self.console.print("[yellow]⚠ 无明确实体，尝试执行宽泛搜索。[/yellow]")
            return result

        with self.console.status("[bold blue]正在查询书画知识图谱...", spinner="dots"):
            all_triples = []
            queried_entities = set()

            for entity in entities:
                # 获取实体名称
                entity_title = entity.get("title") or entity.get("name")

                if not entity_title:
                    continue

                if entity_title in queried_entities:
                    continue

                queried_entities.add(entity_title)
                self.console.print(f"查询实体: [cyan]{entity_title}[/cyan]")

                # 1. 获取实体本身属性
                query_props = "MATCH (n {title: $entity_title}) RETURN n LIMIT 1"
                try:
                    node_data = self.graph.run(query_props, entity_title=entity_title).data()
                except Exception as e:
                    self.console.print(f"[red]查询实体属性失败: {e}[/red]")
                    node_data = []

                if node_data:
                    record = node_data[0]
                    node = record['n']
                    node_properties = dict(node)

                    if 'title' not in node_properties:
                        node_properties['title'] = entity_title

                    result["entity_properties"].append(
                        {"title": entity_title, "properties": node_properties, "labels": list(node.labels)})

                    self.console.print(f"[green]✅ 找到实体: {entity_title}[/green]")
                else:
                    self.console.print(f"[yellow]⚠ 未找到实体: {entity_title}[/yellow]")

                # 2. 获取与实体直接相关的三元组
                query_relations = """
                    MATCH (s)-[r]->(t)
                    WHERE s.title = $entity_title OR t.title = $entity_title
                    RETURN s.title as source, type(r) as relation, t.title as target, 
                           labels(s) as s_labels, labels(t) as t_labels
                    LIMIT 20
                """

                try:
                    triples = self.graph.run(query_relations, entity_title=entity_title).data()
                except Exception as e:
                    self.console.print(f"[red]查询关系失败: {e}[/red]")
                    triples = []

                for t in triples:
                    source_title = t.get('source')
                    target_title = t.get('target')
                    relation = t.get('relation')

                    if source_title and target_title and relation:
                        all_triples.append({
                            "source": {"name": source_title, "labels": t.get('s_labels', [])},
                            "relation": relation,
                            "target": {"name": target_title, "labels": t.get('t_labels', [])}
                        })

            result["related_triples"] = all_triples[:10]  # 限制数量

        self.console.print(
            f"知识图谱查询完成: 找到 {len(result['entity_properties'])} 个实体属性, {len(result['related_triples'])} 个关系。",
            style="bold green")

        return result

    def _generate_knowledge_based_answer(self, question: str, knowledge: Dict) -> str:
        """基于知识图谱信息生成回答"""
        answer_parts = ["### 查询结果"]

        if knowledge['entity_properties']:
            answer_parts.append("#### 实体信息")
            for entity in knowledge['entity_properties']:
                title = entity['title']
                props = entity['properties']

                info_parts = []
                if 'description' in props and props['description']:
                    desc = props['description']
                    if len(desc) > 300:
                        desc = desc[:300] + "..."
                    info_parts.append(desc)

                if 'author' in props and props['author']:
                    info_parts.append(f"**作者**：{props['author']}")

                if 'dynasty' in props and props['dynasty']:
                    info_parts.append(f"**朝代**：{props['dynasty']}")

                if 'style' in props and props['style']:
                    info_parts.append(f"**风格**：{props['style']}")

                if 'date' in props and props['date']:
                    info_parts.append(f"**创作时间**：{props['date']}")

                if info_parts:
                    answer_parts.append(f"**{title}**：" + "；".join(info_parts))
                answer_parts.append("")  # 添加空行

        if knowledge['related_triples']:
            answer_parts.append("#### 相关关系")
            for triple in knowledge['related_triples'][:5]:
                source = triple['source']['name']
                relation = triple['relation']
                target = triple['target']['name']

                relation_display = {
                    'CREATED_BY': '创作于',
                    'PART_OF': '属于',
                    'HAS_STYLE': '具有风格',
                    'HAS_SEAL': '有印章',
                    'HAS_INSCRIPTION': '有题跋'
                }.get(relation, relation)

                answer_parts.append(f"- {source} {relation_display} {target}")
            answer_parts.append("")  # 添加空行

        answer_parts.append("*注：此回答基于知识图谱中的结构化信息生成。*")

        # 格式化回答
        formatted_answer = '\n'.join(answer_parts)
        return self._format_ollama_response(formatted_answer)

    def test_database_connection(self):
        """测试数据库连接和内容"""
        self.console.print("[bold yellow]测试数据库连接和内容...[/bold yellow]")

        # 测试1: 查询节点数量
        try:
            query = "MATCH (n) RETURN count(n) as total"
            result = self.graph.run(query).data()
            total_nodes = result[0]['total']
            self.console.print(f"[green]✅ 数据库中共有 {total_nodes} 个节点[/green]")
        except Exception as e:
            self.console.print(f"[red]❌ 查询节点总数失败: {e}[/red]")

        # 测试2: 查询Artwork节点
        try:
            query = "MATCH (n:Artwork) RETURN n.title as title LIMIT 10"
            results = self.graph.run(query).data()
            if results:
                self.console.print(f"[green]✅ 找到 {len(results)} 个作品:[/green]")
                for r in results:
                    self.console.print(f"  - {r['title']}")
            else:
                self.console.print("[yellow]⚠ 未找到任何Artwork节点[/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ 查询Artwork失败: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(description="中国古代书画问答系统")
    parser.add_argument("--neo4j_uri", type=str, default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--neo4j_user", type=str, default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j_password", type=str, default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument("--ollama_model", type=str, default=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"), help="Ollama模型")
    parser.add_argument("--ollama_host", type=str, default=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                        help="Ollama服务地址")
    parser.add_argument("--search_budget", type=str, default="标准", choices=["详细", "标准"])
    parser.add_argument("--test_db", action="store_true", help="测试数据库连接")
    args = parser.parse_args()

    if not args.neo4j_password:
        console.print("[bold red]错误: Neo4j 密码未设置。请通过 --neo4j_password 参数或 .env 文件提供。[/bold red]")
        return

    console.print(Panel("[bold cyan]中国古代书画问答系统[/bold cyan]\n传承中华文化，弘扬书画艺术", border_style="cyan",
                        title="欢迎"))

    try:
        rag_system = Neo4jRAGSystem(
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password,
            ollama_model=args.ollama_model,
            ollama_host=args.ollama_host,
            search_budget_mode=args.search_budget
        )

        # 明确显示Ollama状态
        if rag_system.ollama_available:
            console.print("[bold green]✓ Ollama服务可用，将优先使用Ollama回答问题[/bold green]")
        else:
            console.print("[bold yellow]⚠ Ollama服务不可用，将使用知识图谱查询[/bold yellow]")

        # 如果指定了测试数据库，运行测试
        if args.test_db:
            rag_system.test_database_connection()
            return

    except Exception as e:
        console.print(f"系统初始化失败，请检查配置。错误: {e}")
        import traceback
        console.print(f"[red]详细错误信息:\n{traceback.format_exc()}[/red]")
        return

    console.print("输入 'exit' 或 'quit' 结束对话。", style="blue")
    while True:
        try:
            question = console.input("\n[bold]请输入您的问题：[/bold]")
            if question.lower() in ['exit', 'quit', '退出']:
                console.print("感谢使用！再见！", style="bold cyan")
                break
            if not question.strip():
                continue
            rag_system.answer_question(question)
        except KeyboardInterrupt:
            console.print("\n\n感谢使用！再见！", style="bold cyan")
            break
        except Exception as e:
            console.print(f"❌ 系统运行时发生错误: {e}", style="bold red")


if __name__ == "__main__":
    main()