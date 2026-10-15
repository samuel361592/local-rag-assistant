 # Hybrid v1.6.2 實作追蹤

狀態：2026-10-08 完成 config.hybrid-v6 的真實模型品質 Acceptance，結果 PASSED。完整規格與發布 Promotion 仍分別追蹤。

[品質驗收報告](hybrid-quality-acceptance-2026-10-08.md) 包含原始結果、精確指標、五輪一致性與效能警示。

| 範圍 | 目前狀態 |
|---|---|
| BM25、識別字／中文 Tokenizer、RRF | 已實作；有固定 I/O、分數與故障測試 |
| Chunk ID、canonical 順序、Registry | 已實作；來源與位置驗證、重複拒絕 |
| Settings、正式問答、UI 降級與計數 | 已接入；修復背景問答參數傳遞，含 Hybrid 開／關回歸測試 |
| 原子建庫與成功後清理 | 已實作；失敗回復有測試 |
| 固定 Reranker revision 與權重驗證 | 已實作；本機載入與實際評分成功 |
| Golden Dataset | 50 題、662 Chunk；Gold 唯一性 Preflight 通過 |
| 四組、五次 Trial、精確指標／品質 Gate | 四組／50 題暖機／五輪正式 Trial 已完成；品質 Gate PASSED |
| Acceptance fingerprint、環境、工作目錄 | 乾淨 checkout、隔離依賴、Preflight／Postflight 與五輪排名一致性通過 |
| 發布預設 | Acceptance Manifest 已準備；尚未執行 Promotion，發布預設 false |

補充契約：無 query string 時，Path-only Token 與完整 request-target 相同，只輸出一次。
不同 Path segment 或 query parameter 原文位置仍保留詞頻。

2026-10-08：完整測試 202 通過、1 略過。BM25＋RRF 額外 P95 為 149.924 ms，超過 100 ms 警示預算，列為後續效能事項。語意 Hit@8 由 13/20 降至 12/20，符合最多減少一題的品質門檻。
