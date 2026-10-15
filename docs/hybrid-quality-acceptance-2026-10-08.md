# Hybrid Retrieval 品質驗收（2026-10-08）

判定：**PASSED**。

驗收時間（台北）：2026-10-08T17:45:10+08:00

## 驗收範圍

- 固定 hybrid-eval-v1：兩份 NIST PDF 與一份識別字 XLSX，共 50 題。
- 題型：語意改寫 20、精確詞 10、識別字 10、混合查詢 10。
- 50 題完整暖機後，執行 5 輪、每輪 50 題；四組共享同題 Dense 與 BM25 計算。
- 品質 Baseline 為 CURRENT_BASELINE（Dense＋Reranker）；TARGET 為 Dense＋BM25＋RRF＋Reranker。
- 每題保留 Top 20 排名；正式回答深度為 8。無跨 Trial 查詢向量或重排分數快取。

## 版本與可重現性

- Evaluated commit：2895c8cecf34e4983e57a570578c9a9d1fe5f3a9
- 設定：evaluation/config.hybrid-v6.json；未修改資料集或品質門檻。
- Config ID：e217ebcfaf54b624a9f47acb3be4cc69508cb4bd9d48ae337435fc2abddd0214
- Run ID：20261008T062103102111Z_2895c8cecf34_e217ebcfaf54
- Pipeline fingerprint：383d1b351f0cb930009121ca056294a269a3cea759b14fc875141c67e52ce39f
- 原始結果 SHA-256：82d08007f8a9d3fb27c26750ec109a8e970df80744bd1162ccb4dc3dca8458fd
- 結果：[JSON](../evaluation/results/hybrid-eval-v1/e217ebcfaf54b624a9f47acb3be4cc69508cb4bd9d48ae337435fc2abddd0214/20261008T062103102111Z_2895c8cecf34_e217ebcfaf54.json)

## 整體品質

| 組別 | Hit@1 | Hit@5 | Hit@8 | Hit@20 | MRR@20 |
|---|---:|---:|---:|---:|---:|
| DENSE_RAW | 60.00% | 78.00% | 78.00% | 80.00% | 0.65733333 |
| CURRENT_BASELINE | 66.00% | 78.00% | 80.00% | 80.00% | 0.71119048 |
| HYBRID_RRF | 56.00% | 66.00% | 72.00% | 82.00% | 0.61585178 |
| TARGET | 68.00% | 80.00% | 84.00% | 86.00% | 0.73149206 |

## 題型比較

| 題型 | Baseline Hit@5 | Target Hit@5 | Baseline Hit@8 | Target Hit@8 | Baseline MRR@20 | Target MRR@20 |
|---|---:|---:|---:|---:|---:|---:|
| semantic_paraphrase | 60.00% | 55.00% | 65.00% | 60.00% | 0.49047619 | 0.47658730 |
| exact_term | 70.00% | 90.00% | 70.00% | 100.00% | 0.57500000 | 0.70428571 |
| exact_identifier | 100.00% | 100.00% | 100.00% | 100.00% | 1.00000000 | 1.00000000 |
| mixed_semantic_exact | 100.00% | 100.00% | 100.00% | 100.00% | 1.00000000 | 1.00000000 |

## 品質 Gate

| 檢查 | 結果 |
|---|---|
| 整體 MRR 非劣 | 通過 |
| 整體 Hit@8 非劣 | 通過 |
| 語意改寫 Hit@8 最多少一題 | 通過 |
| 識別字 ceiling-aware Gate | 通過 |
| 預先指定指標改善／全滿分非劣規則 | 通過 |

五輪排名一致性：通過；共 200 個問題／組別組合。
品質聚合與 Gate 使用精確 Fraction；表格中的小數與百分比僅供顯示。
原始 CLI 完成依賴、工作目錄、來源、模型 digest 與 fingerprint 的 Preflight／Postflight。

## 效能

| 組別 | P50（ms） | P95（ms） |
|---|---:|---:|
| DENSE_RAW | 2805.179 | 4758.024 |
| CURRENT_BASELINE | 17319.667 | 29876.980 |
| HYBRID_RRF | 2865.477 | 4928.475 |
| TARGET | 22228.398 | 36370.551 |

BM25＋RRF 額外 P95：149.924 ms；100 ms 警示預算：超標。
各組 P50／P95 由自身 250 筆逐題總耗時樣本計算，沒有相加階段 P95。

BM25 來源 Chunk：662；可搜尋 Chunk：662；空 Token 排除：0。

## 相關修正與驗證

- app.py 的背景問答函式補上 BM25 Store 與 Chunk Registry 參數，修復五個參數傳入三個參數函式的錯誤。
- 增加 Hybrid 開啟／關閉的背景問答回歸測試。完整測試：202 通過、1 略過。
- 略過項目是既有真實 Excel 應用公式快取 fixture，不影響本次固定 Retrieval Dataset。
- 環境準備期間的套件連結複製失誤已修復；完整 149 個套件版本與 43,049 個 RECORD 檔案雜湊驗證通過。
- UI 修正於目前工作目錄另行測試；Retrieval Acceptance 對應上列已提交版本。

## 決策

符合品質驗收與可證明收益條件；可據本次結果建立發布 Manifest，再依規格進行 Promotion。

本次收益主要來自精確詞：Hit@8 由 7/10 提升到 10/10。語意改寫由 13/20 降到 12/20，恰好符合最多減少一題的門檻，仍值得後續改善。

通過結論限定 TARGET（包含 Reranker）。停用 Reranker 的 HYBRID_RRF 整體 Hit@8 為 72%，低於 DENSE_RAW 的 78%，不能沿用 TARGET 的品質通過結論。

Acceptance Manifest：[hybrid-default.json](../evaluation/releases/hybrid-default.json)。Manifest 已準備但尚未 Promotion；UI 修正仍於工作目錄，若將其納入後續提交，需依 commit Diff 政策重新確認 Acceptance 有效性。
