#!/usr/bin/env python3
"""
NovelWorkshop v3 → v4 数据迁移脚本

功能：
1. 读取旧 outline/hooks.json 或 state/hook_ledger.json，将伏笔数据迁移到 outline.json.foreshadowing
2. 遍历 chapters/ 目录，为每个 .md 文件生成对应的 .json 元数据
3. 按章节号匹配 outline.volumes[].chapters[]，写入 outline_chapter_id 关联
4. 迁移完成后删除旧 hooks.json，标记 "migrated_to_v4": true

用法：
    python migrate_v3_to_v4.py <book_dir>
"""
import json
import os
import sys
import time
from pathlib import Path


def read_json(file_path: str) -> dict:
    """安全读取 JSON 文件"""
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def write_json(file_path: str, data: dict):
    """写入 JSON 文件"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_outline_chapter_id(outline_data: dict, chapter_number: int) -> str:
    """从 outline 数据中按章节号查找 chapter id"""
    # 新格式：volumes[].chapters[]
    for vol in outline_data.get("volumes", []):
        for ch in vol.get("chapters", []):
            if ch.get("number") == chapter_number:
                return ch.get("id", "")
    # 旧格式：outline[].children[]
    for node in outline_data.get("outline", []):
        if isinstance(node, dict):
            for child in node.get("children", []):
                if isinstance(child, dict) and child.get("chapter_number") == chapter_number:
                    return child.get("id", "")
    # 更旧格式：chapters[]
    for ch in outline_data.get("chapters", []):
        if isinstance(ch, dict):
            if ch.get("number", ch.get("chapter_number")) == chapter_number:
                return ch.get("id", "")
    return ""


def extract_chapter_number(filename: str) -> int:
    """从文件名提取章节号，如 chapter-0001.md -> 1"""
    name = Path(filename).stem  # chapter-0001
    try:
        return int(name.replace("chapter-", ""))
    except (ValueError, AttributeError):
        return 0


def extract_title_from_content(content: str, chapter_number: int) -> str:
    """从章节内容提取标题"""
    for line in content.split("\n")[:5]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return f"第{chapter_number}章"


def migrate_hooks(book_dir: Path) -> int:
    """
    迁移伏笔数据到 outline.json.foreshadowing。
    来源1: outline/hooks.json
    来源2: state/hook_ledger.json
    返回迁移的伏笔数量。
    """
    outline_path = book_dir / "outline" / "outline.json"
    outline_data = read_json(str(outline_path))

    migrated_count = 0
    hooks_to_migrate = []

    # 来源1: outline/hooks.json
    hooks_json_path = book_dir / "outline" / "hooks.json"
    if hooks_json_path.exists():
        hooks_data = read_json(str(hooks_json_path))
        raw_hooks = hooks_data.get("hooks", [])
        if isinstance(raw_hooks, list):
            for h in raw_hooks:
                if not isinstance(h, dict):
                    continue
                hooks_to_migrate.append({
                    "id": h.get("id", f"fs-{int(time.time())}-{migrated_count}"),
                    "purpose": h.get("title", h.get("purpose", h.get("description", ""))),
                    "description": h.get("description", h.get("notes", "")),
                    "start_chapter": h.get("start_chapter", h.get("planted_chapter", 0)),
                    "end_chapter": h.get("end_chapter", h.get("target_chapter", 0)),
                    "characters": h.get("characters", []),
                    "status": h.get("status", "planted"),
                })
                migrated_count += 1
        print(f"  [hooks.json] 发现 {len(hooks_to_migrate)} 条伏笔")

    # 来源2: state/hook_ledger.json
    hook_ledger_path = book_dir / "state" / "hook_ledger.json"
    if hook_ledger_path.exists():
        ledger_data = read_json(str(hook_ledger_path))
        raw_hooks = ledger_data.get("hooks", [])
        existing_ids = {h["id"] for h in hooks_to_migrate if "id" in h}
        for h in raw_hooks:
            if not isinstance(h, dict):
                continue
            h_id = h.get("id", "")
            # 避免重复迁移
            if h_id and h_id in existing_ids:
                continue
            hooks_to_migrate.append({
                "id": h_id or f"fs-{int(time.time())}-{migrated_count}",
                "purpose": h.get("title", h.get("purpose", h.get("description", ""))),
                "description": h.get("description", h.get("notes", "")),
                "start_chapter": h.get("start_chapter", h.get("planted_chapter", 0)),
                "end_chapter": h.get("end_chapter", h.get("target_chapter", 0)),
                "characters": h.get("characters", []),
                "status": h.get("status", "planted"),
            })
            migrated_count += 1
            if h_id:
                existing_ids.add(h_id)
        print(f"  [hook_ledger.json] 发现 {len(raw_hooks)} 条伏笔（去重后新增 {migrated_count - len([h for h in hooks_to_migrate if 'id' in h and h['id'] in existing_ids])} 条）")

    if not hooks_to_migrate:
        print("  无需迁移伏笔数据")
        # 确保 outline.json 有 foreshadowing 字段
        if "foreshadowing" not in outline_data:
            outline_data["foreshadowing"] = []
            write_json(str(outline_path), outline_data)
        return 0

    # 合并到 outline.json.foreshadowing（去重）
    existing_foreshadows = outline_data.get("foreshadowing", [])
    existing_purposes = {(fs.get("purpose", ""), fs.get("start_chapter", 0)) for fs in existing_foreshadows}

    added = 0
    for h in hooks_to_migrate:
        key = (h.get("purpose", ""), h.get("start_chapter", 0))
        if key not in existing_purposes:
            existing_foreshadows.append(h)
            existing_purposes.add(key)
            added += 1

    outline_data["foreshadowing"] = existing_foreshadows
    write_json(str(outline_path), outline_data)
    print(f"  已将 {added} 条伏笔写入 outline.json.foreshadowing（总计 {len(existing_foreshadows)} 条）")

    # 删除旧 hooks.json
    if hooks_json_path.exists():
        hooks_json_path.unlink()
        print(f"  已删除旧文件: outline/hooks.json")

    return migrated_count


def migrate_chapter_metadata(book_dir: Path, outline_data: dict) -> int:
    """
    为每个 chapters/ 下的 .md 文件生成对应的 .json 元数据。
    返回生成的元数据文件数量。
    """
    chapters_dir = book_dir / "chapters"
    generated = 0

    # 扫描所有 .md 文件（包括 final/ 和 draft/ 子目录）
    md_files = []
    for sub_dir in [chapters_dir, chapters_dir / "final", chapters_dir / "draft"]:
        if sub_dir.exists():
            for f in sub_dir.glob("chapter-*.md"):
                md_files.append(f)

    if not md_files:
        print("  未发现章节 .md 文件")
        return 0

    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")

    for md_path in sorted(md_files):
        chapter_number = extract_chapter_number(md_path.name)
        if chapter_number == 0:
            continue

        # 目标元数据路径: chapters/chapter-NNNN.json
        meta_path = chapters_dir / f"chapter-{chapter_number:04d}.json"
        if meta_path.exists():
            # 已有元数据，只补充 outline_chapter_id
            meta = read_json(str(meta_path))
            if not meta.get("outline_chapter_id"):
                ocid = find_outline_chapter_id(outline_data, chapter_number)
                if ocid:
                    meta["outline_chapter_id"] = ocid
                    write_json(str(meta_path), meta)
                    print(f"  补充 outline_chapter_id: chapter-{chapter_number:04d} -> {ocid}")
            continue

        # 读取正文
        content = md_path.read_text(encoding="utf-8")
        word_count = len(content.replace("\n", "").replace(" ", ""))
        title = extract_title_from_content(content, chapter_number)

        # 确定状态
        status = "draft"
        if "final" in str(md_path):
            status = "completed"

        # 查找关联的 outline chapter id
        outline_chapter_id = find_outline_chapter_id(outline_data, chapter_number)

        meta = {
            "number": chapter_number,
            "title": title,
            "word_count": word_count,
            "outline_chapter_id": outline_chapter_id,
            "created_at": now_str,
            "updated_at": now_str,
            "status": status,
        }
        write_json(str(meta_path), meta)
        generated += 1
        print(f"  生成元数据: chapter-{chapter_number:04d}.json (title={title}, words={word_count}, outline_id={outline_chapter_id})")

    return generated


def main():
    if len(sys.argv) < 2:
        print("用法: python migrate_v3_to_v4.py <book_dir>")
        print("示例: python migrate_v3_to_v4.py /path/to/books/my-novel")
        sys.exit(1)

    book_dir = Path(sys.argv[1]).resolve()
    if not book_dir.exists():
        print(f"错误: 目录不存在: {book_dir}")
        sys.exit(1)

    print(f"=== NovelWorkshop v3 → v4 数据迁移 ===")
    print(f"书籍目录: {book_dir}")
    print()

    # 加载 outline 数据
    outline_path = book_dir / "outline" / "outline.json"
    outline_data = read_json(str(outline_path))

    # 步骤 1: 迁移伏笔
    print("[1/3] 迁移伏笔数据...")
    hooks_migrated = migrate_hooks(book_dir)
    print(f"  完成: 迁移了 {hooks_migrated} 条伏笔")
    print()

    # 重新加载 outline 数据（因为伏笔迁移可能已更新）
    outline_data = read_json(str(outline_path))

    # 步骤 2: 生成章节元数据
    print("[2/3] 生成章节元数据...")
    meta_generated = migrate_chapter_metadata(book_dir, outline_data)
    print(f"  完成: 生成了 {meta_generated} 个章节元数据文件")
    print()

    # 步骤 3: 标记迁移完成
    print("[3/3] 标记迁移完成...")
    outline_data["migrated_to_v4"] = True
    write_json(str(outline_path), outline_data)
    print(f"  已在 outline.json 中标记 migrated_to_v4: true")
    print()

    print("=== 迁移完成 ===")
    print(f"  - 伏笔迁移: {hooks_migrated} 条")
    print(f"  - 章节元数据: {meta_generated} 个文件")
    print(f"  - 旧 hooks.json 已删除")
    print(f"  - outline.json 已标记 migrated_to_v4")


if __name__ == "__main__":
    main()
