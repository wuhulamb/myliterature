# 文件名：myliterature.py
# 功能：文献管理核心模块

import os
import sqlite3
import argparse
import hashlib
from typing import List, Optional, Tuple
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import pymupdf

# ============ 配置 ============
load_dotenv()
api_key = os.getenv("CHATECNU_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://chat.ecnu.edu.cn/open/api/v1")
DB_PATH = "literatures.db"


# ============ 数据模型 ============
class PaperInfo(BaseModel):
    """文献信息结构"""
    year: int
    journal: str
    title: str
    authors: str
    summary: str


class SearchResult(BaseModel):
    """检索结果结构"""
    relevant_ids: List[int]
    answer: str


# ============ 工具函数 ============
def calculate_text_hash(text: str) -> str:
    """计算文本内容的SHA-256 Hash值"""
    clean_text = text.strip()
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()


# ============ 数据库操作 ============
def init_db(db_path=DB_PATH):
    """初始化数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建主题表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # 创建文献表（关联主题）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS literatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER,
            year INTEGER,
            journal TEXT,
            title TEXT,
            authors TEXT,
            summary TEXT,
            file_path TEXT,
            content_hash TEXT UNIQUE,
            FOREIGN KEY(collection_id) REFERENCES collections(id)
        )
    """)

    conn.commit()
    conn.close()


def get_or_create_collection(name: str, db_path=DB_PATH) -> int:
    """获取或创建主题，返回ID"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查找现有主题
    cursor.execute("SELECT id FROM collections WHERE name = ?", (name,))
    result = cursor.fetchone()

    if result:
        coll_id = result[0]
    else:
        # 创建新主题
        cursor.execute("INSERT INTO collections (name) VALUES (?)", (name,))
        conn.commit()
        coll_id = cursor.lastrowid
        print(f"✓ 创建新主题: {name}")

    conn.close()
    return coll_id


def check_hash_exists(content_hash: str, db_path=DB_PATH) -> Optional[Tuple[int, str]]:
    """
    检查Hash是否存在于数据库中
    :return: 如果存在，返回 (collection_id, collection_name)；否则返回 None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.collection_id, c.name
        FROM literatures l
        JOIN collections c ON l.collection_id = c.id
        WHERE l.content_hash = ?
    """, (content_hash,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return (result[0], result[1])
    return None


def save_to_db(info: PaperInfo, file_path: str, collection_name: str, content_hash: str, db_path=DB_PATH):
    """保存文献信息到指定主题"""
    abs_path = os.path.abspath(file_path)
    coll_id = get_or_create_collection(collection_name)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO literatures (collection_id, year, journal, title, authors, summary, file_path, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (coll_id, info.year, info.journal, info.title, info.authors, info.summary, abs_path, content_hash))
        conn.commit()
        print(f"✓ 已保存到 [{collection_name}]: {info.title}")
    except sqlite3.IntegrityError:
        print(f"✗ 存入失败：文献hash相同")
    finally:
        conn.close()


def get_all_literatures(db_path=DB_PATH):
    """获取所有文献"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT l.id, l.year, l.journal, l.title, l.authors, l.summary, c.name, l.file_path
        FROM literatures l
        JOIN collections c ON l.collection_id = c.id
        ORDER BY c.name, l.id
    """)
    results = cursor.fetchall()
    conn.close()
    return results


def get_literatures_by_collection(collection_name: str, db_path=DB_PATH):
    """获取指定主题下的所有文献"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT l.id, l.year, l.journal, l.title, l.authors, l.summary, c.name, l.file_path
        FROM literatures l
        JOIN collections c ON l.collection_id = c.id
        WHERE c.name = ?
    """, (collection_name,))
    results = cursor.fetchall()
    conn.close()
    return results


# ============ LLM处理 ============
def extract_info_by_llm(text: str) -> PaperInfo:
    """调用LLM提取文献信息"""
    system_prompt = """你是一个学术文献信息提取助手。请从给定的文献文本中提取以下字段：
1. year: 发表年份
2. journal: 发表期刊名称
3. title: 文献标题
4. authors: 作者名单（多人用逗号分隔）
5. summary: 主要内容总结

如果某字段无法从文本中确定，填写"未知"。"""

    completion = client.chat.completions.parse(
        model="ecnu-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"文献内容：\n\n{text}"}
        ],
        response_format=PaperInfo,
    )
    return PaperInfo.model_validate_json(completion.choices[0].message.content)


def search_by_llm(question: str, collection_name: str) -> SearchResult:
    """调用LLM在指定主题下进行语义检索"""
    # 获取该主题下的所有文献
    papers = get_literatures_by_collection(collection_name)

    if not papers:
        print(f"主题 [{collection_name}] 下没有文献。")
        return SearchResult(relevant_ids=[], answer="该主题下没有文献。")

    # 构建文献库上下文字符串
    context = f"【主题: {collection_name}】下的文献库内容：\n\n"
    for p in papers:
        context += f"ID: {p[0]}\n"
        context += f"年份: {p[1]}\n"
        context += f"期刊: {p[2]}\n"
        context += f"题目: {p[3]}\n"
        context += f"作者: {p[4]}\n"
        context += f"主要内容: {p[5]}\n"
        context += "-" * 40 + "\n"

    # 调用LLM检索
    system_prompt = """你是一个文献检索助手。根据用户问题，从提供的文献库中找出最相关的文献。
