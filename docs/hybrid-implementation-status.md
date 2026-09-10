# Hybrid v1.6.2 實作追蹤

狀態：實作與驗證進行中，尚未宣告規格全部完成或品質 Acceptance 通過。

| 範圍 | 目前狀態 |
|---|---|
| BM25、識別字／中文 Tokenizer、RRF | 已實作；有固定 I/O、分數與故障測試 |
| Chunk ID、canonical 順序、Registry | 已實作；來源與位置驗證、重複拒絕 |
| Settings、正式問答、UI 降級與計數 | 已接入；繼續核對全部錯誤組合 |
| 原子建庫與成功後清理 | 已實作；失敗回復有測試 |
| 固定 Reranker revision 與權重驗證 | 已實作；本機載入與實際評分成功 |
| Golden Dataset | 50 題、662 Chunk；Gold 唯一性 Preflight 通過 |
| 四組、五次 Trial、精確指標／品質 Gate | 已實作；真實模型完整 Benchmark 待完成 |
| Acceptance fingerprint、環境、工作目錄 | 已實作；乾淨 checkout 端到端 Acceptance 待完成 |
| 發布預設 | 保持 false；無通過的發布 Manifest |

補充契約：無 query string 時，Path-only Token 與完整 request-target 相同，只輸出一次。
不同 Path segment 或 query parameter 原文位置仍保留詞頻。
