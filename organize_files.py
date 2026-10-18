#!/usr/bin/env python3
"""
파일 자동 분류 스크립트
--------------------------------------------------
사용법:
  python organize_files.py "폴더경로"                 # 미리보기만 (실제로 옮기지 않음)
  python organize_files.py "폴더경로" --apply         # 실제로 분류해서 이동
  python organize_files.py "폴더경로" --apply --by-date   # 카테고리 안에 연-월 폴더까지 생성
  python organize_files.py "폴더경로" --undo          # 마지막 정리 되돌리기
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── 카테고리 규칙: 필요하면 여기만 고치면 됩니다 ──
CATEGORIES = {
    "01_문서":        [".pdf", ".doc", ".docx", ".hwp", ".hwpx", ".txt", ".md", ".rtf", ".odt"],
    "02_스프레드시트": [".xls", ".xlsx", ".csv", ".tsv", ".numbers"],
    "03_프레젠테이션": [".ppt", ".pptx", ".key"],
    "04_이미지":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tiff", ".psd", ".ai"],
    "05_동영상":      [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"],
    "06_오디오":      [".mp3", ".wav", ".m4a", ".aac", ".flac"],
    "07_압축파일":    [".zip", ".rar", ".7z", ".tar", ".gz", ".egg", ".alz"],
    "08_코드":        [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json",
                       ".ipynb", ".sh", ".sql", ".yml", ".yaml"],
    "09_설치파일":    [".exe", ".msi", ".dmg", ".pkg", ".apk"],
}
OTHER = "99_기타"
LOG_NAME = ".organize_log.json"   # 되돌리기용 기록 파일


def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return OTHER


def unique_dest(dest: Path) -> Path:
    """같은 이름 파일이 이미 있으면 '파일명 (1).확장자' 식으로 피해감"""
    if not dest.exists():
        return dest
    i = 1
    while True:
        candidate = dest.with_name(f"{dest.stem} ({i}){dest.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def collect_files(root: Path):
    """폴더 바로 아래의 파일만 대상 (하위 폴더, 숨김 파일, 이 스크립트는 제외)"""
    me = Path(__file__).resolve()
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith(".") or p.resolve() == me:
            continue
        yield p


def organize(root: Path, apply: bool, by_date: bool):
    files = list(collect_files(root))
    if not files:
        print("정리할 파일이 없습니다.")
        return

    summary, moves = {}, []
    for f in files:
        target_dir = root / category_for(f)
        if by_date:
            month = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m")
            target_dir = target_dir / month

        if apply:
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = unique_dest(target_dir / f.name)
            shutil.move(str(f), str(dest))
            moves.append({"from": str(f), "to": str(dest)})
            print(f"  이동: {f.name}  →  {dest.relative_to(root)}")
        else:
            print(f"  [미리보기] {f.name}  →  {(target_dir / f.name).relative_to(root)}")

        cat = category_for(f)
        summary[cat] = summary.get(cat, 0) + 1

    print("\n── 요약 ──")
    for cat in sorted(summary):
        print(f"  {cat}: {summary[cat]}개")

    if apply:
        log = {"time": datetime.now().isoformat(), "moves": moves}
        (root / LOG_NAME).write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n완료! 되돌리려면 --undo 옵션으로 다시 실행하세요.")
    else:
        print("\n미리보기였습니다. 실제로 옮기려면 --apply 를 붙여 실행하세요.")


def undo(root: Path):
    log_path = root / LOG_NAME
    if not log_path.exists():
        print("되돌릴 기록이 없습니다.")
        return
    log = json.loads(log_path.read_text(encoding="utf-8"))
    for m in reversed(log["moves"]):
        src, original = Path(m["to"]), Path(m["from"])
        if src.exists():
            shutil.move(str(src), str(unique_dest(original)))
            print(f"  복원: {original.name}")

    # 비어버린 카테고리 폴더 정리
    for d in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    log_path.unlink()
    print("\n원래 상태로 되돌렸습니다.")


def main():
    parser = argparse.ArgumentParser(description="폴더 안 파일을 카테고리별로 자동 분류")
    parser.add_argument("folder", help="정리할 폴더 경로")
    parser.add_argument("--apply", action="store_true", help="실제로 파일 이동")
    parser.add_argument("--by-date", action="store_true", help="카테고리 안에 연-월 폴더 생성")
    parser.add_argument("--undo", action="store_true", help="마지막 정리 되돌리기")
    args = parser.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"폴더를 찾을 수 없습니다: {root}")

    if args.undo:
        undo(root)
    else:
        organize(root, args.apply, args.by_date)


if __name__ == "__main__":
    main()
