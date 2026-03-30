# 墨韵灵境 — 中国古代书画多模态知识图谱系统

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-Compatible-brightgreen?logo=neo4j)
![CLIP](https://img.shields.io/badge/CLIP-Multimodal_Model-7A4FFF?logo=pytorch&logoColor=white)
![FastSAM](https://img.shields.io/badge/FastSAM-Image_Segmentation-orange?logo=pytorch&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-NLP_Framework-purple?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📋 项目概述

**墨韵灵境**是一个基于**多模态知识图谱**的中国古代书画智能分析与搜索系统，融合了**知识图谱（Neo4j）**、**多模态对齐（LA-CLIP）**、**图像分割（FastSAM）**和**自然语言处理（LangChain）**等先进技术，实现了从数据采集、语义对齐到智能应用的完整流程。

系统以**多源异构数据采集与预处理**为基础，通过**LA-CLIP驱动的细粒度语义对齐**为核心技术，构建**多模态知识存储与融合**的图谱层，最终提供**智能问答**和**跨模态检索**等应用服务。

## 🎯 核心功能

### 1. 数据层：多源异构数据采集与预处理
- ✅ **图像数据处理**：使用FastSAM模型对高清书画图像进行语义分割，自动隔离画面主体、题跋、印章等区域
- ✅ **文本数据处理**：爬取百科网站文本，构建书画家知识库，使用LangChain进行智能分块和清洗
- ✅ **数据标准化**：对多模态数据进行汇聚、清洗和标准化处理，提供高质量数据原料

### 2. 对齐层：LA-CLIP驱动进行细粒度语义对齐
- ✅ **细粒度特征提取**：使用改进的LA-CLIP模型提取文本、图像、分段文本和图像块的特征向量
- ✅ **对齐节点生成**：通过门控权重聚合跨模态特征，生成统一的"对齐专用"节点
- ✅ **关联入库**：通过hasAlignment关系链接实体与对齐节点，形成"实体-对齐专用节点-特征"三角闭环

### 3. 图谱层：多模态知识存储与融合
- ✅ **本体构建**：设计面向书画领域的本体，定义核心实体类型及其关系
- ✅ **知识抽取与融合**：利用大语言模型进行零样本知识抽取，自动生成三元组
- ✅ **向量索引构建**：为实体节点和对齐属性节点构建向量索引，支持语义相似性检索
- ✅ **网络连接性**：确保所有节点都集成到主网络中，无孤立节点

### 4. 应用层：智能服务与验证
- ✅ **智能问答系统**：基于RAG框架构建书画知识问答系统，融合向量检索和知识图谱查询
- ✅ **跨模态检索引擎**：支持"以图搜图"、"以文搜图"和"以图搜文"的检索功能
- ✅ **批量对齐工具**：支持大规模实体的批量语义对齐，提高系统构建效率

## 📁 项目结构

```
Chineseart/
├── artwork_images/          # 艺术品图像库
│   ├── artists/            # 艺术家图像
│   └── artworks/           # 画作图像
├── data/                   # 数据存储
│   ├── alignment/          # 对齐数据
│   ├── artists/            # 艺术家数据
│   ├── cache/              # 缓存数据
│   ├── embeddings/         # 特征嵌入向量
│   ├── encyclopedia/       # 百科数据
│   ├── extracted_triples/  # 提取的三元组
│   ├── knowledge_graph/    # 知识图谱数据
│   └── vector_index/       # 向量索引
├── data_collection.py      # 文本数据采集与处理
├── artapp.py               # 项目主程序
├── artwork_segmentation.py # 图像分割服务
├── la_clip_alignment.py    # LA-CLIP语义对齐服务
├── knowledge_graph.py      # 知识图谱构建与管理
├── q_a.py                  # 智能问答系统
├── batch_align.py          # 批量对齐工具
├── comprehensive_relationship_builder.py  # 关系网络构建
├── isolation_resolution.py                # 孤立节点修复
├── final_network_connection.py            # 最终网络连接
├── ultra_massive_data_expansion.py        # 大规模数据扩展
├── final_node_boost.py                    # 节点数量提升
├── final_push_to_2000.py                  # 确保达到2000+节点
├── requirements.txt        # 项目依赖
├── .env                    # 环境配置
└── README.md               # 项目文档
```

## 🚀 快速开始

### 1. 环境准备

#### 1.1 安装依赖

```bash
pip install py2neo langchain beautifulsoup4 requests torch transformers pillow numpy scikit-learn sentence-transformers flask
```

#### 1.2 配置Neo4j数据库

1. 从[Neo4j官网](https://neo4j.com/download/)下载并安装Neo4j Desktop
2. 创建新的数据库实例，设置用户名和密码
3. 启动数据库服务

#### 1.3 配置环境变量

创建`.env`文件，配置以下参数：

```env
# Neo4j 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword

# 模型配置
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_HOST=http://localhost:11434
```

### 2. 数据层构建

#### 2.1 文本数据处理

运行`data_collection.py`，爬取百科网站文本，构建书画家知识库：

```bash
python data_collection.py
```

#### 2.2 图像数据处理

运行`artwork_segmentation.py`，使用FastSAM模型对书画图像进行语义分割：

```bash
python artwork_segmentation.py
```

### 3. 图谱层构建

#### 3.1 初始化知识图谱

运行`knowledge_graph.py`，构建本体结构，定义实体类型和关系：

```bash
python knowledge_graph.py
```

#### 3.2 大规模节点扩展

依次运行以下脚本，扩展节点数量至2000+：

```bash
# 扩展至1000+节点
python ultra_massive_data_expansion.py

# 进一步增加节点
python final_node_boost.py

# 确保达到2000+节点
python final_push_to_2000.py
```

#### 3.3 构建关系网络

运行`comprehensive_relationship_builder.py`，构建密集的关系网络：

```bash
python comprehensive_relationship_builder.py
```



### 4. 对齐层构建

运行`batch_align.py`，对实体进行批量语义对齐：

```bash
# 对齐所有实体类型
python batch_align.py

# 对齐特定实体类型
python batch_align.py --types Artist Artwork Style

# 限制每类实体数量
python batch_align.py --limit 10
```

### 5. 应用层部署

#### 5.1 智能问答系统

运行`artapp.py`，启动基于RAG框架的智能问答系统：

```bash
python artapp.py
```

#### 5.2 跨模态检索引擎

集成在Web前端中，支持"以图搜图"、"以文搜图"和"以图搜文"功能。

## 📊 技术架构

### 1. 系统架构层次

```
应用层 (智能问答、跨模态检索)
     ↑
图谱层 (本体构建、知识抽取、向量索引)
     ↑
对齐层 (细粒度特征提取、对齐节点生成、关联入库)
     ↑
数据层 (图像处理、文本处理、数据标准化)
```

### 2. 核心技术栈

| 技术 | 用途 | 版本要求 |
|------|------|----------|
| Python | 主要开发语言 | 3.9+ |
| Neo4j | 图数据库 | 5.0+ |
| PyTorch | 深度学习框架 | 2.0+ |
| CLIP | 多模态特征提取 | openai/clip-vit-base-patch32 |
| FastSAM | 图像分割 | 1.0+ |
| LangChain | NLP处理 | 0.0.352+ |
| Transformers | 预训练模型 | 4.35.2+ |
| Sentence-Transformers | 语义相似度计算 | 2.2.2+ |

### 3. 数据流处理

1. **数据采集**：从百科网站爬取文本，从博物馆获取图像
2. **数据预处理**：文本清洗与分块，图像分割与标准化
3. **特征提取**：使用CLIP模型提取文本和图像特征
4. **语义对齐**：生成对齐专用节点，构建多模态关联
5. **知识融合**：构建知识图谱，整合多源信息
6. **智能应用**：提供问答和检索服务

## 🖼️ 知识图谱结构

### 1. 核心实体类型

| 节点类型 | 标签 | 描述 | 示例 |
|---------|------|------|------|
| 艺术品 | `Artwork` | 画作信息 | 清明上河图、千里江山图 |
| 艺术家 | `Artist` | 艺术家信息 | 王希孟、张择端 |
| 朝代 | `Dynasty` | 朝代信息 | 北宋、元代 |
| 艺术流派 | `Style` | 艺术风格流派 | 吴门画派、松江派 |
| 历史事件 | `HistoricalEvent` | 历史事件信息 | 元祐党争、靖康之变 |
| 材料 | `Material` | 创作材料 | 宣纸、绢帛、毛笔 |
| 技术 | `Technique` | 创作技法 | 工笔、写意、没骨 |
| 主题 | `Theme` | 作品主题 | 山水、人物、花鸟 |
| 时期 | `Period` | 历史时期 | 唐代、宋代、元代 |
| 博物馆 | `Museum` | 收藏机构 | 故宫博物院、上海博物馆 |
| 收藏家 | `Collector` | 收藏者信息 | 乾隆皇帝、张伯驹 |
| 对齐节点 | `AlignmentNode` | 多模态对齐节点 | alignment_Artwork_清明上河图 |

### 2. 核心关系类型

| 关系类型 | 描述 | 示例 |
|---------|------|------|
| `CREATED_BY` | 作品由谁创作 | (清明上河图)-[:CREATED_BY]->(张择端) |
| `PART_OF` | 作品属于哪个朝代 | (清明上河图)-[:PART_OF]->(北宋) |
| `HAS_STYLE` | 作品具有什么风格 | (千里江山图)-[:HAS_STYLE]->(青绿山水) |
| `INFLUENCED_BY` | 艺术家受谁影响 | (文徵明)-[:INFLUENCED_BY]->(沈周) |
| `INFLUENCED` | 艺术家影响了谁 | (沈周)-[:INFLUENCED]->(文徵明) |
| `STORED_IN` | 作品收藏在哪个机构 | (清明上河图)-[:STORED_IN]->(故宫博物院) |
| `HAS_MATERIAL` | 作品使用什么材料 | (清明上河图)-[:HAS_MATERIAL]->(宣纸) |
| `USES_TECHNIQUE` | 作品使用什么技法 | (千里江山图)-[:USES_TECHNIQUE]->(工笔) |
| `HAS_THEME` | 作品具有什么主题 | (清明上河图)-[:HAS_THEME]->(山水) |
| `HAS_ALIGNMENT` | 实体有对齐节点 | (清明上河图)-[:HAS_ALIGNMENT]->(alignment_Artwork_清明上河图) |

## 🔧 模块功能详解

### 1. data_collection.py - 文本数据处理
- **功能**：爬取百科网站文本，构建书画家知识库
- **实现**：使用BeautifulSoup4爬取网页内容，使用LangChain进行智能分块和清洗
- **输出**：结构化的文档库，包含书画家生卒年、字号、师承关系、艺术风格等信息

### 2. artwork_segmentation.py - 图像分割服务
- **功能**：使用FastSAM模型对书画图像进行语义分割
- **实现**：加载预训练的FastSAM模型，对图像进行分割，隔离画面主体、题跋、印章等区域
- **输出**：分割后的图像块，用于后续的特征提取

### 3. la_clip_alignment.py - LA-CLIP语义对齐服务
- **功能**：实现多模态数据的细粒度语义对齐
- **实现**：
  - 提取图像和文本特征
  - 通过门控权重聚合跨模态特征
  - 生成统一的"对齐专用"节点
  - 通过hasAlignment关系链接实体与对齐节点
- **输出**：融合多模态特征的对齐节点，用于跨模态检索

### 4. knowledge_graph.py - 知识图谱构建与管理
- **功能**：构建书画领域本体，提取知识三元组，构建向量索引
- **实现**：
  - 定义核心实体类型和关系类型
  - 使用大语言模型提取三元组
  - 构建向量索引支持语义相似性检索
- **输出**：结构化的知识图谱，包含实体、关系和向量索引

### 5. q_a.py - 智能问答系统
- **功能**：基于RAG框架构建书画知识问答系统
- **实现**：
  - 优先使用Ollama直接回答问题
  - 回退到知识图谱查询模式
  - 融合向量检索和知识图谱查询结果
- **输出**：结构化的答案，包含相关知识和推理过程

### 6. batch_align.py - 批量对齐工具
- **功能**：对实体进行批量语义对齐
- **实现**：
  - 支持多种实体类型的对齐
  - 智能文本描述生成
  - 自动图像查找
  - 详细的统计和报告
- **输出**：对齐结果报告，包含成功率和耗时

## 📈 性能优化

### 1. 特征提取优化
- **批量处理**：支持批量提取特征，提高处理速度
- **缓存机制**：缓存已提取的特征，避免重复计算
- **设备选择**：自动选择GPU或CPU，充分利用硬件资源

### 2. 搜索优化
- **相似度阈值**：设置最小相似度阈值，过滤不相关结果
- **结果数量限制**：支持限制返回结果数量，提高响应速度
- **索引优化**：使用Neo4j索引，加速节点查询

### 3. 网络连接性优化
- **密集关系网络**：构建密集的关系网络，确保信息的关联性和完整性
- **孤立节点检测**：自动检测和修复孤立节点，确保网络完整性
- **批量关系构建**：批量创建关系，提高处理效率

## 🔍 批量对齐工具使用指南

### 1. 基本用法

```bash
# 对齐所有实体类型
python batch_align.py

# 对齐特定实体类型
python batch_align.py --types Artist Artwork Style

# 限制每类实体数量
python batch_align.py --limit 10

# 组合使用
python batch_align.py --types Artist Artwork --limit 20
```

### 2. 支持的实体类型

- `Artist` - 艺术家
- `Artwork` - 艺术品
- `Style` - 艺术流派
- `HistoricalEvent` - 历史事件
- `Material` - 材料
- `Technique` - 技术
- `Theme` - 主题
- `Period` - 时期
- `Museum` - 博物馆
- `Collector` - 收藏家

### 3. 输出报告

运行完成后，会生成详细的对齐报告，包括：
- 总处理数量和成功率
- 各实体类型的详细统计
- 总耗时和时间分布

## 🛠️ 开发指南

### 1. 模块扩展

系统采用模块化设计，便于扩展新功能：

- **新实体类型**：在`knowledge_graph.py`中添加新的实体类型定义
- **新关系类型**：在`knowledge_graph.py`中添加新的关系类型定义
- **新服务开发**：创建新的服务类，实现相应接口
- **模型替换**：支持替换为其他分割或特征提取模型

### 2. 调试模式

```bash
# 启用调试模式运行应用
python q_a.py

# 测试数据库连接
python q_a.py --test_db
```

调试模式下，系统会输出详细的日志信息，便于排查问题。

## 📁 数据存储

### 1. 数据目录结构

| 目录 | 用途 | 内容 |
|------|------|------|
| `data/alignment/` | 对齐数据 | 图像和文本向量 |
| `data/embeddings/` | 特征嵌入 | 实体的特征向量 |
| `data/encyclopedia/` | 百科数据 | 艺术家、风格等百科信息 |
| `data/knowledge_graph/` | 知识图谱数据 | 本体结构和配置 |
| `data/vector_index/` | 向量索引 | 用于语义相似性检索 |
| `artwork_images/` | 图像库 | 艺术家和作品图像 |

### 2. 数据格式

- **百科数据**：JSON格式，包含实体的详细信息
- **特征向量**：Numpy数组格式，存储在.npy文件中
- **对齐数据**：包含向量和元数据的结构化数据
- **知识图谱**：存储在Neo4j数据库中，包含节点和关系

## 🚩 部署注意事项

### 1. 硬件要求

- **CPU**：至少4核以上
- **内存**：至少16GB
- **GPU**：推荐使用NVIDIA GPU，支持CUDA（可选，用于加速特征提取）
- **存储空间**：至少50GB（包含图像数据和模型）

### 2. 软件要求

- **操作系统**：Windows 10+ 或 Linux
- **Python**：3.9+
- **Neo4j**：5.0+（推荐使用Neo4j Desktop）
- **Ollama**：用于本地大语言模型（可选）

### 3. 网络要求

- **互联网连接**：首次运行需要下载预训练模型
- **本地网络**：Neo4j和Ollama服务需要在本地网络中可访问

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送分支
5. 创建Pull Request

## 📬 联系与支持

如有问题或建议，请：

- 提交Issue
- 或联系项目维护者

## 🙏 致谢

- [Neo4j](https://neo4j.com/) — 图数据库引擎
- [OpenAI CLIP](https://github.com/openai/CLIP) — 多模态特征提取
- [FastSAM](https://github.com/CASIA-IVA-Lab/FastSAM) — 图像分割模型
- [LangChain](https://www.langchain.com/) — 语言模型应用框架
- [Hugging Face Transformers](https://huggingface.co/) — 预训练模型库

## 📄 许可证

本项目采用Apache 2.0许可证。详见[LICENSE](LICENSE)文件。

---

> **免责声明**：本系统生成的艺术分析信息仅供参考，不能替代专业艺术史研究！

> **注意**：系统使用的艺术品图像仅用于学术研究和教育目的，版权归原作者所有。

> **版本信息**：本文档对应项目版本为1.0.0，最后更新时间：2026-02-11
