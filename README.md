# 文献管理系统

> 我的文献我做主！

## 🌟 Why you need it

1. 下载下来的文献命名混乱
2. 不同阶段研究主题不同，看的文献类型也不同，这些文献东一处西一处，想要找到之前读过的某篇文献却总是找不到
3. 现在已经是AI时代了，天生注意力惊人的AI比我们更适合管理文献

## 🚀 Quickstart

### 安装必要的依赖库

```bash
pip install openai pydantic python-dotenv pymupdf
```

### 在项目根目录创建 `.env` 文件，配置API密钥

```
CHATECNU_API_KEY=your_api_key_here
```

### 文件结构

存放原始文献的目录（`literatures/`）可以放在任意位置，为方便管理，建议放在项目目录下

```text
.
├── .env                  # 环境变量配置 (API Key)
├── literatures.db        # SQLite数据库
├── myliterature.py       # 核心模块：导入、管理、检索文献
├── rename_with_ai.py     # 辅助工具：批量重命名 PDF 文件
├── README.md             # 项目说明文档
└── literatures/          # 原始文献目录
    ├── collection1/      # 主题1的原始PDF
    │   ├── paper_a.pdf
    │   └── paper_b.pdf
    ├── collection2/      # 主题2的原始PDF
    │   ├── paper_c.pdf
    │   └── ...
    └── collection3/      # 主题3的原始PDF
        └── ...
```

### 使用示例

假设你的文件结构为：`literatures/collection1/` (存放深度学习论文) 和 `literatures/collection2/` (存放强化学习论文)

#### 1 智能重命名

批量整理子文件夹内的 PDF 文件名
```bash
python rename_with_ai.py -d ./literatures/collection1
python rename_with_ai.py -d ./literatures/collection2
```

> 💡 **提示**：重复运行命令会自动跳过已存在的文献，支持增量更新

#### 2 导入数据库

将文件夹内容导入系统，并指定主题名（`-c`）
```bash
# 将 collection1 导入为 "Deep_Learning" 主题
python myliterature.py import -c Deep_Learning -d ./literatures/collection1

# 将 collection2 导入为 "RL" 主题
python myliterature.py import -c RL -d ./literatures/collection2
```

> 💡 **提示**：重复运行命令会自动跳过已存在的文献，支持增量更新

#### 3 查看与检索

列出文献或直接向 AI 提问
```bash
# 查看 "Deep_Learning" 主题下的文献列表
python myliterature.py list -c Deep_Learning

# 向 "Deep_Learning" 主题提问
python myliterature.py search -c Deep_Learning "残差网络的核心创新是什么？"
```

## 🗄️ 数据库结构

系统自动创建 `literatures.db` 数据库，包含两个表：

**collections 表（主题）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 主题名称（唯一） |

**literatures 表（文献）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| collection_id | INTEGER | 关联主题ID |
| year | INTEGER | 年份 |
| journal | TEXT | 期刊 |
| title | TEXT | 题目 |
| authors | TEXT | 作者 |
| summary | TEXT | 主要内容总结 |
| file_path | TEXT | 文件绝对路径 |
| content_hash | TEXT | 文件内容的 SHA-256 哈希值（唯一） |
