import argparse
import hashlib
import time
from pathlib import Path

import pymupdf


def compute_pdf_hash(pdf_path: str) -> str:
    """Compute hash of a PDF file based on its text content."""
    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_duplicate_pdfs(directory: str):
    """Find duplicate PDF files in the given directory by content hash."""
    pdf_dir = Path(directory)
    hash_map: dict[str, list[Path]] = {}

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            file_hash = compute_pdf_hash(str(pdf_file))
            hash_map.setdefault(file_hash, []).append(pdf_file)
        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_file.name}: {e}")

    # Report results
    total = sum(len(files) for files in hash_map.values())
    unique = sum(1 for files in hash_map.values() if len(files) == 1)
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    print(f"Total PDF files: {total}")
    print(f"Unique files:    {unique}")
    print(f"Duplicate sets:  {len(duplicates)}")
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
                mtime = Path(f).stat().st_mtime
                print(f"  - {f.name}  (mtime: {time.ctime(mtime)})")
    else:
        print("No duplicate PDF files found.")


def remove_duplicates(directory: str):
    """Remove duplicate PDFs, keeping the earliest file in each duplicate group."""
    pdf_dir = Path(directory)
    hash_map: dict[str, list[Path]] = {}

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            file_hash = compute_pdf_hash(str(pdf_file))
            hash_map.setdefault(file_hash, []).append(pdf_file)
        except Exception as e:
            print(f"[ERROR] Failed to process {pdf_file.name}: {e}")

    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    total_removed = 0

    for h, files in duplicates.items():
        files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)
        keep = files_sorted[0]
        to_remove = files_sorted[1:]

        print(f"\nHash {h[:16]}... — keeping {keep.name}")
        for f in to_remove:
            f.unlink()
            print(f"  [deleted] {f.name}")
            total_removed += 1

    if total_removed == 0:
        print("\nNo duplicate files to remove.")
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