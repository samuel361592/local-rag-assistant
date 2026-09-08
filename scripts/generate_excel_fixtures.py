"""Generate non-sensitive XLSX examples; synthetic caches are explicitly labelled.

Run with the project Python. This never overwrites formula_cached.xlsx, which
must be supplied by a maintainer after saving in Excel or LibreOffice.
"""

from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import openpyxl


OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "excel"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def add_synthetic_cache(workbook, path: Path, values: dict[str, int]) -> None:
    stream = BytesIO()
    workbook.save(stream)
    with ZipFile(stream) as source, ZipFile(path, "w") as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(data)
                for cell in root.iter(f"{NS}c"):
                    coordinate = cell.attrib["r"]
                    if coordinate in values:
                        cell.find(f"{NS}v").text = str(values[coordinate])
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(entry, data)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FormulaCache"
    ws.append(["Product", "Quantity", "Price", "Amount"])
    ws.append(["A", 4, 5, "=B2*C2"])
    ws.append(["B", 3, 7, "=B3*C3"])
    wb.save(OUTPUT / "formula_without_cache.xlsx")
    add_synthetic_cache(wb, OUTPUT / "formula_cached_synthetic.xlsx", {"D2": 20, "D3": 21})

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append([None, "=1+1"])
    ws.append(["名稱", "名稱", "名稱 [A]", None, "日期", "日期時間", "時間", "啟用", "小數"])
    ws.append(["A", 4, 5, "=B3*C3", date(2026, 9, 8), datetime(2026, 9, 8, 10, 20, 30), time(10, 20, 30), True, 1.23])
    ws.append([None])
    ws.append(["B", 3, 7, "=B5*C5"])
    ws["K5"] = "表頭外資料"
    ws["A6"] = "長文字" * 300
    ws.merge_cells("A7:A8")
    ws["A7"] = "合併值"
    ws["B8"] = "不向下填滿"
    hidden = wb.create_sheet("Hidden")
    hidden.sheet_state = "hidden"
    hidden.append(["標題"])
    hidden.append(["隱藏工作表仍索引"])
    wb.create_sheet("Empty")
    add_synthetic_cache(wb, OUTPUT / "excel_success_cases.xlsx", {"D3": 20})

    for filename, row, column, value in (
        ("failure_row_too_long.xlsx", 2, 1, "x" * 2500),
        ("failure_row_index.xlsx", 50001, 1, "out of bounds"),
        ("failure_column_index.xlsx", 2, 201, "out of bounds"),
    ):
        wb = openpyxl.Workbook()
        wb.active.append(["A", "B"])
        wb.active.cell(row, column, value)
        if filename == "failure_row_too_long.xlsx":
            wb.active["B2"] = "y" * 2500
        wb.save(OUTPUT / filename)
    print(f"Generated fixtures with openpyxl {openpyxl.__version__} in {OUTPUT}")


if __name__ == "__main__":
    main()
