"""
批量将 PDF 文件转换为 TXT 文件

使用方法:
    python pdf_to_txt.py <pdf 文件夹路径> [输出 txt 文件夹路径]

示例:
    python pdf_to_txt.py ./pdfs ./txts
    python pdf_to_txt.py ./pdfs  # TXT 输出到当前目录下的 output 文件夹
"""

import argparse
import os
from pathlib import Path

import pymupdf


def convert_pdf_to_txt(pdf_path: Path, txt_path: Path) -> None:
    """将单个 PDF 文件转换为 TXT 文件"""
    doc = pymupdf.open(pdf_path)
    text = []

    for page in doc:
        page_text = page.get_text()
        if page_text.strip():
            text.append(page_text)

    doc.close()

    # 写入 TXT 文件
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(text))


def batch_convert(pdf_folder: Path, output_folder: Path) -> None:
    """批量转换文件夹中的所有 PDF 文件"""
    # 确保输出目录存在
    output_folder.mkdir(parents=True, exist_ok=True)

    # 获取所有 PDF 文件（不递归子目录）
    pdf_files = list(pdf_folder.glob('*.pdf')) + list(pdf_folder.glob('*.PDF'))

    if not pdf_files:
        print(f"在 '{pdf_folder}' 中未找到 PDF 文件")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件")

    success_count = 0
    fail_count = 0

    for pdf_file in pdf_files:
        # 生成对应的 TXT 文件名
        txt_name = pdf_file.stem + '.txt'
        txt_path = output_folder / txt_name

        try:
            print(f"转换：{pdf_file.name} -> {txt_name}")
            convert_pdf_to_txt(pdf_file, txt_path)
            success_count += 1
        except Exception as e:
            print(f"错误 - 无法转换 {pdf_file.name}: {e}")
            fail_count += 1

    print(f"\n转换完成！成功：{success_count}, 失败：{fail_count}")


def main():
    parser = argparse.ArgumentParser(
        description='批量将 PDF 文件转换为 TXT 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python pdf_to_txt.py ./pdfs               # 输出到当前目录的 output 文件夹
    python pdf_to_txt.py ./pdfs ./output      # 指定输出目录
        """
    )

    parser.add_argument(
        'pdf_folder',
        type=str,
        help='包含 PDF 文件的输入文件夹路径'
    )

    parser.add_argument(
        'output_folder',
        type=str,
        nargs='?',
        default='output',
        help='输出 TXT 文件的文件夹路径（默认为当前目录下的 output）'
    )

    args = parser.parse_args()

    # 解析路径（支持波浪号展开）
    pdf_folder = Path(args.pdf_folder).expanduser()
    output_folder = Path(args.output_folder).expanduser()

    if not pdf_folder.is_dir():
        print(f"错误：输入文件夹不存在或不是目录：{pdf_folder}")
        return 1

    print(f"输入文件夹：{pdf_folder.absolute()}")
    print(f"输出文件夹：{output_folder.absolute()}")
    print("-" * 42)

    batch_convert(pdf_folder, output_folder)

    return 0


if __name__ == '__main__':
    exit(main())
