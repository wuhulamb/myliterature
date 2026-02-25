# 文献管理系统

## 项目目标

开发一个基于大模型的文献管理工具，实现以下功能：
1. **文献整理**：读取PDF转换后的纯文本文件，利用LLM提取结构化信息（年份、期刊、题目、作者、主要内容总结），并存入SQLite数据库。
2. **多主题管理**：支持创建不同的主题，文献导入时需指定主题，实现分类存储。
3. **语义检索**：用户输入自然语言问题，系统将指定主题下的文献信息作为上下文传递给LLM，实现智能检索与回答。

## 环境准备

安装必要的依赖库：

```bash
pip install openai pydantic python-dotenv
```

在项目根目录创建 `.env` 文件，配置API密钥：

```
CHATECNU_API_KEY=your_api_key_here
```

## 核心功能

### 1. 数据提取与存储
- 输入：PDF转换后的纯文本文件。
- 处理：调用LLM提取以下字段：
  - `year`: 发表年份
  - `journal`: 期刊名称
  - `title`: 文献标题
  - `authors`: 作者列表
  - `summary`: **文献主要内容总结**（注意：非原文摘要，而是LLM对全文核心内容的概括）
- 存储：自动创建或关联指定主题，保存到本地SQLite数据库。

### 2. 语义检索
- 输入：用户提出的自然语言问题（如"有哪些关于深度学习的文献？"）。
- 处理：
  1. 从数据库中提取指定主题下的所有文献信息。
  2. 将文献信息整理为字符串上下文。
  3. 连同用户问题一起发送给LLM。
- 输出：LLM返回的相关文献ID列表及基于文献内容的回答。

## 使用方法

### 方式一：命令行交互模式

通过命令行参数直接执行操作。

**1. 导入文献**
指定文件路径和主题名称：
```bash
python myliterature.py import -c "人工智能" "paper.txt"
```

**2. 搜索文献**
指定主题和问题进行检索：
```bash
python myliterature.py search -c "人工智能" "有哪些关于神经网络的研究？"
```

**3. 查看主题**
列出所有主题及文献数量：
```bash
python myliterature.py list
```

### 方式二：函数调用方式

在其他Python脚本中引入并调用核心函数：

```python
from myliterature import import_literature, search_literature, list_collections

# 1. 导入文献到指定主题
import_literature("path/to/paper.txt", "机器学习")

# 2. 在指定主题下检索文献
result = search_literature("有哪些关于神经网络的研究？", "机器学习")
print(result.answer)

# 3. 查看所有主题
print(list_collections())
```

## 数据库结构

系统自动创建 `literature.db` 数据库，包含两个表：

**collections 表（主题）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 主题名称（唯一） |

**literature 表（文献）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| collection_id | INTEGER | 关联主题ID |
| year | INTEGER | 年份 |
| journal | TEXT | 期刊 |
| title | TEXT | 题目 |
| authors | TEXT | 作者 |
| summary | TEXT | 主要内容总结 |
| file_path | TEXT | 文件绝对路径（唯一） |

## 示例代码（API调用参考）

本项目基于以下API模式进行结构化数据提取：

```python
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("CHATECNU_API_KEY")

class PaperInfo(BaseModel):
    year: str
    journal: str
    title: str
    authors: str
    summary: str

client = OpenAI(api_key=api_key, base_url="https://chat.ecnu.edu.cn/open/api/v1")

completion = client.chat.completions.parse(
    model="ecnu-turbo",
    messages=[
        {"role": "system", "content": "提取文献信息..."},
        {"role": "user", "content": "文献文本..."}
    ],
    response_format=PaperInfo,
)

print(completion.choices[0].message.content)
```
