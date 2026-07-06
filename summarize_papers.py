# 文件名：summarize_papers.py
# 功能：使用AI提取论文信息并生成Markdown格式的分析报告
# 使用说明：
# 1. 输入：脚本会扫描指定目录中的txt文件（每篇论文一个txt）
# 2. 输出：为每个txt生成对应的Markdown总结文件到输出目录

import os
import json
import argparse
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class PaperSummary(BaseModel):
    """论文分析报告数据模型"""
    title: str = Field(description="论文标题")
    authors: str = Field(description="所有作者，用逗号分隔")
    affiliations: str = Field(description="作者所属机构")
    journal: str = Field(description="发表期刊或会议名称")
    year: int = Field(description="发表年份，格式为YYYY")
    # 以下7个详细字段——论文结构清晰时填写，否则留空
    research_topic: Optional[str] = Field(default=None, description="核心研究问题或目标")
    theoretical_basis: Optional[str] = Field(default=None, description="理论基础和文献依据")
    methods_data: Optional[str] = Field(default=None, description="研究方法与数据来源")
    mechanism_analysis: Optional[str] = Field(default=None, description="机制分析：核心变量间的因果关系或作用路径")
    core_conclusions: Optional[str] = Field(default=None, description="主要发现和最终论点")
    innovation_contribution: Optional[str] = Field(default=None, description="创新点与领域贡献")
    limitations_outlook: Optional[str] = Field(default=None, description="研究局限性与未来研究建议")
    # 当无法按详细结构分析时，填入此字段
    main_content: Optional[str] = Field(default=None, description="主要内容总结（当详细字段留空时使用）")


def read_text_file(txt_path: str) -> Optional[str]:
    """读取文本文件内容"""
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            print(f"警告：文件内容为空: {os.path.basename(txt_path)}")
            return None
        print(f"成功读取文件，大小: {len(content)} 字符")
        return content
    except Exception as e:
        print(f"错误：读取文件失败 {os.path.basename(txt_path)}: {e}")
        return None


def generate_summary(file_content: str) -> Optional[PaperSummary]:
    """使用AI提取论文信息并生成分析报告"""
    api_key = os.getenv("CHATECNU_API_KEY")
    if not api_key:
        print("错误：未找到环境变量 CHATECNU_API_KEY，请在 .env 文件中设置")
        return None

    client = OpenAI(
        api_key=api_key,
        base_url="https://chat.ecnu.edu.cn/open/api/v1",
    )

    system_prompt = (
        "你是一个专业的学术分析助手。请严格按以下JSON格式输出，不要添加任何列表、序号、注释、说明或额外文本。\n"
        "每个字段的文本都应完整、准确，保留原文关键信息。\n"
        "{\n"
        '  "title": "论文标题",\n'
        '  "authors": "作者1, 作者2, 作者3",\n'
        '  "affiliations": "作者所属机构",\n'
        '  "journal": "期刊或会议名称",\n'
        '  "year": 2024,\n'
        '  "research_topic": "核心研究问题或目标",\n'
        '  "theoretical_basis": "理论基础和文献依据",\n'
        '  "methods_data": "研究方法与数据来源、类型",\n'
        '  "mechanism_analysis": "机制分析：核心变量间的因果关系或作用路径",\n'
        '  "core_conclusions": "主要发现和最终论点",\n'
        '  "innovation_contribution": "创新点与领域贡献",\n'
        '  "limitations_outlook": "研究局限性与未来研究建议",\n'
        '  "main_content": ""\n'
        "}\n"
        "说明：如果论文内容清晰可辨，请按详细字段（research_topic / theoretical_basis / methods_data / "
        "mechanism_analysis / core_conclusions / innovation_contribution / limitations_outlook）填写7个方面；"
        "如果无法按上述结构分析（如论文缺少明确的方法、机制等章节），则将主要内容填入main_content字段，"
        "详细字段留空（null）。\n"
        "仅输出合法JSON。每个字段使用中文回答。"
    )

    user_prompt = f"请分析以下学术文献，提取信息并生成分析报告：\n\n{file_content}"

    retry_count = 0
    max_retries = 3

    json_schema = json.dumps(PaperSummary.model_json_schema())

    while retry_count < max_retries:
        try:
            print("正在调用AI API生成文献分析报告...")

            response = client.chat.completions.create(
                model="ecnu-plus",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "paper_summary", "schema": json.loads(json_schema)},
                },
            )

            parsed = json.loads(response.choices[0].message.content)
            summary = PaperSummary(**parsed)
            print("成功生成文献分析报告")
            return summary

        except Exception as e:
            print(f"错误：生成分析报告时发生错误: {e}")
            retry_count += 1
            continue

    print(f"错误：生成文献分析报告失败，已达到最大重试次数 {max_retries}")
    return None