请返回：
1. relevant_ids: 相关文献的ID列表（按相关度排序）
2. answer: 对用户问题的回答（基于文献内容）"""

    completion = client.chat.completions.parse(
        model="ecnu-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\n用户问题：{question}"}
        ],
        response_format=SearchResult,
    )
    return SearchResult.model_validate_json(completion.choices[0].message.content)


# ============ 核心功能函数 ============
def import_single_file(file_path: str, collection_name: str):
    """
    导入单篇PDF文献到指定主题
    :param file_path: PDF文件路径
    :param collection_name: 主题名称
    """
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return

    # 读取PDF文本
    try:
        doc = pymupdf.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        text = text.strip()
        doc.close()
    except Exception as e:
        print(f"✗ 读取PDF失败: {file_path} (错误: {e})")
        return

    if not text:
        print(f"文件内容为空: {file_path}")
        return

    # 计算Hash
    content_hash = calculate_text_hash(text)

    # 在调用LLM前预检Hash
    existing_info = check_hash_exists(content_hash)
    if existing_info:
        _, existing_coll_name = existing_info
        print(f"✗ 跳过处理：文献内容已存在")
        print(f"  已存在于主题 [{existing_coll_name}]")
        return

    print(f"正在解析: {file_path} ...")
    info = extract_info_by_llm(text)
    save_to_db(info, file_path, collection_name, content_hash)


def import_directory(dir_path: str, collection_name: str):
    """
    导入目录下所有PDF文件到指定主题
    :param dir_path: 目录路径
    :param collection_name: 主题名称
    """
    if not os.path.exists(dir_path):
        print(f"目录不存在: {dir_path}")
        return

    if not os.path.isdir(dir_path):
        print(f"不是目录: {dir_path}")
        return

    # 获取目录下所有pdf文件（不包含子目录）
    files = [f for f in os.listdir(dir_path)
             if os.path.isfile(os.path.join(dir_path, f)) and f.lower().endswith('.pdf')]

    if not files:
        print(f"目录中没有PDF文件: {dir_path}")
        return

    print(f"开始导入目录: {dir_path} (共 {len(files)} 个PDF文件)")

    for i, filename in enumerate(files, 1):
        file_path = os.path.join(dir_path, filename)
        print(f"\n[{i}/{len(files)}] 处理: {filename}")
        import_single_file(file_path, collection_name)


def search_literature(question: str, collection_name: str):
    """
    在指定主题下搜索文献
    :param question: 自然语言问题
    :param collection_name: 主题名称
    :return: 检索结果
    """
    result = search_by_llm(question, collection_name)

    # 获取匹配文献的详细信息
    papers_dict = {p[0]: p for p in get_literatures_by_collection(collection_name)}

    print(f"\n回答: {result.answer}")
    print(f"\n相关文献 ({len(result.relevant_ids)} 篇):")

    for pid in result.relevant_ids:
        if pid in papers_dict:
            print_paper_info(papers_dict[pid])

    return result


# ============ 打印函数 ============
def print_paper_info(paper: tuple, indent: str = "  "):
    """
    统一打印单条文献信息
    :param paper: 文献数据元组 (id, year, journal, title, authors, summary, collection_name, file_path)
    :param indent: 缩进字符，默认两个空格
    """
    pid, year, journal, title, authors, _, _, file_path = paper

    print(f"{indent}[ID:{pid}] {title}")
    print(f"{indent}    {year} | {journal} | {authors}")
    print(f"{indent}    路径: {file_path}")


# ============ 命令行接口 ============
def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="文献管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # import 命令
    p_import = subparsers.add_parser("import", help="导入文献")
    p_import.add_argument("-c", "--collection", required=True, help="主题名称")

    # 互斥参数：要么导入单个文件，要么导入目录
    import_group = p_import.add_mutually_exclusive_group(required=True)
    import_group.add_argument("-f", "--file", help="导入单个文件")
    import_group.add_argument("-d", "--dir", help="导入目录下所有文件")

    # search 命令
    p_search = subparsers.add_parser("search", help="搜索文献")
    p_search.add_argument("-c", "--collection", required=True, help="主题名称")
    p_search.add_argument("-q", "--query", required=True, help="查询内容")

    # list 命令
    p_list = subparsers.add_parser("list", help="列出文献")
    p_list.add_argument("-c", "--collection", help="指定主题名称（可选）")

    args = parser.parse_args()

    # 初始化数据库
    init_db()

    # 分发命令
    if args.command == "import":
        if args.file:
            # 导入单个文件
            import_single_file(args.file, args.collection)
        elif args.dir:
            # 导入目录
            import_directory(args.dir, args.collection)
    elif args.command == "search":
        search_literature(args.query, args.collection)
    elif args.command == "list":
        if args.collection:
            # 列出指定主题的文献
            papers = get_literatures_by_collection(args.collection)
            if not papers:
                print(f"[{args.collection}] 下没有文献。")
            else:
                print(f"[{args.collection}] (共{len(papers)}篇)")
                for p in papers:
                    print_paper_info(p)
        else:
            # 列出所有文献
            papers = get_all_literatures()
            if not papers:
                print("数据库中没有文献。")
            else:
                # 统计每个主题的文献数量
                from collections import Counter
                # p[6] 是 collection_name
                counts = Counter(p[6] for p in papers)

                print("所有文献列表:")
                current_coll = None
                for p in papers:
                    # p 结构: (id, year, journal, title, authors, summary, collection_name, file_path)
                    coll_name = p[6]
                    # 按主题分组显示
                    if coll_name != current_coll:
                        current_coll = coll_name
                        print(f"\n[{coll_name}] (共{counts[coll_name]}篇)")
                    print_paper_info(p)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
