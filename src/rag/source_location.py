"""Source locations shared by context, progress messages and previews."""

from typing import Mapping


def build_location_label(metadata: Mapping[str, object]) -> str:
    if metadata.get("source_type") == "excel":
        sheet = metadata.get("sheet_name") or "未知工作表"
        start, end = metadata.get("row_start"), metadata.get("row_end")
        if start is None or end is None:
            return f"工作表「{sheet}」，未知列號"
        rows = str(start) if start == end else f"{start}–{end}"
        return f"工作表「{sheet}」，第 {rows} 列"
    if metadata.get("source_type") == "image":
        return "圖片"
    return f"第 {metadata.get('page_number') or '未知'} 頁"