def generate_markdown(summary: PaperSummary, source_filename: str, source_abspath: str) -> str:
    """根据PaperSummary生成Markdown格式的分析报告"""
    md = f"""# 文献分析报告

---

## 第一部分：文献基本信息

| 项目 | 内容 |
|------|------|
| **论文标题** | {summary.title} |
| **所有作者** | {summary.authors} |
| **作者所属机构** | {summary.affiliations} |
| **发表期刊/会议** | {summary.journal} |
| **发表年份** | {summary.year} |

---
"""

    # 第二部分：根据是否能够按详细结构分析，展示不同内容
    if summary.main_content:
        # 无法按详细结构分析，只展示主要内容
        md += f"""## 第二部分：内容提炼与分析

### 主要内容

{summary.main_content}

"""
    else:
        # 按详细结构展示
        md += f"""## 第二部分：内容提炼与分析

### 1. 研究主题

{summary.research_topic}

### 2. 理论基础

{summary.theoretical_basis}

### 3. 方法与数据

{summary.methods_data}

### 4. 机制分析

{summary.mechanism_analysis}

### 5. 核心结论

{summary.core_conclusions}

### 6. 创新与贡献

{summary.innovation_contribution}

### 7. 局限与展望

{summary.limitations_outlook}

"""

    md += f"""---
原始文献路径：{source_abspath}
"""
    return md


def main(input_dir: str, output_dir: str):
    """主函数：处理目录中的所有txt文件并生成Markdown总结

    Args:
        input_dir: txt文件所在目录
        output_dir: 输出Markdown文件的目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    for filename in sorted(os.listdir(input_dir)):
        if not filename.lower().endswith('.txt'):
            continue

        # 检查是否已存在对应的md文件
        md_filename = os.path.splitext(filename)[0] + ".md"
        md_path = os.path.join(output_dir, md_filename)
        if os.path.exists(md_path):
            print(f"跳过已处理文件: {filename}（对应的Markdown文件已存在）")
            skipped_count += 1
            continue

        filepath = os.path.join(input_dir, filename)
        print(f"\n开始处理文件: {filename}")

        try:
            # 读取文本内容
            content = read_text_file(filepath)
            if content is None:
                print(f"错误：无法读取文件内容: {filename}")
                failed_count += 1
                continue

            # 调用AI生成分析报告
            summary = generate_summary(content)
            if summary is None:
                print(f"错误：无法生成文献分析报告: {filename}")
                failed_count += 1
                continue

            # 生成Markdown内容
            abspath = os.path.abspath(filepath)
            markdown_content = generate_markdown(summary, filename, abspath)

            # 写入Markdown文件
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            print(f"Markdown文件已保存: {md_path}")
            processed_count += 1

        except Exception as e:
            print(f"错误：处理文件 {filename} 时发生未知错误: {e}")
            failed_count += 1

    # 输出统计信息
    print("\n" + "=" * 50)
    print("处理完成！统计结果:")
    print(f"  处理成功: {processed_count} 个文件")
    print(f"  跳过已处理: {skipped_count} 个文件")
    print(f"  处理失败: {failed_count} 个文件")
    print(f"  总计文件: {processed_count + skipped_count + failed_count} 个")
    print("=" * 50)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="使用AI生成文献的分析报告（Markdown格式）",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="包含文献txt文件的目录路径"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="输出Markdown文件的目录路径"
    )

    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = parse_arguments()
        main(args.input, args.output)
    except KeyboardInterrupt:
        print("用户中断程序执行")
    except Exception as e:
        print(f"程序发生严重错误: {e}")
