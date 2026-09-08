# Excel fixtures

These files contain only synthetic, non-sensitive data. Generated using
openpyxl 3.1.5, Python, and explicit XML cache injection where noted.

Run `python scripts/generate_excel_fixtures.py` from the project root to
regenerate these files. Tests read the committed files and do not run an
office application or download models.

| File | Contents |
| --- | --- |
| `formula_without_cache.xlsx` | Sheet `FormulaCache`: D2 `=B2*C2`, B2=4, C2=5; D3 `=B3*C3`, B3=3, C3=7. Both cached values are absent. |
| `formula_cached_synthetic.xlsx` | Same formulas, with synthetic XML cached values D2=20 and D3=21. **Not saved by Excel/LibreOffice.** |
| `excel_success_cases.xlsx` | Three sheets, hidden/empty sheets, duplicate headers, gaps, types, merged cells, dynamic columns and a 900-character oversized row under default CHUNK_SIZE=500. D3 has synthetic cached value 20; D5 and B1 have no cache. |
| `failure_row_too_long.xlsx` | Two individually valid values produce a row longer than 4,000 characters. |
| `failure_row_index.xlsx` | Cell A50001 exceeds the default row coordinate limit. |
| `failure_column_index.xlsx` | Cell GS2 (column 201) exceeds the default column coordinate limit. |

## Outstanding real-application validation

The specification's `formula_cached.xlsx` is **not supplied yet**: this
environment has neither Excel nor LibreOffice, and the user has no existing
fixture. Synthetic XML fixtures verify the parser but do not satisfy this
specific acceptance requirement.

To complete it:

1. Open `formula_without_cache.xlsx` in Excel or LibreOffice.
2. Recalculate and save a copy named `formula_cached.xlsx` in this directory.
3. Record the application name/version and date in this README.
4. Run `python -m pytest tests/test_excel_processing.py`.
   The real-cache test must pass rather than skip: D2=20 and D3=21 with
   `data_only=True`; both formulas remain available with `data_only=False`.

Use `excel_success_cases.xlsx` for successful mixed PDF/image/XLSX uploads
with the default limits. Test each failure file separately after establishing
a working index; the old index and previews must remain available. Live model
answers and real-application formula cache validation remain manual acceptance
steps; automated UI tests use fake vector/model dependencies.
