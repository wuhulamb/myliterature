# 文件名：rename_with_ai.py
# 功能：使用AI提取论文信息并重命名PDF文件
# 使用说明：
# 1. 输入：脚本会扫描指定目录中的PDF文件
# 2. 输出：将PDF重命名为"发表时间__期刊__标题__作者.pdf"格式
# 3. 配置：可在脚本顶部修改SEPARATOR变量调整分隔符，支持"-", " ", ".", "__"等

import os
import re
import argparse
from datetime import datetime
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pymupdf

# 加载环境变量
load_dotenv()

# 配置：可以在这里修改分隔符
SEPARATOR = "__"  # 可以改为 "-", " ", ".", "__" 等
MAX_FILENAME_LENGTH = 255  # 大多数系统的文件名长度限制

class PaperInfo(BaseModel):
    """论文信息数据模型"""
    year: int = Field(description="论文发表年份，格式为YYYY")
    journal: str = Field(description="论文发表的期刊名称")
    title: str = Field(description="论文的完整标题")
    author: str = Field(description="论文的主要作者姓名")

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """从PDF文件中提取文本内容"""
    try:
        # 打开PDF文件
        doc = pymupdf.open(pdf_path)
        text = ""

        # 逐页提取文本
        for page in doc:
            text += page.get_text()

        doc.close()

        if not text.strip():
            print(f"警告：PDF文件内容为空或无法提取文本: {os.path.basename(pdf_path)}")
            return None

        print(f"成功提取PDF文本，大小: {len(text)} 字符")
        return text

    except Exception as e:
        print(f"错误：读取PDF文件失败 {os.path.basename(pdf_path)}: {e}")
        return None

def extract_publication_info(file_content: str) -> Optional[PaperInfo]:
    """从论文内容中提取发表时间、期刊、标题和作者信息"""
    # 从环境变量获取API密钥
    api_key = os.getenv("CHATECNU_API_KEY")
    if not api_key:
        print("错误：未找到环境变量 CHATECNU_API_KEY，请在 .env 文件中设置")
        return None

    client = OpenAI(
        api_key=api_key,
        base_url="https://chat.ecnu.edu.cn/open/api/v1",
    )

    system_prompt = (
        "你是一个专业的学术助手。请仔细阅读论文内容，准确提取以下信息：\n"
        "1. 发表时间：论文发表的年份（格式：YYYY）\n"
        "2. 发表期刊：论文发表的期刊名称\n"
        "3. 论文标题：论文的完整标题\n"
        "4. 论文作者：论文的主要作者姓名\n\n"
        "请确保信息准确，不要添加任何额外说明。"
    )

    user_prompt = f"请提取以下论文的信息：\n\n{file_content}"

    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            print("正在调用AI API提取论文信息...")

            completion = client.chat.completions.parse(
                model="ecnu-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=PaperInfo,
            )

            paper_info = completion.choices[0].message.parsed
            print("成功提取论文信息")
            return paper_info

        except Exception as e:
            print(f"错误：提取信息时发生错误: {e}")
            retry_count += 1
            continue

    print(f"错误：提取论文信息失败，已达到最大重试次数 {max_retries}")
    return None

def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    cleaned = re.sub(r'[\\/*?:"<>|\']', "", name)
    if cleaned != name:
        print(f"清理文件名: '{name}' -> '{cleaned}'")
    return cleaned

def truncate_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """如果文件名太长，直接硬截断

    保留文件扩展名完整
    """
    if len(filename) <= max_length:
        return filename

    print(f"警告：文件名过长 ({len(filename)} 字符)，进行截断: {filename}")

    # 分离文件名和扩展名
    name_without_ext, ext = os.path.splitext(filename)

    # 直接硬截断，保留扩展名
    truncated = name_without_ext[:max_length - len(ext)] + ext
    print(f"截断后的文件名: {truncated}")
    return truncated

def safe_rename(old_path: str, new_name: str) -> bool:
    """安全重命名文件，处理文件名过长问题"""
    try:
        # 检查新文件名长度
        if len(new_name) > MAX_FILENAME_LENGTH:
            new_name = truncate_filename(new_name)

        # 构建完整路径
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)

        # 执行重命名
        os.rename(old_path, new_path)
        print(f"文件重命名成功: {os.path.basename(old_path)} -> {new_name}")
        return True

    except OSError as e:
        print(f"错误：重命名文件失败 {os.path.basename(old_path)}: {e}")
        return False
    except Exception as e:
        print(f"错误：重命名文件失败 {os.path.basename(old_path)}: {e}")
        return False

def is_already_renamed(filename: str) -> bool:
    """检查文件是否已经重命名过"""
    pattern = r'^\d{4}' + re.escape(SEPARATOR) + r'.*' + re.escape(SEPARATOR) + r'.*' + re.escape(SEPARATOR) + r'.*'
    is_renamed = bool(re.match(pattern, filename))
    if is_renamed:
        print(f"文件已处理过: {filename}")
    return is_renamed

def main(target_dir: str):
    """主函数：重命名目录中的所有PDF文件

    Args:
        target_dir: 目标目录路径
    """
    print(f"开始处理目录: {target_dir}")
    print(f"分隔符配置: '{SEPARATOR}'")
    print(f"最大文件名长度: {MAX_FILENAME_LENGTH} 字符")

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    for filename in os.listdir(target_dir):
        if not filename.lower().endswith('.pdf'):
            continue

        if is_already_renamed(filename):
            print(f"跳过已处理文件: {filename}")
            skipped_count += 1
            continue

        filepath = os.path.join(target_dir, filename)
        print(f"开始处理PDF文件: {filename}")

        try:
            # 从PDF提取文本
            content = extract_text_from_pdf(filepath)

            if content is None:
                print(f"错误：无法提取PDF文本内容: {filename}")
                failed_count += 1
                continue

            # 调用AI提取论文信息
            paper_info = extract_publication_info(content)

            if paper_info is None:
                print(f"错误：无法提取论文信息: {filename}")
                failed_count += 1
                continue

            date = paper_info.year
            journal = sanitize_filename(paper_info.journal)
            title = sanitize_filename(paper_info.title)
            author = sanitize_filename(paper_info.author)

            # 构建新文件名
            new_pdf_name = f"{date}{SEPARATOR}{journal}{SEPARATOR}{title}{SEPARATOR}{author}.pdf"

            # 重命名PDF文件
            if safe_rename(filepath, new_pdf_name):
                processed_count += 1
            else:
                print(f"错误：重命名PDF文件失败: {filename}")
                failed_count += 1

        except FileNotFoundError:
            print(f"错误：文件不存在: {filename}")
            failed_count += 1
        except PermissionError:
            print(f"错误：权限不足无法读取文件: {filename}")
            failed_count += 1
        except Exception as e:
            print(f"错误：处理文件 {filename} 时发生未知错误: {e}")
            failed_count += 1

    # 输出统计信息
    print("=" * 50)
    print(f"处理完成！统计结果:")
    print(f"  处理成功: {processed_count} 个文件")
    print(f"  跳过已处理: {skipped_count} 个文件")
    print(f"  处理失败: {failed_count} 个文件")
    print(f"  总计文件: {processed_count + skipped_count + failed_count} 个")
    print("=" * 50)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="使用AI重命名文献PDF文件",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-d", "--dir",
        type=str,
        required=True,
        help="文献目录路径"
    )

    return parser.parse_args()

if __name__ == "__main__":
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 运行主函数
        main(args.dir)
    except KeyboardInterrupt:
        print("用户中断程序执行")
    except Exception as e:
        print(f"程序发生严重错误: {e}")
