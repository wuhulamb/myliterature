import argparse
import hashlib
import time
from pathlib import Path

import pymupdf


def get_pdf_text(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def find_duplicate_pdfs(directory: str):
    """Find duplicate PDF files in the given directory by content hash."""
    pdf_dir = Path(directory)

    content_map: dict[str, list[Path]] = {}
    empty_pdfs: list[Path] = []

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            text = get_pdf_text(str(pdf_file))
            if not text.strip():
                empty_pdfs.append(pdf_file)
                continue
            file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            content_map.setdefault(file_hash, []).append(pdf_file)
        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_file.name}: {e}")

    # Report results
    total = len(empty_pdfs) + sum(len(files) for files in content_map.values())
    unique = sum(1 for files in content_map.values() if len(files) == 1)
    duplicates = {h: files for h, files in content_map.items() if len(files) > 1}

    print(f"Total PDF files:           {total}")
    print(f"Unique files:              {unique}")
    print(f"Duplicate sets:            {len(duplicates)}")
    print(f"Empty (no text content):   {len(empty_pdfs)}")
    print()

    if empty_pdfs:
        print("=" * 60)
        print("EMPTY PDF FILES (no extractable text)")
        print("=" * 60)
        for f in empty_pdfs:
            mtime = f.stat().st_mtime
            print(f"  - {f.name}  (mtime: {time.ctime(mtime)})")
        print()

    if duplicates:
        print("=" * 60)
        print("DUPLICATE FILES")
        print("=" * 60)
        for i, (h, files) in enumerate(duplicates.items(), 1):
            # Sort by modification time (ascending) so the earliest is first
            files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)
            print(f"\nDuplicate set #{i} (hash: {h[:16]}...):")
            for f in files_sorted:
                mtime = f.stat().st_mtime
                print(f"  - {f.name}  (mtime: {time.ctime(mtime)})")
    else:
        print("No duplicate PDF files found.")


def remove_duplicates(directory: str):
    """Remove duplicate PDFs, keeping the earliest file in each duplicate group.
    Empty PDFs (no extractable text) are never deleted; they are reported separately.
    """
    pdf_dir = Path(directory)
    content_map: dict[str, list[Path]] = {}
    empty_pdfs: list[Path] = []

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            text = get_pdf_text(str(pdf_file))
            if not text.strip():
                empty_pdfs.append(pdf_file)
                continue
            file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            content_map.setdefault(file_hash, []).append(pdf_file)
        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_file.name}: {e}")

    # Report empty PDFs (not deleted)
    if empty_pdfs:
        print(f"Empty PDFs (no extractable text, skipped): {len(empty_pdfs)}")
        for f in empty_pdfs:
            print(f"  - {f.name}")
        print()

    duplicates = {h: files for h, files in content_map.items() if len(files) > 1}
    total_removed = 0

    for h, files in duplicates.items():
        files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)
        keep = files_sorted[0]
        to_remove = files_sorted[1:]

        print(f"Hash {h[:16]}... — keeping {keep.name}")
        for f in to_remove:
            f.unlink()
            print(f"  [deleted] {f.name}")
            total_removed += 1

    if total_removed == 0:
        print("No duplicate files to remove.")
    else:
        print(f"\nTotal removed: {total_removed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find duplicate PDF files by content hash.")
    parser.add_argument("-d", "--dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--keep", action="store_true",
                        help="Remove duplicate PDFs, keeping only the earliest file in each group")
    args = parser.parse_args()

    if args.keep:
        remove_duplicates(args.dir)
    else:
        find_duplicate_pdfs(args.dir)