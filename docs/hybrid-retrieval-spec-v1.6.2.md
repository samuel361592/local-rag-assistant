# Local RAG Assistant－Hybrid Retrieval 升級規格 v1.6.2

## 1. 文件資訊

| 項目 | 內容 |

|---|---|

| 文件名稱 | Hybrid Retrieval 升級規格 |

| 適用專案 | `samuel361592/local-rag-assistant` |

| 版本 | v1.6.2 |

| 狀態 | 待實作 |

| 主要目標 | 在保留既有 FAISS 與 Reranker 的前提下，加入 BM25 與 RRF，提升中文、精確代號、錯誤碼、API 路徑及 Excel 欄位的檢索品質 |

### 1.1 v1.6 修訂重點

- 分離正式回答深度 `TOP_K`（預設 8）與評測深度 `EVALUATION_DEPTH=20`。

- 明訂 Hybrid 關閉、重新啟用、建庫及設定驗證行為。

- 明訂正式查詢的可見降級策略，以及評測的 Fail-fast 策略。

- 以來源內容雜湊、標準位置與內容雜湊完整定義 Chunk ID。

- 固定評測語料、題型數量、設定檔與 Gold Chunk 判定方式。

- 明訂 BM25、斷詞、正規化、RRF 去重及同分行為。

- 明訂 UI 候選計數時點、跳過事件及 P95 測量方法。

- 加入 Baseline 滿分時的 ceiling-aware 替代驗收規則。

- 統一 `TOP_K` 為可設定、預設 8，並固定 Evaluation 的 `answer_top_k=8`。

- 修正 Session State 在重新啟動後無法保留的生命週期描述。

- 補齊成功、空結果與錯誤交叉組合的查詢決策矩陣。

- 新增 Tokenizer 的固定輸入／Token 輸出案例。

- 將「全部 Chunk 無 Token」定義為可建立的合法空 BM25 Store。

- 定義 Hybrid 在 Benchmark 未執行、失敗、通過與全指標滿分時的預設發布政策。

- 定義各類識別字的完整匹配文法、邊界、最長匹配與 API query string 行為。

- 鎖定 `rank-bm25` 實作版本，並固定初始 Config 的 `k1`、`b`、`epsilon` 預設值。

- 明訂 Chunk ordinal 分組鍵與 Excel Gold 列範圍包含語意。

- 明訂四組評測的共享計算、暖機、五次 Trial、洗牌與品質聚合規則。

- 建立錯誤分類、跨檢索器一致性及 Reranker revision／權重驗證契約。

- 建立調參版本、結果保存與失敗／跳過 UI 的 `null`／`0` 契約。

- 修正 Acceptance commit 與 Promotion commit 的循環失效問題，改以 `evaluated_commit`、Pipeline fingerprint 及允許差異判定 stale。

- 統一識別字最長匹配規則，並將單／雙引號定義為 API request-target 終止字元。

- 將 BM25 數值改定義為版本化預設值，允許正式環境及新 Pipeline Config 使用通過驗證的自訂值。

- 明訂 Reranker skip 判定優先序，消除 disabled 與 no-candidate 同時成立時的衝突。

- 統一 Baseline 與 Target 的完整候選重排範圍及實際輸入數記錄方式。

- v1 固定 Dense 後 BM25 的順序執行，並定義四組逐題總耗時與 P95 計算公式。

- 將 Chunk 一致性檢查改為提交前逐一驗證全部 Chunk，並限定 Reranker 去重的作用範圍。

- 記錄 Reranker 官方 revision／權重雜湊的查證狀態與下載後複驗要求。

- 將 API request-target Regex 移出表格，明訂同一 Path segment 可混合一般字元與百分比編碼，且 Path／Query 都必須整段通過百分比編碼驗證。

- 固定 Pipeline fingerprint 的 Schema、檔案集合、路徑格式、原始 bytes 雜湊、Canonical JSON 與缺檔處理。

- 新增 Acceptance Worktree Preflight／Postflight，確保實際執行內容與 `evaluated_commit` 一致。

- 修正 Reranker Output Error 可降級契約及各設定值的零值邊界測試。

- 品質指標改以精確有理數聚合與比較，不以浮點逐位相等或容差判斷通過。

### 1.2 v1.6 修訂內容

- 明訂外部快取、bytecode、乾淨 checkout 與隔離依賴的適用範圍。

- 固定 LF 與 Git blob 原始 bytes 比對，新增完整實際依賴 Manifest 與 fingerprint v2。

- 補齊 Dense-only 同分規則，澄清點路徑片段並移出時間 Regex。

- 本文件保留原規格全文與歷史對照；實作以目前正文為準。

### 1.3 v1.6.1 實作契約補充

本版不改變 Hybrid Retrieval 的目標架構與品質 Gate，僅補齊會造成不同工程實作結果的契約：

- 修正所有可直接複製的 Regex／code fence，不允許 Markdown escape 混入實際程式內容。
- 明訂新知識庫成功提交後的 Session State 清理範圍；失敗仍維持完全不變。
- 固定 Dense 同分／回傳順序契約、Reranker 實際推論參數記錄要求。
- 固定 `source_type`、`content_type`、`extraction_method` 的列舉值與合法組合。
- 固定錯誤類別對應的 `error_code`。
- 固定 `config_id` 的 RFC 8785 JCS 計算方式與 `run_id` 格式。
- 擴大 Pipeline fingerprint 的 Repository Python 程式涵蓋範圍，並驗證實際 import 不得逃逸。
- 固定 Acceptance `platform` 字串格式及 Ollama model digest 取得／正規化規則。
- 補上重複 query parameter 的 Tokenizer 詞頻契約。

### 1.4 v1.6.2 實作歧義修正

本版延續 v1.6.1，不改變 Retrieval 架構、Dataset 或品質 Gate，只修正剩餘可造成不同實作結果的契約：

- 修正日期／`TIME_PATTERN` 的 Python lookbehind；Regex 內容不得混入 Markdown escape，正文唯一合法形式為 `(?<!...)`。
- 所有 fenced `json` 範例必須能被標準 JSON parser 直接解析；placeholder 使用 `"<sha256>"`、`"<name>"` 等普通 JSON 字串，`<` 前不得加入 Markdown 跳脫反斜線。
- 新增全域 canonical Chunk 建庫順序；Chunk Registry、FAISS 與 BM25 必須使用同一份排序後 Chunk 序列。
- 重新定義 request-target 衍生 Token 的去重作用域：不得對整個 request-target 做全域局部去重；Path 與每個 query parameter pair 分開處理，不同 pair 保留重複詞頻。
- 強化第 14.2 節範例，明示 `exact_identifier` 多命中一題本身不足以通過；仍須滿足第 5 條至少一項預先指定指標嚴格改善。

## 2. 背景與問題

目前正式問答流程只使用 BGE-M3 Dense Embedding 與 FAISS 進行第一階段檢索，再由 `BAAI/bge-reranker-v2-m3` 對候選 Chunk 重排。

現行流程：

```text

Question

  -> BGE-M3 Dense Embedding

  -> FAISS Top RETRIEVAL_TOP_K

  -> Reranker Top TOP_K

  -> Context

  -> qwen3:4b

```

Dense Retrieval 能處理同義改寫及語意相近內容，但對下列精確字串可能不穩定：

- 產品或設備編號，例如 `ABC-123`。

- CRM／Excel 欄位，例如 `FU038`。

- 錯誤碼，例如 `SOURCE_NOT_FOUND`。

- API 路徑，例如 `/REP/TobeRepair/Query`。

- 日期、型號、序號及其他低語意、高識別性的字串。

## 3. 目標

1. 保留既有 BGE-M3、FAISS 與 Reranker。

2. 新增 BM25 Sparse Retrieval，補強精確關鍵字檢索。

3. 使用 Reciprocal Rank Fusion（RRF）合併 Dense 與 BM25 排名。

4. 將融合後候選交由既有 Reranker 精排。

5. 支援中文內容及完整保留英文代號、錯誤碼與 API 路徑。

6. 擴充 Retrieval Evaluation，量化 Hybrid Search 對 Hit Rate 與 MRR@20 的改善。

7. 保持知識庫原子替換：新知識庫完整建立成功後才取代舊知識庫。

## 4. 非目標

本版本不包含：

- 將 FAISS 替換成 Qdrant、Milvus、Pinecone、Chroma 或 pgvector。

- 將 FAISS Flat Index 改成 HNSW、IVF 或 PQ。

- Query Rewrite、HyDE、Multi-Query Retrieval。

- LLM 判斷檢索路徑或動態選擇 Retriever。

- 正式 Streamlit 知識庫永久保存。

- 修改現有文件解析、OCR、VLM 或 Excel Row Packer 規則。

## 5. 目標架構

```text

                              +-> Original trimmed query -> BGE-M3 -> FAISS Dense Top-K --+

User Question ----------------+                                                       +-> RRF -> Fusion Top-K

                              +-> BM25-only normalize/tokenize -> BM25 Sparse Top-K ---+

                                                                    |

                                                                    v

                                                         Existing Reranker

                                                                    |

                                                                    v

                                                               Answer Top-K

                                                                    |

                                                                    v

                                                           Context -> qwen3:4b

```

### 5.1 建庫流程

1. 沿用現有文件解析流程建立 `list[Document]`。

2. 計算來源 ID、標準位置及 Chunk ID。

3. 使用原始 `page_content` 建立 FAISS Dense Index。

4. `HYBRID_SEARCH_ENABLED=true` 時，對相同 Chunk 執行 BM25 正規化與斷詞並建立 BM25 Index；為 `false` 時不得建立 BM25 Index。

5. Dense 與 BM25 必須共用穩定的 Chunk ID。

6. 所有本次啟用的索引皆成功後，才一次提交到 Streamlit Session State。

7. 任一必要索引建立失敗時，不得替換目前生效的知識庫與問答狀態。

### 5.1.1 知識庫原子提交後的 Session State 契約

建庫成功與失敗必須視為單一 Transaction 邊界：

- **成功**：一次原子替換本次知識庫相關的 FAISS、BM25、Chunk Registry、來源檔案清單、Chunk 預覽資料與建庫統計。提交完成後，必須清除所有依賴舊知識庫內容的 Query State，包括聊天紀錄、最近一次 `RagResult`、最近回答、Retrieval debug／候選清單、檢索 Count／Status、來源篩選、Chunk 預覽選取、舊知識庫警告及其他引用舊 Chunk ID 的 UI State。
- **成功時可保留**：純 UI 偏好且與特定知識庫內容無關的設定，例如展開／收合狀態；不得保留任何可能引用舊來源、舊 Chunk 或舊回答的值。
- **失敗**：上述所有生效中的知識庫與 Query State 必須保持提交前值，包含舊聊天、舊回答、舊檢索紀錄與目前生效檔案；不得先清除後再嘗試回填。
- `knowledge_state.py` 必須集中定義「KB-bound state keys」與「query-bound state keys」，建庫呼叫端不得各自散落清除邏輯。
- 原子提交後若任一必要 State key 寫入失敗，視為 `KnowledgeStateError`，不得留下 Dense 新、BM25 舊或 Registry 不一致的部分提交狀態。

### 5.2 問答流程

1. 驗證問題不是空字串，並保留 `strip()` 後的原始問題供 Dense 與 Reranker 使用。

2. FAISS 取回 `RETRIEVAL_TOP_K` 個 Dense 候選。

3. Hybrid 啟用時，BM25 以專用正規化問題取回 `BM25_TOP_K` 個 Sparse 候選；Hybrid 停用時跳過本步與 RRF。

4. Hybrid 啟用時，使用 RRF 合併可用排名並去除重複 Chunk。

5. 取融合排名前 `FUSION_TOP_K` 個候選。

6. 啟用 Reranker 時，將第一階段候選交由既有 Reranker 評分並取 `TOP_K`。

7. 停用 Reranker 時，Hybrid 模式直接取 RRF 前 `TOP_K`；Dense-only 模式直接取 FAISS 前 `TOP_K`。

8. 沿用既有 Context、來源資訊與 LLM 回答流程。

9. 正式回答最多使用設定值 `TOP_K` 個 Chunk，預設為 8；評測另依第 12 節保留至第 20 名，不受回答截斷影響。

## 6. 檢索演算法

### 6.1 Dense Retrieval

- Embedding：沿用 `EMBEDDING_MODEL=bge-m3`。

- Vector Store：沿用 LangChain FAISS。

- 候選數量：沿用 `RETRIEVAL_TOP_K`。

- 不在本版本調整距離函數或 FAISS Index 類型。
- Dense Retrieval 不對 FAISS 回傳結果做二次依 Score 排序；候選順序以 FAISS API 實際回傳順序為唯一 Dense Rank。
- 建立 FAISS Index 前，必須先依第 9.2.2 節產生唯一的 `canonical_chunk_sequence`；FAISS 的 Document insertion order、Chunk Registry 建立順序與 BM25 接收的完整 Chunk 順序全部使用同一序列，不得各自依檔名、上傳順序、dict iteration order 或 Retriever 自行排序。
- Chunk ordinal 必須在 canonical 全域排序前完成配置；第 9.2.2 節排序不得重新編號 ordinal。
- 若相同 `canonical_chunk_sequence`、相同 Pipeline Config 與相同 FAISS 實作仍使完全相同距離候選在五次 Trial 間改變順序，必須由第 12.5 節 Determinism Gate 判定為 `NON_DETERMINISTIC`；不得在 Evaluation 階段臨時加入未記錄的 tie-breaker 修補結果。

### 6.2 BM25 Retrieval

- 唯一允許的 v1 實作為 `rank-bm25==0.2.2` 的 `BM25Okapi`；不得在相同評測設定下替換成 Elasticsearch、Whoosh、自製 BM25 或其他變體。

- 初始程式預設值及 `evaluation/config.hybrid-v1.json` 的固定值為：

```python

BM25Okapi(

    tokenized_corpus,

    k1=1.5,

    b=0.75,

    epsilon=0.25,

)

```

- 上述三個數字是版本化預設值，不是所有執行不可變更的常數。正式應用程式使用第 7 節驗證後的環境設定值；Evaluation 僅使用該次 Pipeline Config 明列的值，不得受環境變數覆寫。

- 實際使用的 `k1`、`b`、`epsilon`、套件名稱與套件版本都必須寫入 Evaluation 設定、結果 Manifest 與 Evaluation cache signature，並實際傳入 `BM25Okapi`。

- 任一參數或套件版本變動都視為新的 Pipeline Config，依第 12.7 節建立新識別，不得覆蓋既有結果；正式知識庫也必須重建 BM25 Store。

- 正式環境使用的參數若沒有對應且有效的 Acceptance Manifest，功能仍可明確手動啟用，但發布狀態必須標記為 `custom_unverified`，不得沿用預設 Config 的通過結論。

- BM25 Store 接收與 FAISS 相同的完整 Chunk 清單及 Chunk ID；斷詞後非空的 Chunk 才加入實際評分 Corpus，空 Token Chunk 保留於來源統計但不加入 `BM25Okapi`。

- BM25 回傳內容仍為原始 LangChain `Document`，不得把斷詞後文字送進 Context。

- 僅 `score > 0` 且為有限數值的文件可進入候選；零分與負分文件一律排除，不得為補滿 `BM25_TOP_K` 而加入。

- `NaN` 或正負無限值代表索引或計算異常，必須拋出 `BM25SearchError`，不得當作零分處理。

- 同分依 `chunk_id` 字典序升冪排列，以確保跨 Process 可重現。

- `BM25_TOP_K` 大於合格結果數時回傳實際合格數量，不補滿。

- Query 經斷詞後沒有 Token，或所有文件分數皆小於或等於 0 時，回傳空候選；這是合法的「無結果」，不是查詢失敗。

- 完整 Chunk 清單本身為空時，沿用現有規則使整批建庫失敗。

- 有 Chunk、但全部 Chunk 斷詞後皆無 Token 時，必須建立合法的 `EmptyBM25Store`，不得呼叫 `BM25Okapi`：

  - `source_document_count = len(all_chunks)`。

  - `searchable_document_count = 0`。

  - `status = "empty_no_tokens"`。

  - 任意合法 Query 搜尋都回傳空結果。

  - 建庫成功但 UI 顯示「BM25 沒有可搜尋詞彙，本知識庫將以 Dense Retrieval 為主」警告。

- 部分 Chunk 無 Token 時只排除那些 Chunk，並在建庫統計顯示排除數量；這不算查詢錯誤或降級。

### 6.3 中文與識別字斷詞

使用固定版本 `jieba==0.42.1` 與版本控管的 `src/rag/tokenizer_userdict.txt` 處理中文，呼叫 `jieba.lcut(text, HMM=False)`。在中文斷詞前，以由左至右、不可重疊且具固定優先序的掃描器抽取需要完整保留的識別字。文件與 Query 必須使用同一個純函式及相同規則版本 `bm25-tokenizer-v1`。

#### 6.3.1 識別字完整匹配文法

所有 Regex 都在 NFKC 後文字上執行，ASCII 字元範圍固定，不使用語言環境相依的 `\w`。掃描器由左至右；同一開始位置若多個規則可匹配，先選字元數最長者，長度相同才依表中優先序。已占用字元不得再次成為另一完整識別字。

一般識別字的左、右邊界定義為：左側不得是 `[A-Za-z0-9_]`，右側不得是 `[A-Za-z0-9_]`。中文不屬於此邊界集合，因此 `欄位FU038代表` 可以取出 `FU038`。

API request-target 使用下列唯一 Regex，並以 `re.VERBOSE | re.ASCII` 編譯；表格只描述語意，不重複 Regex：

```python

API_REQUEST_TARGET_PATTERN = r"""

/

(?:

    (?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+

    (?:/(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+)*

    /?

)?

(?:[?]

    (?:[A-Za-z0-9._~!$&()*+,;=:@/?+-]|%[0-9A-Fa-f]{2})*

)?

"""

```

- `segment = (?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+`，因此同一 Segment 可混合一般字元與完整百分比編碼，例如 `/files/a%20b`。

- 掃描器先從 `/` 取得直到空白、控制字元、`#`、單引號、雙引號、`<`、`>` 或非 ASCII 字元前的完整原始候選，再要求整個候選通過 `fullmatch()`；不得只接受合法前綴。

- Path 與 Query 中的 `%` 都只能出現在完整 `%[0-9A-Fa-f]{2}`。任何裸 `%`、少於兩位十六進位數或非十六進位內容都使整個 request-target 候選不成立，再將完整候選交回一般 Tokenizer。

| 優先序 | 類型 | 完整匹配文法與額外條件 | 最大長度 |

|---:|---|---|---:|

| 1 | API request target | 必須完整符合上方 `API_REQUEST_TARGET_PATTERN`；可有多個 Segment、結尾 `/` 與 Query；左側不得是 `[A-Za-z0-9_%]` | 2048 |

| 2 | 日期 | `(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])`，且必須能以 Gregorian calendar 驗證 | 10 |

| 3 | 時間 | 使用下方 TIME_PATTERN；小時 00～23，分鐘／秒 00～59，秒可省略 | 8 |

| 4 | 版本／小數 | 邊界內 `v?[0-9]+(?:\.[0-9]+){1,3}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?` | 128 |

| 5 | 底線錯誤碼 | 邊界內 `[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+` | 128 |

| 6 | 連字號代號 | 邊界內、至少含一個 ASCII 字母的 `[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+` | 128 |

| 7 | 一般英數混合代號 | 邊界內、同時至少含一個 ASCII 字母與一個數字的 `[A-Za-z0-9]+` | 128 |

時間 Regex 獨立定義如下，以 `re.ASCII` 編譯；不得把 Markdown 表格跳脫字元當作 Regex 內容：

```python

TIME_PATTERN = r"(?<![0-9])(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?(?![0-9])"

```

API query string 規則：

- 完整 request-target Token 包含 Path 與 query string，但不包含 `#fragment`；遇到空白、控制字元、`#`、單引號、雙引號、`<`、`>` 或非 ASCII 字元即結束。單引號不屬於本系統支援的 request-target 子集合，合法 apostrophe 必須寫成 `%27`。

- Path 與 Query 的百分比編碼都套用上方整段驗證規則；不得只保留非法 `%` 前的合法前綴。

- Query 使用 `&` 或 `;` 分隔 pair，第一個 `=` 分隔 name/value；空 name 不輸出，空 value 只輸出 name。
- 完整 request-target 本身只負責先輸出一個「完整 request-target Token」；**不得把整個 request-target 視為一個局部去重作用域**。其衍生 Token 必須拆成 Path scope 與各個 query parameter pair scope 分別處理。
- Query parameter pair 依原文出現順序逐一處理；不同 pair 之間不得去重。同名 parameter 重複出現時，每個 pair 都各自輸出一次 parameter name Token，以保留原始詞頻。
- 每一個 pair 的 parameter name 與 value 是不同原文位置，不互相去重；非空 value 再獨立套用非 API 識別字／一般 Token 規則。局部去重只允許發生在「單一衍生元件自己的 expansion」內，例如一個識別字 expansion 或一個 value expansion，不得跨 Path segment、name/value 或不同 pair 去重。

- 不執行 URL decode，也不把 `+` 轉成空白；百分比編碼維持 NFKC 後原字面並 `casefold()`。

- 除完整 request-target Token 外，依序輸出 Path-only Token、各 Path segment 的衍生 Token，再依原文順序輸出每個 query parameter pair 的 name 與非空 value 衍生 Token。

- 超過最大長度的候選不視為完整識別字，交回一般 Tokenizer 分段處理並記錄 `identifier_overflow_count`；不得截斷後假裝完整匹配。

#### 6.3.2 一般 Token 與子詞規則

正規化及斷詞規則：

1. 僅 BM25 分支使用 Unicode NFKC 正規化、`casefold()` 與斷詞；不得覆寫原始 `Document.page_content`。

2. Dense Embedding 與 Reranker 僅使用既有的 `question.strip()` 結果及原始 Chunk 文字，不使用 BM25 正規化文字，以維持現有 Baseline 行為。

3. Golden Dataset 的 `expected_text` 仍對原始 Chunk 執行區分大小寫的精確子字串比對，不使用 BM25 正規化。

4. 連續空白在 BM25 分支合併為一個空白。

5. 下列識別字必須保留完整 Token：

   - 英數混合代號：`FU038`、`ABC-123`。

   - 底線錯誤碼：`SOURCE_NOT_FOUND`。

   - API 路徑：`/REP/TobeRepair/Query`。

   - 小數、日期及時間：`1.8.0`、`2026-09-08`、`09:30`。

6. 每個識別字除完整 Token 外，額外產生可用子詞：

   - `FU038` → `fu038`、`fu`、`038`。

   - `ABC-123` → `abc-123`、`abc`、`123`。

   - `SOURCE_NOT_FOUND` → `source_not_found`、`source`、`not`、`found`。

   - `/REP/TobeRepair/Query` → `/rep/toberepair/query`、`rep`、`toberepair`、`tobe`、`repair`、`query`。

   - 完整 Token 與子詞皆加入 BM25 Token 序列。

7. CamelCase 拆分必須在 `casefold()` 前取得邊界；拆分後再轉為小寫。

8. 中文與識別字直接相連時，例如 `欄位FU038代表`，掃描器先抽出 `FU038`，左右中文片段再各自交由 `jieba.lcut()`。

9. 不屬於識別字的標點與純空白 Token 排除；識別字內的 `/`、`-`、`_`、`.`、`:` 保留。

10. 本版本不移除停用詞、不進行詞幹化，也不將 BM25 正規化套用至 Dense 或 Reranker。

一般 Token 規則：

- 一般英文：匹配 `[A-Za-z]+(?:'[A-Za-z]+)?`，輸出 `casefold()` 後 Token；前後標點排除。

- 純數字：匹配 `[0-9]+`，保留前導 0；已被日期、時間、版本或其他識別字占用的數字不得重複由一般規則輸出。

- 一般連續英文字若含 CamelCase，輸出完整小寫 Token，再輸出 CamelCase 子詞。

- CamelCase 邊界同時包含 `lowercase/digit -> Uppercase` 與 `縮寫尾端 -> Uppercase+lowercase`；例如 `TobeRepair -> ["toberepair", "tobe", "repair"]`、`XMLHttpRequest -> ["xmlhttprequest", "xml", "http", "request"]`、`API -> ["api"]`。

- 非 request-target 的單一完整識別字（例如 `FU038`、`ABC-123`、`SOURCE_NOT_FOUND`、日期、時間、版本）中，完整 Token 與該識別字自身衍生子詞依第一次出現順序做局部去重。

- request-target 不套用「整個 target 一次局部去重」。完整 target Token 只輸出一次；Path 與 query parameter 依第 6.3.1 節分 scope 展開。Path 中同一個 segment 在不同原文位置重複時應保留詞頻；不同 parameter pair、以及同一 pair 的 name/value 之間也不得互相去重。

- 不同匹配或原文不同位置之間不得全域去重；同一識別字在原文出現兩次，其 Token 序列也出現兩次，以保留真實詞頻。

掃描器固定由左至右處理。在同一開始位置列出所有合法匹配，先選字元數最長者；只有長度相同時，才依下列類型優先序決定：API 路徑、日期、時間、版本／小數、底線錯誤碼、含連字號代號、一般英數混合代號。選中的範圍占用字元，其他規則不得重複匹配；完整 Token 的子詞仍依第 6 點額外輸出。

固定輸入／輸出案例如下；Token 順序與重複次數都是測試契約：

| 輸入 | 預期 Token 輸出 |

|---|---|

| `欄位FU038代表什麼？` | `["欄位", "fu038", "fu", "038", "代表", "什麼"]` |

| `呼叫/REP/TobeRepair/Query失敗` | `["呼叫", "/rep/toberepair/query", "rep", "toberepair", "tobe", "repair", "query", "失敗"]` |

| `錯誤SOURCE_NOT_FOUND，版本1.8.0` | `["錯誤", "source_not_found", "source", "not", "found", "版本", "1.8.0", "1", "8", "0"]` |

| `於2026-09-08 09:30執行` | `["於", "2026-09-08", "2026", "09", "08", "09:30", "09", "30", "執行"]` |

| `型號ABC-123／欄位ＦＵ０３８` | `["型號", "abc-123", "abc", "123", "欄位", "fu038", "fu", "038"]` |

| `查詢/REP/TobeRepair/Query?id=ABC-123&date=2026-09-08` | `["查詢", "/rep/toberepair/query?id=abc-123&date=2026-09-08", "/rep/toberepair/query", "rep", "toberepair", "tobe", "repair", "query", "id", "abc-123", "abc", "123", "date", "2026-09-08", "2026", "09", "08"]` |

| `呼叫'/api/items?id=A-1'完成` | `["呼叫", "/api/items?id=a-1", "/api/items", "api", "items", "id", "a-1", "a", "1", "完成"]` |

| `呼叫"/api/items?id=A-1"完成` | `["呼叫", "/api/items?id=a-1", "/api/items", "api", "items", "id", "a-1", "a", "1", "完成"]` |
| `/api/items?id=A-1&id=B-2` | `["/api/items?id=a-1&id=b-2", "/api/items", "api", "items", "id", "a-1", "a", "1", "id", "b-2", "b", "2"]` |

| `/api/items?id=id&id=A-1` | `["/api/items?id=id&id=a-1", "/api/items", "api", "items", "id", "id", "id", "a-1", "a", "1"]` |

| `！！！` | `[]` |

- 上表最後一例代表有文字但沒有可索引 Token。

- NFKC 使全形 `ＦＵ０３８` 轉為 `FU038`，全形分隔符 `／` 在本例只作標點排除，不屬於 API 路徑。

- `src/rag/tokenizer_userdict.txt` 至少固定上表所需中文詞彙；字典或 jieba 版本變更必須升級 Tokenizer 規則版本並重建 BM25 與 Evaluation cache。

- Matcher 單元測試另以受控候選驗證「同開始位置取最長」及「同長度才依類型優先序」；不得只靠目前剛好沒有同長衝突的範例間接測試。

### 6.4 RRF 排名融合

每個候選 Chunk 的融合分數：

```text

RRFScore(chunk) = sum(1 / (RRF_K + rank_i(chunk)))

```

- `rank_i` 從 1 開始。

- 預設 `RRF_K=60`。

- Chunk 缺席某份排名時，該份排名的分數貢獻為 0；不得把缺席項目視為「最後一名」加入分數。

- 每份檢索器結果先依 `chunk_id` 去重，只保留第一次出現者，之後重新編為連續的 1-based Rank。

- 同一份結果若相同 `chunk_id` 對應到不同來源或不同內容，視為資料不變量破壞並拋出 `RetrievalInvariantError`，不得降級。

- 跨檢索器的相同 `chunk_id` 合併成單一候選並累加兩邊貢獻。

- 只有一個可用檢索器時，RRF 必須保持該檢索器原始排名。

- 不直接相加 FAISS 距離與 BM25 分數，避免不同分數尺度造成偏差。

- RRF 同分依序使用：出現的檢索器數量降冪、Dense Rank 升冪、BM25 Rank 升冪、`chunk_id` 字典序升冪。缺席 Rank 在同分比較時視為正無限大，但不參與 RRF 分數。

### 6.5 Reranker

- 模型倉庫固定為 `BAAI/bge-reranker-v2-m3`。

- Hugging Face revision 固定為完整 commit SHA [`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`](https\://huggingface.co/BAAI/bge-reranker-v2-m3/commit/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e)，不得使用浮動的 `main`。

- `model.safetensors` 預期 SHA-256 固定為 `d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286`；來源為[官方模型檔案頁](https\://huggingface.co/BAAI/bge-reranker-v2-m3/blob/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e/model.safetensors)。

- 上述 revision、檔案存在性與 SHA-256 已於 `2026-09-08` 依官方 Hugging Face 頁面查證；實作下載後仍必須對本機實際 bytes 重新計算 SHA-256，遠端頁面資訊不得取代本機完整性檢查。

- 使用 `huggingface_hub.snapshot_download(repo_id=..., revision=...)` 取得固定 Snapshot，再將本機 Snapshot 路徑交給 `FlagReranker`；不得只把模型名稱傳給 `FlagReranker` 讓它追蹤 `main`。

- 模型載入前驗證 Snapshot resolved commit 與權重 SHA-256。Revision、權重檔缺失或雜湊不符時拋出 `RerankerIntegrityError`；正式問答與 Evaluation 都必須中止，不得降級。

- 輸入為 `[question.strip(), original_page_content]`，不得使用 BM25 正規化後的文字。
- Reranker 不得依賴 `FlagReranker` 或底層套件的隱含推論預設值。Pipeline Config 必須明列且結果 Manifest 必須記錄實際使用的 `device`、`dtype`／`use_fp16`、`batch_size`、`max_length` 與 `normalize`；上述任一值改變皆產生新的 `config_id`。
- `CURRENT_BASELINE` 與 `TARGET` 在同一 Pipeline Config 下必須使用完全相同的 Reranker inference parameters；兩者唯一允許不同的是候選輸入清單。
- `evaluation/config.hybrid-v1.json` 建立時必須把目前程式實際採用的上述值顯式寫入；缺欄位、使用 `auto` 後無法解析到單一實際值，或 Runtime 實際值與 Config 不一致時 Acceptance 中止。

- 使用正規化分數並由高至低排序。

- 每個輸入必須剛好得到一個有限數值。出現 `NaN`、正負無限、非數值，或輸出數量不等於候選數時，拋出 `RerankerOutputError`。

- 同分時保留輸入候選順序：Hybrid 為 RRF 順序；Dense-only 與 CURRENT_BASELINE 為 FAISS 順序。

- 正式問答最終只回傳 `TOP_K` 個 Chunk；Evaluation 必須保留並排序至 `EVALUATION_DEPTH`，不得先套用正式回答的 `TOP_K` 截斷。

## 7. 設定規格

新增以下環境設定：

```env

HYBRID_SEARCH_ENABLED=false

BM25_TOP_K=20

FUSION_TOP_K=30

RRF_K=60

BM25_K1=1.5

BM25_B=0.75

BM25_EPSILON=0.25

```

| 設定 | 預設值 | 驗證規則 | 說明 |

|---|---:|---|---|

| `HYBRID_SEARCH_ENABLED` | `false`（發布前） | 必須為合法布林值 | 是否啟用 BM25 與 RRF；依第 7.1 節才可改成預設 `true` |

| `BM25_TOP_K` | `20` | 必須大於 0 | BM25 候選數量 |

| `FUSION_TOP_K` | `30` | 必須大於或等於 `TOP_K` | RRF 後送入 Reranker 的最大候選數 |

| `RRF_K` | `60` | 必須大於 0 | RRF 排名平滑常數 |

| `BM25_K1` | `1.5` | 有限浮點數且大於 0 | `BM25Okapi.k1` |

| `BM25_B` | `0.75` | 有限浮點數且介於 0～1 | `BM25Okapi.b` |

| `BM25_EPSILON` | `0.25` | 有限浮點數且大於或等於 0 | `BM25Okapi.epsilon` |

既有設定保持：

```env

RETRIEVAL_TOP_K=20

TOP_K=8

RERANKER_ENABLED=true

RERANKER_REVISION=953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e

RERANKER_WEIGHTS_SHA256=d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286

```

- 正式回答依 `TOP_K` 設定運作，不固定只能取 8 筆。

- 本版本將 `Settings.top_k` 程式預設值由 4 統一改為 8，使未提供 `.env` 與使用 `.env.example` 時行為一致。

- Evaluation 設定檔另固定 `answer_top_k=8`，用於報告「預設正式回答」的命中表現；它不覆寫正式應用程式環境值。

- 正式應用程式以驗證後的 `BM25_K1`、`BM25_B`、`BM25_EPSILON` 建立 BM25 Store；任一值改變後，既有 Store 不得繼續使用，必須重新建庫。

- Evaluation 必須由 Pipeline Config 明確提供 BM25 三個參數；即使執行 Process 存在同名環境變數，也不得覆寫評測 Config。

其他驗證：

- `HYBRID_SEARCH_ENABLED=true` 時才驗證 `BM25_TOP_K > 0`、`RRF_K > 0`、BM25 三個浮點參數、`FUSION_TOP_K >= TOP_K` 及 `FUSION_TOP_K <= RETRIEVAL_TOP_K + BM25_TOP_K`。

- `HYBRID_SEARCH_ENABLED=false` 時，除開關本身外，不驗證、不建立也不載入 BM25／RRF；即使相關環境變數缺少或格式錯誤，也不得阻擋 Dense-only 啟動。

- Evaluation 啟用 Hybrid 比較時，額外要求 `RETRIEVAL_TOP_K >= EVALUATION_DEPTH`、`BM25_TOP_K >= EVALUATION_DEPTH`、`FUSION_TOP_K >= EVALUATION_DEPTH`。

- `EVALUATION_DEPTH=20` 只定義在版本控管的 Evaluation 設定檔，不是正式應用程式環境變數；正式 Streamlit 問答不得使用它取代 `TOP_K`。

- `HYBRID_SEARCH_ENABLED=false` 時，必須完全沿用既有 Dense＋Reranker 流程，Session State 中不建立 `bm25_store`。

- 本版本只支援透過 `.env` 在 Process 啟動時決定 Hybrid 開關，不提供執行中的 UI 動態切換。

- `false -> true` 與 `true -> false` 都必須重新啟動應用程式才能生效。

- 正式知識庫目前只存在 Streamlit Session State，沒有磁碟持久化；應用程式重新啟動後 FAISS、BM25、Chunk 與聊天狀態全部消失。因此任何方向的開關切換，在重啟後都必須重新上傳檔案並建立知識庫，不存在「重啟但保留原知識庫」的行為。

- 系統不得在第一次查詢時自動建立或補建 BM25 Index。若 Hybrid 已啟用但 Session State 缺少 `bm25_store`，視為知識庫狀態不完整，要求使用者重新建庫。

- 不得因 Hybrid Search 改變 `TOP_K` 的語意。

- Reranker 啟用時，revision 與權重 SHA-256 必須是 40／64 位小寫十六進位字串，並依第 6.5 節驗證實際 Snapshot。

### 7.1 Hybrid 發布預設政策

「預設」同時指 `src/rag/release_defaults.json` 內由 `Settings.hybrid_search_enabled` 讀取的值與 `.env.example`；兩者必須一致。使用者仍可明確覆寫 `.env` 進行開發實驗，但不得把手動覆寫描述成發布預設。

| Benchmark／Gate 狀態 | 發布預設 | 規則 |

|---|---|---|

| 尚未執行 Acceptance Benchmark | `false` | 沒有發布 Manifest，視為未驗證 |

| 執行錯誤、資料失配、非決定性或任一硬性 Gate 未通過 | `false` | 不得建立通過的發布 Manifest |

| 已通過所有硬性 Gate，且至少一個預先指定、未飽和品質指標嚴格改善 | `true` | 另開 Promotion commit，同步將程式與 `.env.example` 預設改為 `true` |

| `CURRENT_BASELINE` 的所有預先指定品質指標皆已達理論滿分，`TARGET` 也全部維持滿分 | `false` | 標記 `CEILING_NON_INFERIOR`；Hybrid 保留為 opt-in，待真實未飽和資料集證明收益 |

| 過去曾通過，但 Dataset／Config／模型／Pipeline fingerprint 不一致，或評測後出現不允許的變更 | `false` | 結果視為 stale，必須重新跑 Acceptance |

- Acceptance 結果與發布 Manifest 必須記錄 `evaluated_commit`，表示實際執行 Benchmark 時的完整 Git commit SHA；不得把後續 Promotion commit 冒充成受評測 commit。

- 預設改為 `true` 的 Promotion commit 必須引用 `evaluation/releases/hybrid-default.json` 中的 Acceptance Run ID，且 `evaluated_commit` 必須是 Promotion commit 的祖先。

- Hybrid 發布預設必須放在專用的 `src/rag/release_defaults.json`，該檔只允許包含版本與 `hybrid_search_enabled`；`Settings` 載入此值後仍允許明確環境變數覆寫。

- 從 `evaluated_commit` 到 Promotion commit，只允許變更 `src/rag/release_defaults.json` 的 Hybrid 布林值、`.env.example` 的相同預設、發布 Manifest、該次 Acceptance 結果，以及不影響執行的 README／規格文件。CI 必須驗證實際 Diff 內容，不得只以檔名作寬鬆 Allowlist。

- Promotion commit 不需要、也不得要求 Manifest 預先記錄包含 Manifest 自身的 commit SHA，以避免自我參照。可在 CI／Release metadata 另記實際 Promotion commit，但它不屬於 Acceptance 身分。

- 修改檢索程式、依賴鎖定、模型、Tokenizer、語料、Chunk／解析邏輯，或任何可能影響排名與耗時的設定時，既有 Acceptance 立即失效並必須重新執行。

- stale 判定以 `evaluated_commit`、Dataset／Config／模型識別、Pipeline fingerprint，以及 `evaluated_commit..HEAD` 是否僅含允許差異為準；不得只因目前 HEAD 與 `evaluated_commit` 不同就判定 stale。

- 若後續版本的 Acceptance 失敗或 Manifest stale，下一個 Release 必須恢復預設 `false`；已發布舊版不在執行時自動改寫使用者 `.env`。

- P95 100 ms 在參考硬體尚未固定前只是警示預算，因此單獨超標不把 `PASSED` 改成 `FAILED`，但 Promotion 說明必須揭露。

## 8. 程式結構

### 8.1 新增檔案

```text

src/rag/

├── bm25_store.py

├── chunk_identity.py

├── hybrid_retriever.py

├── release_defaults.json

└── retrieval_errors.py

```

#### `bm25_store.py`

負責：

- Query／Document 共用正規化。

- 中文與識別字斷詞。

- 建立 BM25 Index。

- 執行 BM25 Top-K 搜尋。

- 將排名結果對應回原始 `Document`。

建議介面：

```python

class BM25Store:

    @classmethod

    def from_documents(cls, documents: Sequence[Document]) -> "BM25Store": ...

    def search(self, question: str, top_k: int) -> list[RankedDocument]: ...



def tokenize_for_bm25(text: str) -> list[str]: ...

```

#### `chunk_identity.py`

負責來源 ID、標準位置、Chunk ID、ordinal 分組與 `ChunkRegistry` 一致性驗證；所有 Retriever 共用此模組，不得各自產生 ID。

#### `hybrid_retriever.py`

負責：

- 依 v1 固定順序先呼叫 Dense、再呼叫 BM25 Retriever；不得自行改成並行。

- 將結果轉為帶 Chunk ID 與 Rank 的統一結構。

- 執行 RRF、去重、穩定排序與候選截斷。

建議介面：

```python

@dataclass(frozen=True, slots=True)

class RankedDocument:

    chunk_id: str

    document: Document

    rank: int

    score: float | None = None



def reciprocal_rank_fusion(

    rankings: Sequence[Sequence[RankedDocument]],

    rrf_k: int,

    top_k: int,

) -> list[Document]: ...

```

#### `retrieval_errors.py`

集中定義第 11.3 節的穩定錯誤階層與 `error_code`，供正式查詢、Evaluation 與 UI 使用；不得在呼叫端以訊息字串推斷是否可降級。

#### `release_defaults.json`

只保存 Release 可 Promotion 的版本號與 `hybrid_search_enabled` 預設布林值。此檔不得包含 Top-K、BM25、RRF、模型或其他會影響排名／耗時的設定，避免 Promotion 改動被錯誤排除於 Pipeline fingerprint。

```json

{

  "schema_version": 1,

  "hybrid_search_enabled": false

}

```

### 8.2 修改檔案

| 檔案 | 修改內容 |

|---|---|

| `.gitattributes` | 固定 fingerprint 文字檔 LF、二進位語料不轉換 |

| `evaluation/environments/hybrid-v1.json` | 提交完整實際依賴環境 Manifest，路徑由 Pipeline Config 指定 |

| `requirements.txt` | 新增並固定 `rank-bm25==0.2.2`、`jieba==0.42.1` |

| `.env.example` | 新增 Hybrid Search 設定與中文說明 |

| `src/rag/tokenizer_userdict.txt` | 固定中文領域詞與 Tokenizer 測試輸出 |

| `src/rag/config.py` | 新增設定欄位、讀取與驗證 |

| `src/rag/document_loader.py` 或建庫協調層 | 為每個 Chunk 配置穩定 Chunk ID |

| `src/rag/evaluation_cache.py` | 將 Dataset、Tokenizer、BM25、模型與解析設定納入 Cache signature 驗證 |

| `src/rag/knowledge_state.py` | 原子提交 `bm25_store`，重建成功後替換舊索引 |

| `src/rag/rag_service.py` | 將第一階段檢索改由 Hybrid Retriever 協調 |

| `src/rag/reranker.py` | 固定模型 Snapshot、驗證權重雜湊及輸出數量／有限值 |

| `scripts/evaluate_retrieval.py` | 新增四個固定評測組別、20 深度排序、Fail-fast、分階段計時與差異報表 |

| `evaluation/dataset.hybrid-v1.json` | 新增固定 50 題、Category 與 Gold Targets |

| `evaluation/config.hybrid-v1.json` | 固定評測深度、模型 digest、解析與檢索設定 |

| `evaluation/fixtures/hybrid_identifiers.xlsx` | 新增無機密的精確識別字與混合查詢語料 |

| `README.md` | 更新架構、設定、流程及限制 |

## 9. Chunk ID 規格

每個來源與 Chunk 必須有穩定 ID，並寫入 `Document.metadata`。ID 不以顯示檔名作為主要身分，因此相同內容只改名時仍可得到相同 ID。

### 9.1 來源 ID

```text

source_content_sha256 = sha256(original_file_bytes)

source_id = sha256("source-v1\0" + source_type + "\0" + source_content_sha256)

```

規則：

- 檔名只保留在 `source_filename` 供顯示與篩選，不參與 `source_id`。

- 相同 bytes 改名後重新上傳，`source_id` 保持一致，來源顯示名稱更新。

- 同一批次中，Unicode NFKC＋`casefold()` 後同名的檔案一律拒絕，不論內容是否相同。

- 同一批次中，bytes 完全相同但檔名不同的檔案也一律拒絕，錯誤訊息列出兩個顯示檔名；不得重複索引或靜默去重。

- 檔案內容任一 byte 改變即產生新的 `source_id`，並視為新版本來源。

- PDF、圖片與 Excel 使用不同 `source_type`，即使 bytes 相同也不得共用 `source_id`。

### 9.2 標準位置

位置不得使用 UI 顯示字串，必須序列化為 UTF-8、鍵名排序、無多餘空白的 canonical JSON：

```json

{"chunk_ordinal":0,"content_type":"text","extraction_method":"native","page":1,"source_type":"pdf"}

```

各來源必要欄位：

| 來源 | 標準位置必要欄位 |

|---|---|

| PDF 文字／OCR／VLM | `source_type`、1-based `page`、`content_type`、`extraction_method`、該頁同類型的 0-based `chunk_ordinal` |

| 直接上傳圖片 | `source_type`、`content_type`、`extraction_method`、0-based `chunk_ordinal` |

| Excel | `source_type`、0-based `sheet_index`、原始 `sheet_name`、1-based `row_start`、1-based `row_end`、0-based `chunk_ordinal` |

固定列舉如下；Chunk ID v1 不接受表外字串：

| 欄位 | 合法值 |
|---|---|
| `source_type` | `pdf`、`image`、`excel` |
| `content_type` | `text`、`visual` |
| `extraction_method` | `native`、`ocr`、`vlm` |

合法組合固定為：

| `source_type` | `content_type` | `extraction_method` |
|---|---|---|
| `pdf` | `text` | `native` |
| `pdf` | `text` | `ocr` |
| `pdf` | `visual` | `vlm` |
| `image` | `text` | `ocr` |
| `image` | `visual` | `vlm` |
| `excel` | `text` | `native` |

- 不在上表的組合視為 `RetrievalInvariantError`；不得自行新增 `table`、`pdf_text`、`excel_native` 等同義字。
- 未來若新增新的來源、內容類型或解析方式，必須提高 Chunk ID schema 版本並更新 canonical location 測試。

- `row_start`、`row_end` 是該 Excel Row Packer Chunk 實際涵蓋的資料列；單列 oversized Chunk 兩者相同。

- 所有 ordinal 都在最終 Chunk 產生、空白 Chunk 移除後一次配置；後續 FAISS、BM25 或預覽排序不得重新編號。

#### 9.2.1 Chunk ordinal 分組鍵

| 來源 | 分組鍵 | 歸零與遞增規則 |

|---|---|---|

| PDF | `(source_id, page, content_type, extraction_method)` | 每個 PDF 頁面、內容類型與解析方式組合從 0 重新起算；依該組最終 Splitter 輸出順序遞增 |

| 直接上傳圖片 | `(source_id, content_type, extraction_method)` | 每個圖片檔及內容／解析類型從 0 重新起算；依最終輸出順序遞增 |

| Excel | `(source_id, sheet_index, sheet_name)` | 每個工作表從 0 重新起算；依 `row_start`、`row_end` 升冪及 Row Packer 輸出順序遞增，不因列範圍改變而在每個 Chunk 重新歸零 |

- PDF 的 `native`、`ocr`、`vlm` 屬於不同 `extraction_method`，即使在同一頁也各自從 0 起算。

- PDF 每一頁重新起算；不得跨頁延續 ordinal。

- Excel 每一工作表重新起算；同工作表第二個 Row Packer Chunk 的 ordinal 為 1，不因它具有新的 `row_start`／`row_end` 而回到 0。

- 工作表順序使用 Workbook 原始順序；`sheet_index` 與 `sheet_name` 都寫入 canonical location。

- 分組鍵、排序規則或解析輸出順序規則變動時，必須提高 Chunk ID schema 版本，例如 `chunk-v2`。

#### 9.2.2 全域 canonical Chunk 建庫順序

各來源內的 `chunk_ordinal` 依第 9.2.1 節配置完成、空白 Chunk 移除且 `chunk_id` 計算完成後，建庫協調層必須只建立一次全域 `canonical_chunk_sequence`：

```python
canonical_chunk_sequence = sorted(
    final_chunks,
    key=lambda doc: (
        doc.metadata["source_id"],
        doc.metadata["canonical_location_json"].encode("utf-8"),
        doc.metadata["chunk_id"],
    ),
)
```

排序契約：

1. 第一鍵為 64 位小寫十六進位 `source_id`，依 ASCII 字典序升冪。
2. 第二鍵為已依本節 canonical location 規則產生的 `canonical_location_json` **UTF-8 bytes**，依 unsigned byte lexicographic order 升冪；不得改用 `source_filename`、上傳順序或 Python object identity。
3. 第三鍵為 64 位小寫十六進位 `chunk_id`，依 ASCII 字典序升冪，作為完整 total-order tie-breaker。
4. 此全域排序只決定 Registry／Index insertion order，**不得重新配置 `chunk_ordinal`、修改 canonical location 或重新計算 Chunk ID**。
5. `ChunkRegistry` 必須依此序列插入；FAISS 建索引與 `BM25Store.from_documents()` 也必須接收此同一序列。不得由不同模組再次排序。
6. UI 預覽可使用自己的顯示排序，但顯示排序不得回寫或改變 `canonical_chunk_sequence`。
7. 對完全相同的來源 bytes、解析／Chunk 設定與 Pipeline Config，`canonical_chunk_sequence` 的 Chunk ID 序列必須跨 Process 完全一致；否則拋出 `RetrievalInvariantError`。

### 9.3 Chunk ID

```text

content_sha256 = sha256(original_page_content_utf8)

chunk_id = sha256(

  "chunk-v1\0" + source_id + "\0" + canonical_location_json + "\0" + content_sha256

)

```

要求：

- 相同來源 bytes、解析設定、位置與 Chunk 內容重新建庫時產生相同 ID。

- 同一來源內文字完全相同但位置不同時，因標準位置不同而得到不同 ID。

- 相同位置的文字改變時，因 `content_sha256` 不同而得到新 ID。

- Dense、BM25、RRF、Reranker 與 Evaluation 全程使用相同 ID。

- 不得以 Python `hash()` 建立 ID，避免不同 Process 結果不同。

- 建庫提交前必須驗證所有 `chunk_id` 唯一；發生碰撞或同 ID 對應不同內容時整批建庫失敗。

### 9.4 Chunk Registry 與跨檢索器一致性

建庫時依第 9.2.2 節的 `canonical_chunk_sequence` 建立唯一的 `ChunkRegistry: dict[str, Document]`；FAISS 與 BM25 必須接收同一序列並儲存／回傳 Chunk ID、Rank 與 Score。RRF 完成後一律從 Registry 取得提供給 Reranker 與 Context 的 canonical `Document`，不得合併兩份 Retriever 各自攜帶的 metadata。

Dense 與 BM25 出現相同 Chunk ID 時，必須對照 Registry 驗證：

| 類別 | 必須完全相同的欄位 |

|---|---|

| 內容 | `page_content` 的 Python 字串值、`content_sha256` |

| 來源 | `source_id`、`source_content_sha256`、`source_type`、目前知識庫的 `source_filename` |

| 類型 | `content_type`、`extraction_method` |

| PDF 位置 | `page`、`chunk_ordinal`；不適用欄位必須為 `None` |

| Excel 位置 | `sheet_index`、`sheet_name`、`row_start`、`row_end`、`chunk_ordinal`；不適用欄位必須為 `None` |

| Canonical | 完整 `canonical_location_json`、重新計算的 `chunk_id` |

- 以上任一欄位不一致、Retriever 回傳 Registry 不存在的 ID，或重新計算 ID 不符時，拋出 `RetrievalInvariantError` 並中止，不得降級。

- `source_filename` 不參與 ID 計算，但同一次知識庫內兩個 Retriever 的顯示檔名仍必須與 Registry 一致；改名後重建的新知識庫可保有相同 ID 與新的檔名。

- 非上述身分／引用 metadata 不從 Retriever 結果合併，一律使用 Registry 版本；需要新增為引用依據的欄位，必須先加入本表與一致性測試。

- 索引建立完成後、原子提交前，逐一驗證全部 Chunk；每次查詢另驗證實際返回的候選。任一步失敗皆視為 Fatal。

## 10. UI 與進度訊息

啟用 Hybrid Search 時，進度事件至少包含：

1. `dense_retrieve`：正在執行 FAISS Dense Retrieval。

2. `dense_retrieved`：Dense 搜尋完成並記錄有效候選數。

3. `sparse_retrieve`：正在執行 BM25 Keyword Retrieval。

4. `sparse_retrieved`：BM25 搜尋完成並記錄正分候選數。

5. `fusion`：正在使用 RRF 合併與去重候選。

6. `fused`：RRF 完成並記錄 Union 與截斷後數量。

7. `rerank`：正在使用既有 Reranker 精排。

8. `reranked`：Reranker 完成並記錄最終數量。

9. `context`：正在組合 Context。

10. `generate`：正在產生答案。

條件事件：

- Hybrid 關閉時，Dense 完成後發出一次 `hybrid_skipped`，不得發出 `sparse_*` 或 `fusion`／`fused`。

- Reranker 關閉時，在第一階段候選完成後發出一次 `rerank_skipped(reason="disabled")`，不得發出 `rerank`／`reranked`。

- Reranker 啟用且第一階段合法完成但沒有候選時，發出 `rerank_skipped(reason="no_candidates")`；不得呼叫 Reranker 或發出 `rerank`／`reranked`。

- Dense、BM25、Reranker 執行錯誤時分別發出 `dense_failed`、`sparse_failed`、`rerank_failed`；之後再依結果發出 `retrieval_degraded` 或 `retrieval_failed`。

- 任一元件查詢失敗但可依第 11 節降級時，發出 `retrieval_degraded`，內容只包含失敗元件、使用中的替代路徑及安全化原因。

完成檢索後，UI 應顯示：

- `dense_candidate_count`：Dense 回傳後，完成該排名內依 Chunk ID 去重的數量。

- `bm25_candidate_count`：確認分數皆為有限數值後，排除零分、負分並完成該排名內去重的數量；非有限值會使該檢索器失敗，不會被計數。

- `union_unique_count`：兩份可用排名跨檢索器合併去重後、套用 `FUSION_TOP_K` 前的數量。

- `fused_candidate_count`：RRF 排序後套用 `FUSION_TOP_K` 的數量。

- `reranker_input_count`：實際送入 Reranker 的數量。

- `reranker_output_count`：Reranker 成功驗證後輸出的排名數量。

- `final_chunk_count`：成功重排或降級後，套用正式 `TOP_K` 的數量。

所有數量都代表「實際結果」，不得顯示設定上限冒充回傳數量。`null` 與 `0` 的契約如下：

| 狀況 | 對應 Count | Status／事件 |

|---|---|---|

| 階段未執行，因功能停用 | `null` | `disabled`；發出對應 `*_skipped(reason="disabled")` |

| 階段未執行，因上游 Fatal 中止 | `null` | `not_run_upstream_failure` |

| 階段已執行但發生錯誤，沒有可信結果 | `null` | `error`；發出 `*_failed` |

| 階段成功執行且合法無候選 | `0` | `success_empty` |

| 階段成功執行且有候選 | 實際非負整數 | `success` |

Reranker 狀態必須依下列優先序判定，符合前一項後不得再套用後一項；每次查詢最多發出一次 `rerank_skipped`：

1. 上游 Fatal：`reranker_input_count=null`、`reranker_output_count=null`、`reranker_status="not_run_upstream_failure"`；只發出終止事件 `retrieval_failed`，不另發 `rerank_skipped`。

2. Reranker 停用：兩個 Count 皆為 `null`、`reranker_status="disabled"`；發出一次 `rerank_skipped(reason="disabled")`。

3. Reranker 啟用、上游成功但沒有候選：兩個 Count 皆為 `0`、`reranker_status="success_empty"`；發出一次 `rerank_skipped(reason="no_candidates")`。

4. 其餘狀況才正常呼叫 Reranker，並依成功或錯誤結果填值。

只要上游合法成功且沒有候選，`final_chunk_count=0`，不受 Reranker 啟用或停用影響；不得呼叫 LLM。

欄位特例：

- Hybrid 關閉：`bm25_candidate_count`、`union_unique_count`、`fused_candidate_count` 及三個 BM25 建庫統計皆為 `null`；`bm25_status="disabled"`。

- `EmptyBM25Store`：`bm25_candidate_count=0`、`bm25_status="empty_no_tokens"`，並正常發出 `sparse_retrieve`、`sparse_retrieved`；不得標記為錯誤。

- Hybrid 啟用但一條 Retriever 錯誤、另一條有候選而降級：失敗側 Count 為 `null`；`union_unique_count` 與 `fused_candidate_count` 使用成功側實際結果。

- 一條 Retriever 錯誤、另一條合法為 0 而中止：成功側 Count 為 `0`、失敗側為 `null`，未執行的 Fusion／Reranker／Final Count 皆為 `null`。

- 兩條 Retriever 都成功但皆為 0：`union_unique_count=0`、`fused_candidate_count=0`、`final_chunk_count=0`；Reranker Count、Status 與事件再依上述優先序決定。

- Reranker 停用：`reranker_input_count=null`、`reranker_output_count=null`、`reranker_status="disabled"`；`final_chunk_count` 取第一階段截斷後實際數量。

- Reranker 已呼叫但失敗：`reranker_input_count` 為實際嘗試數、`reranker_output_count=null`、`reranker_status="error"`；成功降級時 `final_chunk_count` 為 fallback 實際數量，Fatal 時為 `null`。

建庫完成資訊另顯示：

- `bm25_source_document_count`：BM25 Store 接收的總 Chunk 數。

- `bm25_searchable_document_count`：實際具有 Token、可參與 BM25 評分的 Chunk 數。

- `bm25_excluded_empty_token_count`：兩者差值。

- `bm25_status`：`ready` 或 `empty_no_tokens`。

- Hybrid 關閉時以上三個 BM25 建庫 Count 皆為 `null`，`bm25_status="disabled"`。

- `empty_no_tokens` 時必須顯示持續可見的建庫警告，不得只寫入 Log。

不得向一般使用者顯示內部 Exception、檔案絕對路徑或模型堆疊資訊。

## 11. 錯誤與一致性處理

- 新知識庫的 FAISS，或 Hybrid 啟用時的 BM25，任一建立失敗時整批建庫失敗。

- 建庫失敗時，保留舊 FAISS、舊 BM25、舊聊天與目前生效檔案。

- Query 為空字串時，沿用既有「請先輸入問題」錯誤。

- BM25 無有效 Token 或全部分數為 0 時，允許只以 Dense Ranking 進入 RRF。

- Dense 無結果但 BM25 有結果時，允許以 BM25 結果繼續。

- 兩者皆無結果時，回傳既有資訊不足訊息。

### 11.1 正式問答查詢失敗策略

Retriever 呼叫結果先分類為 `success_nonempty`、`success_empty` 或 `error`。`success_empty` 是合法結果；`error` 是元件未完成查詢。Hybrid 啟用時使用以下完整矩陣：

| Dense | BM25 | 行為 | UI |

|---|---|---|---|

| `success_nonempty` | `success_nonempty` | 正常執行雙路 RRF | 無警告 |

| `success_nonempty` | `success_empty` | 以 Dense 單路進入 RRF | 無查詢失敗警告；若 BM25 Store 為 `empty_no_tokens`，沿用建庫警告 |

| `success_empty` | `success_nonempty` | 以 BM25 單路進入 RRF | 無警告 |

| `success_empty` | `success_empty` | 不呼叫 Reranker／LLM，回傳既有資訊不足訊息 | 一般無結果提示 |

| `error` | `success_nonempty` | 以 BM25 單路進入 RRF，再繼續回答 | `retrieval_degraded`，指出 Dense 失敗 |

| `success_nonempty` | `error` | 以 Dense 單路進入 RRF，再繼續回答 | `retrieval_degraded`，指出 BM25 失敗 |

| `error` | `success_empty` | 中止；不可宣稱資訊不足，因 Dense 結果未知 | 安全化檢索失敗訊息 |

| `success_empty` | `error` | 中止；不可宣稱資訊不足，因 BM25 結果未知 | 安全化檢索失敗訊息 |

| `error` | `error` | 中止本次回答 | 安全化檢索失敗訊息 |

Hybrid 關閉時只看 Dense：`success_nonempty` 繼續、`success_empty` 回傳資訊不足、`error` 中止。不得建立或假設 BM25 結果。

Reranker 與不變量錯誤：

| 狀況 | 行為 |

|---|---|

| 第一階段有候選，Reranker 發生第 11.3 節定義的 Operational／Output 錯誤 | 退回 RRF 排名；Dense-only 模式退回 FAISS 排名，顯示 `retrieval_degraded` |

| 第一階段沒有候選 | 不呼叫 Reranker，依 Retriever 矩陣處理 |

| Chunk ID 碰撞、同 ID 不同內容、設定或資料結構錯誤 | 中止，不允許降級 |

- 降級只適用於單次正式查詢，不得修改環境設定或永久停用元件；下一次查詢仍應重新嘗試。

- 所有降級都必須在 UI 明確提示，不得靜默發生。

- 回傳 `RagResult` 時應附帶 `degraded_components: list[str]` 與安全化 `warnings: list[str]`，供 UI 與測試驗證。

### 11.2 Evaluation 失敗策略

- Evaluation 一律 Fail-fast，不使用任何降級結果計算指標。

- Dense、BM25、RRF 或 Reranker 任一必要元件發生錯誤時，該次評測整體失敗、Exit Code 非 0，且不得輸出看似完整的總指標。

- 合法空結果仍可計為 Miss；程式錯誤、模型錯誤與不變量錯誤不得計為一般 Miss。

- 此差異用來確保正式問答具可用性，同時確保 Benchmark 可重現且組別定義不被改變。

### 11.3 錯誤分類契約

只有明確屬於 `DegradableRetrievalError` 的錯誤可依第 11.1 節降級；未分類的 `Exception` 一律視為 Fatal，不得用廣泛的 `except Exception` 靜默降級。

| 類別／例外 | 典型原因 | 正式問答 | Evaluation |

|---|---|---|---|

| `UserInputError` | 空白 Query | 中止並要求修正輸入 | 中止 |

| `DenseRetrievalError` | Ollama Embedding 連線、逾時、模型執行失敗 | 僅在 BM25 有候選時降級 | 中止 |

| `BM25SearchError` | BM25 執行失敗、Score 為 `NaN`／無限值 | 僅在 Dense 有候選時降級 | 中止 |

| `RerankerOperationalError` | 網路逾時、相依套件暫時不可用、載入／記憶體／計算失敗 | 第一階段有候選時退回第一階段排名 | 中止 |

| `RerankerOutputError` | 非數值、非有限分數、分數數量與候選數不符 | 第一階段有候選時退回第一階段排名 | 中止 |

| `RerankerIntegrityError` | Revision 不符、固定檔案缺失、權重 SHA-256 不符 | 立即中止，不降級 | 中止 |

| `RetrievalInvariantError` | Chunk ID 碰撞、Registry 缺 ID、跨檢索器身分／位置／內容不一致 | 立即中止，不降級 | 中止 |

| `KnowledgeStateError` | Hybrid 已啟用但 BM25 Store 缺失、索引與 Registry 數量不符 | 立即中止並要求重建 | 中止 |

| `RetrievalConfigError` | 設定格式、範圍或互斥條件錯誤 | 啟動／建庫中止 | 中止 |

| 未預期 Exception | 程式錯誤或未分類狀況 | 立即中止，寫入內部 Log | 中止 |

穩定 `error_code` 固定如下；UI、測試、Evaluation Manifest 只能依 `error_code` 或 Exception type 判斷，不得解析訊息文字：

| Exception 類別 | `error_code` |
|---|---|
| `UserInputError` | `USER_INPUT_INVALID` |
| `DenseRetrievalError` | `DENSE_RETRIEVAL_FAILED` |
| `BM25SearchError` | `BM25_SEARCH_FAILED` |
| `RerankerOperationalError`（含既有 Operational 子類） | `RERANKER_OPERATIONAL_FAILED` |
| `RerankerOutputError` | `RERANKER_OUTPUT_INVALID` |
| `RerankerIntegrityError` | `RERANKER_INTEGRITY_FAILED` |
| `RetrievalInvariantError` | `RETRIEVAL_INVARIANT_VIOLATION` |
| `KnowledgeStateError` | `KNOWLEDGE_STATE_INVALID` |
| `RetrievalConfigError` | `RETRIEVAL_CONFIG_INVALID` |
| 未預期 Exception 的外層安全包裝 | `INTERNAL_RETRIEVAL_ERROR` |

- 子類若沒有在本規格另定專用 code，一律繼承上表父類 code；不得以不同訊息文字建立臨時 code。
- `error_code` 是機器契約；安全化使用者訊息可調整措辭，但不得改變分類語意。

- 既有 `RerankerDependencyError`、`RerankerDownloadError`、`RerankerLoadError`、`RerankerMemoryError`、`RerankerComputeError` 應改為 `RerankerOperationalError` 的子類；404／revision 不存在及權重驗證失敗則轉為 `RerankerIntegrityError`。

- Reranker 分數先完成「可轉 float、數量相等、全部有限」驗證後才能排序；驗證失敗不得回傳部分排序。

- 建庫期間發生的任何索引、Registry、Tokenizer 或模型完整性錯誤都屬 Fatal，維持原子替換；正式查詢只處理本節明列的 `DegradableRetrievalError`，包括符合第 11.1 節條件的 Operational 與 Output 錯誤。

- 每個錯誤物件必須包含穩定 `error_code`、安全化使用者訊息與可記錄的原始 cause；UI 不直接顯示 cause 或 Stack Trace。

## 12. Retrieval Evaluation

### 12.1 評測組別

所有組別使用相同解析結果、相同 Chunk ID 與同一份問題集：

1. `DENSE_RAW`：FAISS 原始排名，只作診斷比較。

2. `CURRENT_BASELINE`：Dense＋Reranker，代表本次改版前的正式流程，也是品質驗收 Baseline。

3. `HYBRID_RRF`：FAISS＋BM25＋RRF，不使用 Reranker。

4. `TARGET`：Hybrid＋RRF＋Reranker，代表改版目標正式流程。

`Dense Baseline` 一詞不得再單獨使用；文件、程式輸出及報告必須寫 `DENSE_RAW` 或 `CURRENT_BASELINE`。

### 12.2 指標

正式回答深度與評測深度分開：

- 正式回答：套用可設定的 `TOP_K`，預設只將最多 8 個 Chunk 送入 Context。

- Evaluation：固定 `EVALUATION_DEPTH=20`，在套用正式 `TOP_K` 前保留各組排序至第 20 名。

- `DENSE_RAW` 使用同一次 Dense Retrieval 的候選清單，保留前 `EVALUATION_DEPTH` 筆。

- `CURRENT_BASELINE` 對該次 Pipeline Config 實際取得、依 Chunk ID 去重後最多 `RETRIEVAL_TOP_K` 筆的完整 Dense 候選執行 Reranker，再保留前 `EVALUATION_DEPTH` 筆；不得固定只重排 Dense Top 20，也不得呼叫會先截斷成正式 `TOP_K` 的包裝函式。

- `HYBRID_RRF` 對融合結果保留前 `EVALUATION_DEPTH` 筆。

- `TARGET` 對 RRF 後實際取得、最多 `FUSION_TOP_K` 筆候選完整執行 Reranker，再保留前 `EVALUATION_DEPTH` 筆。

- 任一階段候選不足時保留實際數量，不得以零分或重複 Chunk 補滿。

- 每題報告必須記錄 `dense_candidate_count`、`baseline_reranker_input_count`、`fused_candidate_count` 與 `target_reranker_input_count`，以區分設定上限和實際重排範圍。

輸出指標：

- Hit Rate@1、@3、@5、@8、@20。

- `MRR@20`：第一個 Gold Chunk 位於 Rank 1～20 時記為 `1/rank`，20 名內未命中記為 0；不得輸出未標深度的 `MRR`。

- `HYBRID_RRF` 與 `TARGET` 相對 `CURRENT_BASELINE` 的 Delta。

- `CURRENT_BASELINE` 相對 `DENSE_RAW` 的 Reranker Delta，供診斷使用。

- 每題第一個正確 Chunk 的 Rank。

- Dense 命中、BM25 命中及融合後命中狀態。

Hit Rate@20 與 MRR@20 衡量的是「Retriever／Reranker 排名品質」，不是實際送入 LLM 的數量；正式回答使用設定的 `TOP_K`，其預設值為 8。

### 12.3 Golden Dataset 補強

資料集版本固定為 `hybrid-eval-v1`，共 50 題。語料、題目、Category、Gold Target 或 Gold 判定語意變更時必須建立新 Dataset Version；解析、模型或檢索設定變更只建立新的 Pipeline Config ID。兩者皆不得覆寫舊結果，完整政策見第 12.7 節。

固定語料：

| 語料 | 用途 | 固定方式 |

|---|---|---|

| `documents/evaluation/NIST.AI.100-1.pdf` | 語意改寫、正式術語 | 沿用下載腳本中的官方 URL 與 SHA-256 |

| `documents/evaluation/NIST.AI.600-1.pdf` | 語意改寫、正式術語 | 沿用下載腳本中的官方 URL 與 SHA-256 |

| `evaluation/fixtures/hybrid_identifiers.xlsx` | 欄位代號、產品編號、錯誤碼、API 路徑、日期、版本及混合查詢 | 以無機密合成資料建立並提交 Git；Manifest 固定 SHA-256 |

固定題型與數量：

| Category | 題數 | 主要語料 |

|---|---:|---|

| `semantic_paraphrase` | 20 | NIST PDF |

| `exact_term` | 10 | NIST PDF |

| `exact_identifier` | 10 | 合成 Excel |

| `mixed_semantic_exact` | 10 | 合成 Excel |

| 合計 | 50 | － |

- `exact_identifier` 10 題固定包含：欄位／產品代號 3 題、錯誤碼 2 題、API 路徑 2 題、日期／時間 2 題、版本號 1 題。

- `mixed_semantic_exact` 每題必須同時包含自然語言意圖與至少一個完整識別字。

- 題目存於版本控管的 `evaluation/dataset.hybrid-v1.json`。

- 固定參數存於 `evaluation/config.hybrid-v1.json`，至少包含 `evaluation_depth=20`、`answer_top_k=8`、模型名稱與 Ollama 模型 digest、Chunk 設定、解析設定、Dense/BM25/Fusion Top-K、RRF K、`rank-bm25` 版本與 `k1/b/epsilon`、Tokenizer 規則版本、Reranker revision 及權重 SHA-256。

- 執行結果必須記錄資料集版本、三份語料 SHA-256、設定檔 SHA-256、`evaluated_commit`、Pipeline fingerprint、Python 與重要套件版本；模型 digest 或語料雜湊不符時中止。

Golden Dataset 每題結構：

```json

{

  "id": "exact_identifier_001",

  "category": "exact_identifier",

  "question": "FU038 欄位代表什麼？",

  "gold_targets": [

    {

      "source_content_sha256": "<sha256>",

      "location": {"sheet_name": "Fields", "row_start": 2, "row_end": 2},

      "expected_text": "FU038"

    }

  ]

}

```

Gold Chunk 判定規則：

1. Retrieved Chunk 的來源內容 SHA-256 必須相同。

2. PDF／圖片的 `location` 使用欄位完全相等：Gold 提供的 `page`、`content_type` 或 `extraction_method` 必須與 Retrieved Chunk 相同；未提供欄位不參與判定。

3. Excel 的 `sheet_name` 必須完全相同；Gold 的 `row_start`／`row_end` 表示「答案實際所在列區間」，Retrieved Chunk 只要完整包含該區間即符合位置：`chunk.row_start <= gold.row_start` 且 `chunk.row_end >= gold.row_end`。不要求 Chunk 範圍與 Gold 範圍完全相等。

4. Excel 單列答案令 Gold `row_start == row_end`；跨列答案必須明列最小完整答案區間。Gold 不得省略 Excel 列範圍。

5. `expected_text` 必須以區分大小寫、未正規化的原始字串完整出現在 `Document.page_content`。

6. 一題可定義多個 `gold_targets`；命中任一 Target 即為 Hit。

7. 評測前執行 Preflight：每個 Target 必須依來源、位置包含規則與 `expected_text` 解析到且只解析到一個 Chunk。為 0 或多於 1 時，資料集無效並中止評測；不得把資料集錯誤計為 Miss。

8. Row Packer 參數改變後若同一答案列被不同大小的 Chunk 包含，只要 Preflight 仍唯一命中即可；這也是 Excel 採包含語意而非 Chunk 範圍完全相等的原因。

9. 舊 `evaluation/dataset.json` 保留供歷史比較，但不得與 `hybrid-eval-v1` 的結果混合或直接比較。

### 12.4 四組評測執行協定

索引、文件與模型在一次 Benchmark Process 內載入一次。四組不是各自重跑相同前置計算，而是對每一題、每一 Trial 依下列固定資料流產生：

1. Dense Retrieval 執行一次，結果同時供 `DENSE_RAW`、`CURRENT_BASELINE` 及兩個 Hybrid 組使用。

2. Dense 完成後才執行一次 BM25 Retrieval，結果同時供 `HYBRID_RRF` 與 `TARGET` 使用；v1 不得與 Dense 並行。

3. 對完整的實際 Dense 候選執行一次 Reranker，產生 `CURRENT_BASELINE`。

4. 對 Dense＋BM25 執行一次 RRF，結果同時產生 `HYBRID_RRF` 並作為 `TARGET` 的 Reranker 輸入。

5. 對融合候選執行一次 Reranker，產生 `TARGET`。

報表與比較順序固定為 `DENSE_RAW -> CURRENT_BASELINE -> HYBRID_RRF -> TARGET`。實際計算按上述依賴執行；不得為配合報表順序重複 Dense 或 BM25 搜尋。

執行模式固定記為 `retrieval_execution_mode="sequential_dense_then_bm25"`，並納入 Pipeline Config、結果 Manifest 與 cache signature。未來若改成並行，必須建立新的 Pipeline Config、提高本規格 Minor Version，重新執行完整品質與效能 Acceptance；不得沿用本版本的加總公式或 P95 結論。

暖機與樣本：

- 模型與索引完成載入後，先將固定 50 題完整執行 1 個不記錄的 Warm-up Trial；每題都跑完上述五個步驟，因此每組各有 50 個暖機結果。

- 暖機不得寫入品質或效能統計，也不得作為五次正式 Trial 之一。

- 正式執行 5 個 Measured Trial；每個 Trial 包含全部 50 題，因此每組共有 250 個 query-trial 結果。

- 洗牌單位是「完整問題」，不得拆散同一題的四組計算。Trial `i` 使用 `random.Random(20260908 + i)` 對 50 個固定 Question ID 洗牌，其中 `i=0..4`。

- 對每個 Question，先完成並保存四組排名，再處理下一題；四組必須使用同一次 Dense／BM25 結果。

快取規則：

- 五次 Trial 可共用已驗證的文件解析結果、Chunk Registry、FAISS Evaluation 磁碟索引、BM25 Store，以及已載入的 Embedding／Reranker 模型。

- Measured Trial 之間不得快取 Query Embedding、Dense／BM25 排名、RRF 結果或 Reranker 分數；每個 Trial 都必須重新執行這些查詢階段。

- 同一 Question、同一 Trial 內必須依前述資料流共用 Dense 與 BM25 階段結果，避免四組輸入不一致。

- Cache signature 或 Manifest 不符時必須重建索引；不得載入後忽略差異。

### 12.5 重複評測的品質聚合規則

- 每個 Trial 分別以 50 題計算各組 Hit Rate 與 MRR@20；品質指標全程使用精確有理數，不使用 Binary Floating Point 作 Gate 比較。

- Hit Rate 的每題貢獻固定為整數 `0` 或 `1`；`Hit Rate@K = Fraction(hit_count, question_count)`。

- MRR@20 的每題貢獻固定為 `Fraction(1, first_gold_rank)`，20 名內未命中為 `Fraction(0, 1)`；Trial MRR 為全部貢獻總和除以題數。

- 每題、每組建立 `ranking_signature = sha256(join(top_20_chunk_ids, "\0"))`；少於 20 筆時使用實際完整列表。

- 同一題、同一組的五個 `ranking_signature` 必須完全一致。分數可有浮點微差，但排名 ID 不得改變。

- 任一排名在五次 Trial 間不同時，整次 Benchmark 標記 `NON_DETERMINISTIC`，品質 Release Gate 失敗；仍可輸出每 Trial 指標、平均、最小與最大值供診斷，但不得選最佳一次或用平均值宣告通過。

- 通過 Determinism Gate 後，正式報告值以 `sum(trial_metrics, Fraction(0, 1)) / 5` 計算；因排名一致，聚合後的分子／分母化簡結果必須與每一 Trial 完全相同，不需要也不得使用浮點容差。若精確結果不同，視為 Aggregation bug 並中止。

- JSON 同時保存 `numerator`、`denominator` 與顯示用 `decimal`。`decimal` 由精確分數使用 Decimal `ROUND_HALF_EVEN` 四捨五入至小數點後 8 位並輸出為字串；所有 Gate、Delta 與相等判斷只使用分子／分母，不使用顯示字串。

- 品質 Gate 同時保存每 Trial 原始結果與聚合結果；不得只保存平均值。

### 12.6 效能量測

每一組額外輸出：

- Dense Search 耗時。

- BM25 Search 耗時。

- RRF 耗時。

- Reranker 耗時。

- 每題總 Retrieval 耗時。

- 全部題目的 P50、P95 Retrieval Latency。

v1 固定先 Dense、後 BM25 順序執行。每題、每 Trial 的四組總 Retrieval Duration 定義為：

```text

DENSE_RAW = dense_duration

CURRENT_BASELINE =

  dense_duration

  + baseline_reranker_duration

HYBRID_RRF =

  dense_duration

  + bm25_duration

  + rrf_duration

TARGET =

  dense_duration

  + bm25_duration

  + rrf_duration

  + target_reranker_duration

```

- 共用階段只執行一次並使用同一筆實測耗時；公式中的加總代表該組自身正式路徑，不包含為其他評測組額外執行的階段。

- `TARGET` 不得計入 `baseline_reranker_duration`，`CURRENT_BASELINE` 也不得計入 BM25、RRF 或 Target Reranker。

- 四組共享流程從頭到尾的整段經過時間只能另記為 `shared_flow_wall_clock_duration` 診斷欄位，不得作為任何單一組的 Retrieval Latency。

- 每組先產生自己的 250 筆逐題總耗時樣本，再分別計算 P50／P95；不得將各階段的 P50 或 P95 相加冒充該組總耗時百分位數。

- BM25＋RRF 額外耗時先對每筆計算 `bm25_duration + rrf_duration`，再用 250 筆額外耗時樣本計算 P50／P95。

量測方法：

- 使用 `time.perf_counter_ns()`，各階段以不重疊區間量測。

- 建庫、模型下載、模型載入與 LLM 回答不納入 Retrieval Latency。

- 問題 Embedding 與 FAISS 計入 Dense Search；BM25 正規化、斷詞與評分計入 BM25 Search；合併、去重、排序與截斷計入 RRF；Cross-Encoder 計入 Reranker。

- 暖機、五次 Trial、250 個樣本與洗牌順序完全沿用第 12.4 節，不得另跑一套不同順序的品質與效能評測。

- P50／P95 使用 nearest-rank：排序後取 `ceil(p * N)` 的 1-based 樣本。

- 報告 CPU、RAM、作業系統、Python、執行緒數、Ollama 版本及模型 digest。

- BM25＋RRF 額外 P95 明確排除 Dense、Reranker 與 LLM，並依上述逐筆加總後取百分位數。

- 「額外 P95 < 100 ms」在尚未固定參考硬體前是警示型效能預算，不是阻擋合併的硬性驗收；超標必須在報告標紅並建立效能改善事項。

- 固定參考硬體與 CI Runner 後，另以規格修訂把門檻升為硬性 Release Gate，不得在實作時自行更改門檻性質。

### 12.7 調參、版本與結果保存政策

版本識別分成三層：

| 層級 | 何時改變 | 識別方式 |

|---|---|---|

| Dataset Version | 語料 bytes、題目、Category、Gold Target 或判定語意改變 | 新增不可覆寫檔案，例如 `dataset.hybrid-v2.json` |

| Pipeline Config | Top-K、RRF K、BM25 參數／版本、Tokenizer、Chunk／解析、Embedding、Reranker revision、執行模式或其他會影響排名／耗時的值改變 | `config_id = sha256(canonical_config_json)` |

| Benchmark Run | 每次實際執行 | `run_id = UTC timestamp + evaluated_commit_short + config_id_prefix` |

`config_id` 與 `run_id` 的唯一計算契約：

- `canonical_config_json` = 將 Pipeline Config JSON 解析成 JSON Object、通過 Schema 驗證後，依 **RFC 8785 JCS** 序列化所得的 UTF-8 bytes；不得以檔案原始排版、Python `json.dumps(sort_keys=True)` 或自行定義格式代替。
- `config_id = sha256(canonical_config_json_utf8_bytes).hexdigest()`；結果固定為 64 位小寫十六進位。
- Pipeline Config 不得包含 timestamp、run ID、絕對 cache path 等每次執行會改變但不屬於 Pipeline 身分的欄位；這些值寫入 Run Manifest，不參與 `config_id`。
- `run_id` 固定格式為 `YYYYMMDDTHHMMSSffffffZ_<commit12>_<config12>`，時間使用 UTC、24 小時制與 6 位 microseconds；`commit12` 為 `evaluated_commit` 前 12 位，`config12` 為 `config_id` 前 12 位。
- 若生成的結果路徑已存在，維持既有規則中止，不得覆寫或自動追加隨機字尾。

- 修改 `RETRIEVAL_TOP_K`、`BM25_TOP_K`、`FUSION_TOP_K`、`RRF_K`、BM25 `k1/b/epsilon` 不必提高 Dataset Version，但一定產生新的 `config_id`。

- 修改預設正式參數或要將某組調參結果升為發布預設時，必須新增版本化設定檔，例如 `evaluation/config.hybrid-v2.json`，並將本規格 Minor Version 提高；不得覆寫 `config.hybrid-v1.json`。

- 修改語料、題目或 Gold 判定時必須提高 Dataset Version；新舊 Dataset 的絕對指標不得直接宣稱為改善 Delta。

- 結果保存至 `evaluation/results/<dataset_version>/<config_id>/<run_id>.json`；路徑已存在時中止，不得覆寫。

- 每份結果至少保存 Dataset／Config SHA-256、完整 canonical config、`evaluated_commit`、Pipeline fingerprint、五個 Trial 明細、聚合指標、排名 signature、各組實際重排輸入數、模型／套件版本、硬體資料及 Gate 結論。

- 調參實驗與正式驗收結果使用相同格式，但加上 `run_purpose: tuning|acceptance`。只有 `acceptance` 且完全通過第 14 節的結果可以寫入發布 Manifest。

- 發布 Manifest 固定為 `evaluation/releases/hybrid-default.json`，內容指向唯一的 Dataset Version、Config ID、Acceptance Run ID、`evaluated_commit`、Pipeline fingerprint、決策狀態與 `verified_at`。Manifest 不記錄也不要求預先知道包含自身的 Promotion commit SHA。

- Promotion 後的 stale 判斷依第 7.1 節檢查評測身分、Pipeline fingerprint、祖先關係及允許 Diff；目前 HEAD 單純不同於 `evaluated_commit` 不構成失效。

#### 12.7.1 Pipeline fingerprint 計算契約

Fingerprint Schema 固定為 `pipeline-fingerprint-v2`。產生器必須建立下列結構；所有雜湊均為原始 bytes 的 SHA-256 小寫十六進位字串：

```json

{

  "schema": "pipeline-fingerprint-v2",

  "files": {

    "relative/posix/path": "<sha256>"

  },

  "models": {

    "embedding": {"name": "<name>", "digest": "<digest>"},

    "generator": {"name": "<name>", "digest": "<digest>"},

    "reranker": {

      "repo_id": "BAAI/bge-reranker-v2-m3",

      "revision": "<40-char-commit>",

      "weights_sha256": "<sha256>"

    }

  },

  "runtime": {

    "python": "<major.minor.patch>",

    "rank_bm25": "0.2.2",

    "jieba": "0.42.1",

    "environment_manifest_sha256": "<sha256>",

    "installed_distributions_sha256": "<sha256>",

    "retrieval_execution_mode": "sequential_dense_then_bm25"

  }

}

```

`files` 必須恰好包含：

1. `git ls-files` 列出的全部 `src/**/*.py`。這是 Repository 內可被正式 RAG／Evaluation 執行路徑匯入的 Python 原始碼完整範圍，不只限於 `src/rag/`。

2. `scripts/evaluate_retrieval.py` 與 `evaluation/**/*.py` 中版本控管、會被 Acceptance 執行或匯入的 Python 檔案；Acceptance 不得匯入其他 Repository-local `.py`。

3. `src/rag/tokenizer_userdict.txt`、`requirements.txt`、`.gitattributes`，以及本次 Pipeline Config 指定且版本控管的依賴環境 Manifest。

4. 本次命令指定的 Dataset JSON 與 Pipeline Config JSON。

5. Dataset 明確引用的每一份 Fixture 與實際評測語料檔案，包括下載後的 PDF／Excel 原始 bytes。

計算規則：

- 所有路徑必須相對 Git repository root，使用 `/` 分隔，不得包含名稱恰為 `.` 或 `..` 的路徑片段、反斜線、絕對路徑或重複正規化後的鍵；檔名中的句點合法，例如 `config.hybrid-v1.json`；路徑必須是 UTF-8 可表示的普通檔案，Symbolic link 一律拒絕。

- 每個檔案直接讀取原始 bytes 計算 `sha256(file_bytes).hexdigest()`；不得換行正規化、文字解碼或使用 Git blob SHA 代替。

- 完整物件依 RFC 8785 JSON Canonicalization Scheme（JCS）序列化為 UTF-8；不得自行採用不同的 Key 排序、Unicode 轉義、數字格式或可選的 `/` 轉義，也不得加入 BOM、縮排、空白或結尾換行。本 Schema 的欄位值只允許 Object 與 String，以避免非有限數值或跨語言數字格式差異。

- `pipeline_fingerprint = sha256(jcs_canonical_json_utf8_bytes).hexdigest()`。
- Embedding 與 Generator 的 Ollama digest 必須由本次實際連線的 `OLLAMA_BASE_URL` 呼叫 `GET /api/tags` 取得；以 Config 中完整 model name（含 tag）做**字串完全相等**匹配。找不到、找到多筆或回應缺少 digest 時中止。
- Ollama digest 接受 API 回傳 `sha256:<64hex>` 或 `<64hex>`；Fingerprint 與 Manifest 一律 canonicalize 為去除 `sha256:` 前綴後的 **64 位小寫十六進位字串**。其他格式一律拒絕。
- Acceptance 不得從 README、模型名稱推測 digest，也不得只記錄 tag；Preflight 與 Postflight 都重新取得並要求一致。

- 任一必要檔案缺失、不是普通檔案、無法讀取、路徑不合法、模型 digest 缺失或 Dataset 引用未列入 `files` 時立即中止 Acceptance，不得跳過或使用空值。
- Acceptance 載入 Repository-local Python module 後，Preflight／Postflight 必須收集各 module 的 resolved `__file__`；任何位於 Repository root 內、但不在上述 fingerprint `files` 集合的 `.py` 被匯入時，立即中止為 `INVALID_IMPORT_SCOPE`。

- README、規格文件、結果檔、發布 Manifest、`.env.example` 與專用的 `src/rag/release_defaults.json` 固定排除；該專用檔不得包含 Hybrid 發布布林值以外的執行設定。

#### 12.7.2 Acceptance Worktree 契約

Acceptance Preflight 必須在載入索引或模型前執行：

1. 以 `git rev-parse HEAD` 取得 `evaluated_commit`，並要求它是完整 40 位 Commit SHA。

2. 使用 `git status --porcelain=v1 --untracked-files=all --ignored=matching` 同時檢查 Staged、Unstaged、Untracked 與 Ignored 項目。任何可能被 Evaluation 匯入、讀取或列入 fingerprint 的路徑都必須乾淨；不得因檔案在 `.gitignore` 中就略過。

3. Repository 內唯一允許的非 Commit 評測來源輸入，是 Dataset 明確引用且 SHA-256 與 Dataset 宣告一致的下載語料；這些檔案必須納入 `files`，不得以目錄 Allowlist 接受未宣告檔案。Repository 外模型、衍生快取與隔離依賴依第 12.7.3、12.7.5 節驗證，不視為額外語料。`evaluation/results/**` 只作輸出並排除於工作目錄判定。

4. 全部 Git-tracked fingerprint 檔案的工作目錄原始 bytes 必須與 `evaluated_commit` 對應 Git blob 原始內容一致，依第 12.7.4 節驗證；Fingerprint 範圍及 Python import／Evaluation 設定搜尋路徑內的未追蹤或被忽略程式、設定、字典、Fixture 一律中止。無法被本次 Evaluation 讀取的其他本機檔案不影響判定。

5. Preflight 必須輸出 Effective Pipeline Config；任何 `.env` 或環境變數造成的排名／耗時相關值若與本次 Pipeline Config 不同，立即中止。連線位置等非排名設定可由環境提供，但必須另行記錄且不得改變模型 digest 或演算法設定。

6. Preflight 通過後才計算並保存 Pipeline fingerprint；Benchmark 執行完成後重新執行相同 Worktree 檢查並重算 fingerprint。Postflight 出現新的作用範圍檔案或 fingerprint 不同時，整次 Run 標記為 `INVALID_WORKTREE_CHANGED`，不得產生通過 Manifest。

Benchmark 在 Repository 內只能將新結果寫入 `evaluation/results/**`；模型下載、衍生快取及暫存檔必須使用第 12.7.3 節宣告的外部目錄。Acceptance 不得修改 Dataset、Config、程式、依賴環境或 Fixture。

#### 12.7.3 Acceptance 快取與執行目錄

- Pipeline Config 明列快取政策版本 `acceptance-cache-v1`。啟動參數提供 Repository 外的 cache root 與暫存目錄，解析絕對路徑並記入報告；實體位置不參與 fingerprint，快取政策與內容識別必須參與。

- 模型 Snapshot、Ollama 模型儲存、解析快取與 FAISS 磁碟快取可使用不同外部目錄，均須在 Preflight 宣告用途。快取目錄不得加入 Python import 或設定搜尋路徑。

- 模型依既有 digest／revision／權重驗證契約使用；衍生快取驗證來源、解析設定、模型識別及 cache signature，失配時在外部目錄重建。載入後仍驗證完整 Registry、來源集合、數量與 ID，不得增加 Dataset 未宣告的文件。

- 冷快取與暖快取皆可執行 Acceptance；下載、解析、建庫與模型載入於正式 Trial 前完成，不計 Retrieval Latency。Worktree Preflight 先於上述動作執行。

- Python 必須在 Process 啟動時使用 `-B` 或等效的 `PYTHONDONTWRITEBYTECODE=1`，不得在 Repository 產生新 bytecode。既有作用範圍 bytecode 不得靜默忽略；使用無此類檔案的乾淨 checkout，檢查失敗只提示，不自動刪除。

- 外部衍生快取與暫存檔可更新；Postflight 驗證受評測來源、模型識別、依賴及 fingerprint，不要求外部 cache root 的全部 bytes 不變。

- 不放寬第 12.4 節 Query Embedding、排名及 Reranker 分數不得跨 Trial 快取的限制。

- 第 12.7.2 節對未追蹤程式的限制不包含按第 12.7.5 節驗證的隔離依賴環境；合法 site-packages 不視為未追蹤專案程式。

#### 12.7.4 Git bytes 與換行政策

- Repository 必須提交 `.gitattributes`，將 fingerprint 範圍文字檔固定為 LF；PDF／Excel 等二進位檔不得文字轉換。初始建置完成正規化並提交後才執行 Acceptance。

- 使用 `git show <evaluated_commit>:<relative_path>` 或等效 Git blob API 取得原始內容，以二進位方式與工作目錄 bytes 比較；不得經文字管線、換行轉換或重新編碼後才比較。

- Git status 乾淨只是必要條件，不能取代 bytes 比對；Git 物件 SHA 不能代替檔案內容 SHA-256。

- 因 CRLF 或 checkout filter 導致不同時中止，指出檔案並提示建立符合 `.gitattributes` 的 checkout；Acceptance 不自動改寫來源。

- `.gitattributes` 納入 fingerprint，修改後必須重跑 Acceptance。

#### 12.7.5 Acceptance 依賴環境契約

- Pipeline Config 指定版本控管的 `environment_manifest`，例如 `evaluation/environments/hybrid-v1.json`。實際環境清單須在 Acceptance 前建立並提交，不得以佔位值通過。

- Manifest Schema 為 `acceptance-environment-v1`，恰含 `schema`、`python`、`platform`、`distributions`。前三者為字串：`python` 為完整 major.minor.patch；`platform` 固定計算為 `f"{sys.platform}|{platform.machine().lower()}"`；`distributions` 為完整「套件名稱 → 精確版本字串」Object。
- `platform` 範例：Linux x86-64 為 `linux|x86_64`、Windows AMD64 為 `win32|amd64`、Apple Silicon macOS 為 `darwin|arm64`。不得使用 `platform.platform()` 等包含 Kernel build／版本文字的可變格式。

- 以 `importlib.metadata.distributions()` 取得隔離環境全部已安裝 distributions，名稱小寫並將連續 `-`、`_`、`.` 統一為單一 `-`。名稱碰撞、缺版本或 metadata 無法讀取時中止。

- 清單包含實際 FAISS distribution、FlagEmbedding、PyTorch、Transformers、NumPy、LangChain 相關套件、rank-bm25、jieba 及其餘全部已安裝 distributions，不只列直接依賴。

- 實際 Python 版本與 OS／架構必須符合 Manifest；實際套件清單與 Manifest 必須完全相等；缺少、多出或版本不同均中止。Preflight／Postflight 均驗證，Acceptance 不得安裝、更新或移除依賴。

- 使用 Repository 外的隔離 Python 環境，不繼承 user site-packages，不允許 editable install 或未宣告 PYTHONPATH；專案原始碼只從受評測 checkout 的明確路徑匯入。

- `installed_distributions_sha256` 是正規化清單 Object 經 RFC 8785 JCS 序列化後的 SHA-256；Manifest 原始 bytes SHA-256 記入 `environment_manifest_sha256`，兩者納入 fingerprint runtime。

- 報告保存完整實際清單、Python、OS／架構、Ollama 版本及可用的 PyTorch／CUDA／裝置資訊。Pipeline Config 固定 device、dtype、batch size、執行緒等運算設定，Effective Config 必須一致。

- 環境變更須提交新版本 Manifest、產生新 Config ID／fingerprint 並重跑 Acceptance，不因 requirements 未變就沿用結論。

- 本契約固定版本與執行設定，不宣稱同版本套件在所有平台的二進位 bytes 相同。

## 13. 測試規格

### 13.1 單元測試

`test_bm25_store.py`：

- 中文問題可以命中中文 Chunk。

- `FU038` 與 `fu038` 可以命中相同 Chunk。

- `欄位FU038代表` 能拆成中文 Token、完整識別字及子詞。

- API 路徑同時保留完整 Token、路徑段與 CamelCase 子詞。

- 錯誤碼、日期與版本號同時具有完整 Token 與規定子詞。

- BM25 正規化不得改變送往 Dense、Reranker 或 Context 的文字。

- 空白 Query 拒絕搜尋。

- 無 Token Query 與全部零分時回傳空結果。

- 零分與負分文件不補入候選，非有限分數拋出錯誤。

- 同分依 Chunk ID 穩定排序，Top-K 大於有效結果數時不補滿。

- 完整 Chunk 清單為空時拒絕建庫。

- 全部 Chunk 無 Token 時建立 `EmptyBM25Store`，搜尋回傳空結果並產生建庫警告。

- 部分無 Token Chunk 不加入 BM25 評分 Corpus，但保留來源與排除統計。

- 回傳的是原始 `Document` 與 metadata。

- 驗證實際安裝為 `rank-bm25==0.2.2`；預設 Config 令 `BM25Okapi` 收到 `k1=1.5`、`b=0.75`、`epsilon=0.25`，自訂 Config 也必須將各自實際值完整傳入。

- 識別字左／右 ASCII 邊界、同位置最長匹配、最大長度 overflow 與匹配優先序符合第 6.3.1 節。

- API request-target 含 query string 時，同時輸出完整 target、path、segment、parameter name/value，並排除 fragment；`/files/a%20b?name=x%20y` 必須整段匹配且不得 URL decode。

- Path 與 Query 的裸 `%`、不完整 `%2`、非十六進位 `%ZZ` 都使整個 request-target 候選不成立，不得退回合法前綴；單／雙引號都終止匹配。

- 一般英文、純數字、`TobeRepair`、`XMLHttpRequest`、全大寫縮寫符合固定 Token 契約。
- 重複 query parameter 例如 `/api/items?id=A-1&id=B-2` 必須依原文保留兩次 `id` Token，不得跨 pair 去重；`/api/items?id=id&id=A-1` 必須保留三個來自不同原文位置的 `id` Token（第一個 pair name、第一個 pair value、第二個 pair name）。

- 非 request-target 的單次識別字 expansion 可局部去重；request-target 不得把整個 target 當成去重作用域。相同識別字在不同原文位置出現時保留實際詞頻。

`test_hybrid_retriever.py`：

- v1 每題固定先執行 Dense、完成後才執行 BM25，不得並行或反轉順序。

- RRF 分數公式正確。

- 同一 Chunk 同時出現在兩份結果時只保留一次。

- 單一排名內重複 ID 只保留第一筆並重新編 Rank。

- 同 ID 對應不同內容時拋出 `RetrievalInvariantError`。

- 同時被 Dense 與 BM25 排在前面的 Chunk 排名提高。

- 單一 Retriever 無結果時仍可融合。

- 缺席 Retriever 的分數貢獻為 0，單路 RRF 保持原排名。

- 同分結果排序穩定。

- `FUSION_TOP_K` 截斷正確。

`test_config.py`：

- 新設定的預設值與環境變數讀取正確。

- Hybrid 開關的不合法布林值永遠被拒絕。

- Hybrid 啟用時，`BM25_TOP_K`、`FUSION_TOP_K`、`RRF_K` 與 `BM25_K1` 拒絕 0、負數、非有限值及格式錯誤。

- `BM25_B=0` 與 `BM25_EPSILON=0` 必須合法；`BM25_B` 拒絕小於 0、大於 1 或非有限值，`BM25_EPSILON` 拒絕小於 0 或非有限值。

- Hybrid 關閉時，不讀取或驗證 BM25、Fusion 與 RRF 環境值。

- `FUSION_TOP_K < TOP_K` 會被拒絕。

- `FUSION_TOP_K > RETRIEVAL_TOP_K + BM25_TOP_K` 會被拒絕。

- 發布前 `Settings` 與 `.env.example` 的 Hybrid 預設皆為 `false`。

- `Settings` 從 `release_defaults.json` 取得未覆寫預設；該檔出現未知欄位、缺少必要欄位或非布林值時啟動失敗。

- BM25 三個浮點參數及 Reranker revision／SHA 格式驗證正確。

- BM25 參數改變時既有 Store 失效並要求重建；沒有相符 Acceptance Manifest 的正式自訂值標記為 `custom_unverified`。

`test_chunk_identity.py`：

- PDF ordinal 依 page、content type、extraction method 分組並各自從 0 起算。
- `source_type`、`content_type`、`extraction_method` 僅接受第 9.2 節固定列舉與合法組合；未知值或非法組合拒絕。

- Excel ordinal 每個工作表從 0 起算，同工作表跨 Row Range 持續遞增。

- 空白 Chunk 移除後才配置 ordinal，FAISS／BM25／預覽不重新編號。

- `canonical_chunk_sequence` 嚴格依 `(source_id, canonical_location_json UTF-8 bytes, chunk_id)` 排序；不同檔案上傳順序、dict 插入順序或 `source_filename` 改名不得改變相同來源 bytes 的 canonical Chunk ID 序列。

- Chunk Registry、FAISS 與 BM25 必須接收完全相同的 canonical Chunk ID 序列；任何模組自行重排都使測試失敗。

- 相同 Chunk ID 的內容、來源、類型、標準位置及顯示檔名逐欄與 Registry 一致。

- Registry 缺 ID、任一必要欄位不同或重算 ID 不符時拋出 `RetrievalInvariantError`。

`test_reranker_integrity.py`：

- Snapshot 使用固定 revision，不得請求 `main`。

- `model.safetensors` SHA-256 正確時可載入；revision、檔案或 SHA 不符時拋出 `RerankerIntegrityError`。

- 非數值、`NaN`、無限值與輸出數量不符時拋出 `RerankerOutputError`，不得回傳部分結果。
- Reranker 的 device、dtype/use_fp16、batch_size、max_length、normalize 必須由 Pipeline Config 顯式提供並與 Runtime 實際值一致；Baseline／Target 使用相同值。

`test_evaluation_protocol.py`：

- 每個 Measured Trial 的 Dense 與 BM25 只各執行一次並供四組共用。

- `CURRENT_BASELINE` 重排完整實際 Dense 候選、`TARGET` 重排完整實際 Fusion 候選，最後才各自截斷至 `EVALUATION_DEPTH`；不足時不補滿。

- 完整 Warm-up 1 次、Measured Trial 5 次、每組 250 個結果，Seed 與問題洗牌順序固定。

- Measured Trial 之間不共用 Query Embedding、排名或 Reranker Score cache。

- 五次 ranking signature 不一致時標記 `NON_DETERMINISTIC` 且 Gate 失敗。

- Hit Rate 與 MRR@20 使用 Fraction 精確運算；JSON 保存化簡後分子／分母，Gate 與 Delta 不讀取顯示用 Decimal。

- Dataset／Config／Run ID 分層正確，既有結果路徑不得覆寫。

- Excel Gold row interval 採包含判定，且 Preflight 必須唯一命中。

- 四組逐題總耗時符合第 12.6 節公式；每組由自己的 250 筆總耗時算 P50／P95，不得相加各階段百分位數。

- Promotion 的 `evaluated_commit` 祖先關係、Pipeline fingerprint 與允許 Diff 判定正確；只有 HEAD 不同不得直接判 stale。

- Pipeline fingerprint 對相同輸入跨 Process 產生相同值；路徑分隔、Key 順序、原始 bytes、缺檔、Symlink、未宣告 Fixture 與模型 digest 缺失案例都符合第 12.7.1 節。
- `config_id` 使用 RFC 8785 JCS；不同 JSON 排版但相同 Config Object 產生相同 ID，欄位值改變則 ID 必須改變；`run_id` 嚴格符合固定 UTC microsecond 格式。
- Acceptance 實際 import 的 Repository-local Python 檔必須全部存在於 fingerprint files；逃逸檔案觸發 `INVALID_IMPORT_SCOPE`。
- Ollama `/api/tags` digest 取得、`sha256:` 前綴正規化、缺失／多筆／不一致案例皆依第 12.7.1 節處理。
- Environment Manifest 的 `platform` 使用固定 `sys.platform|machine` 格式，Preflight／Postflight 完全一致。

- Acceptance 在 Pipeline 作用範圍出現 Staged、Unstaged、未宣告 Untracked／Ignored、環境覆寫 Effective Config，或執行期間 fingerprint 改變時中止；已宣告且雜湊正確的下載語料與結果輸出依契約處理。

### 13.1.1 v1.6 補充測試

- Hybrid／Dense-only 同分均維持各自 Reranker 輸入順序。

- TIME_PATTERN 匹配 `09:30`、`23:59:59`，不接受無效小時／分鐘。

- 允許 `config.hybrid-v1.json`，拒絕 `.`、`..` 路徑片段。

- status 乾淨但 blob bytes 不符仍中止；不自動正規化 checkout。

- 合法外部模型、衍生快取與依賴不觸發未宣告語料錯誤；失配快取重建且不修改來源。

- Repository 未宣告程式／bytecode 拒絕；冷暖快取皆可通過 Worktree Postflight。

- 實際依賴缺少、多出、版本不符或正規化名稱碰撞時中止。

- Manifest、實際環境或 `.gitattributes` 改變會改變 fingerprint；Postflight 依賴變動不得產生通過結果。

### 13.2 整合測試

- PDF、圖片與 Excel Chunk 可以同時進入兩種索引。

- 建庫成功後 Session State 同時具有 FAISS 與 BM25。

- BM25 建立失敗時保留舊知識庫與舊 UI 狀態。
- 新知識庫成功時清除所有舊 KB-dependent/query-dependent Session State；失敗時任何舊 State 都不得被先行清除。

- 啟用 Hybrid 時執行 Dense、BM25、RRF 與 Reranker。

- 停用 Hybrid 時結果與既有 Dense 流程相容。

- 停用 Hybrid 時不建立 BM25，重新啟用後舊知識庫要求重建。

- 停用 Reranker 時直接採用 RRF Top-K。

- 停用 Hybrid 或 Reranker 時發出對應 `*_skipped` 事件且不發出被跳過階段事件。

- Dense 或 BM25 單路錯誤時有提示降級；兩路都錯時中止。

- Retriever 決策矩陣的 9 種 Dense／BM25 組合全部具獨立測試；特別驗證「一方 error、另一方 success_empty」必須中止而非回傳資訊不足。

- Reranker 錯誤時有提示退回第一階段排名。

- Reranker Integrity 錯誤不可降級；Output／Operational 錯誤可依第一階段候選降級。

- Evaluation 任一元件錯誤時 Fail-fast，不輸出總指標。

- 正式回答依 `TOP_K` 截斷（預設 8），但 Evaluation 可計算 Hit Rate@20 與 MRR@20。

- 來源檔名、PDF 頁碼、Excel 工作表及實際列號不因融合而遺失。

- UI 對 disabled、upstream failure、error、success empty 與 success 的 Count 分別使用第 10 節規定的 `null` 或數值。

- Reranker skip 嚴格套用第 10 節優先序：Fatal 不發 skip、停用優先於 no-candidate，且每題最多一次；BM25 停用時相關候選與建庫 Count 都是 `null`。

- Benchmark 狀態對應第 7.1 節的 Hybrid 發布預設，stale Manifest 不得啟用預設。

## 14. 驗收標準

### 14.1 功能驗收

- [ ] Hybrid Search 可由環境變數啟用或停用。

- [ ] BM25 Store 接收與 Dense 相同的完整 Chunk 集合與 Chunk ID；只有無 Token Chunk 可依第 6.2 節排除於 BM25 評分 Corpus。

- [ ] 中文、欄位代號、錯誤碼及 API 路徑可以正常檢索。

- [ ] RRF 正確融合、去重並穩定排序。

- [ ] Reranker 正確接收融合後候選。

- [ ] 最終 Context 不超過 `TOP_K` 個 Chunk。

- [ ] 來源 metadata 完整保留。

- [ ] 建庫保持原子替換與失敗保留機制。

- [ ] Dense-only 相容模式仍可運作。

- [ ] Hybrid 關閉時不建立或驗證 BM25／RRF，重新啟用時明確要求重建知識庫。

- [ ] 正式問答所有降級都有 UI 警告，Evaluation 不使用降級結果。

- [ ] 正式回答使用可設定的 `TOP_K`（程式與範例預設皆為 8），Evaluation 使用固定 `EVALUATION_DEPTH=20`。

- [ ] 候選計數符合第 10 節定義，停用階段發出正確的跳過事件。

- [ ] Hybrid 發布預設符合第 7.1 節，沒有有效 Acceptance Manifest 時保持 `false`。

- [ ] 識別字文法、一般 Token、CamelCase、query string 與局部去重通過固定 I/O 測試；Path／Query 混合百分比編碼與非法 `%` 的整段拒絕符合第 6.3.1 節。

- [ ] `rank-bm25==0.2.2` 被鎖定；BM25 實際參數與本次 Runtime／Pipeline Config 完全一致並被記錄，初始 Config 預設為 `k1=1.5`、`b=0.75`、`epsilon=0.25`。

- [ ] PDF／圖片／Excel ordinal 依第 9.2.1 節分組且結果可重現。

- [ ] Excel Gold 列範圍使用完整包含語意並通過唯一命中 Preflight。

- [ ] 四組評測共用同 Trial 的 Dense／BM25 結果，完成 1 次暖機與 5 次正式 Trial。

- [ ] 五次排名 Determinism Gate 通過；結果依 Dataset／Config／Run 分層且不可覆寫。

- [ ] 錯誤型別、可降級範圍與 Reranker 非有限／數量錯誤符合第 11.3 節。

- [ ] 跨檢索器相同 Chunk ID 的所有必要內容、來源、類型與位置欄位驗證一致。

- [ ] Reranker 使用固定 revision 與權重 SHA-256，完整性失敗時中止。

- [ ] Acceptance 與 Promotion 以 `evaluated_commit`、Pipeline fingerprint、祖先關係及允許 Diff 判定，不因合法 Promotion commit 立即 stale。

- [ ] v1 的 Dense／BM25 固定順序執行；四組 P50／P95 由各自逐題總耗時樣本計算。

- [ ] Pipeline fingerprint 完全符合 `pipeline-fingerprint-v2` Schema，相同輸入跨 Process 產生相同 SHA-256，必要檔案或模型識別缺失時中止。

- [ ] Acceptance Preflight／Postflight 通過，實際執行內容與 `evaluated_commit` 及保存的 fingerprint 一致。

- [ ] Hit Rate 與 MRR@20 使用精確分數進行聚合、Delta 及 Gate 比較；顯示用 Decimal 不參與判定。

- [ ] 外部快取／bytecode／隔離依賴符合第 12.7.3 節，冷暖快取均不修改受評測來源。

- [ ] `.gitattributes` 與 blob bytes 比對符合第 12.7.4 節。

- [ ] 完整實際依賴符合版本化 Manifest，Preflight／Postflight 均通過。

- [ ] v1.6 同分、Regex 與路徑邊界補充測試通過。
- [ ] v1.6.1 Session State 成功／失敗 Transaction、固定 Enum、固定 error_code 與重複 query parameter 詞頻契約通過。
- [ ] `config_id` 使用 RFC 8785 JCS、`run_id` 使用固定 UTC microsecond 格式。
- [ ] Fingerprint 涵蓋全部 `src/**/*.py` 與實際 Acceptance import scope；不存在 Repository-local import escape。
- [ ] Reranker inference parameters、Ollama model digest 與 Acceptance platform canonicalization 均與 Pipeline Config／Manifest 一致。

### 14.2 品質驗收

以 `hybrid-eval-v1`、固定語料及固定設定比較。`CURRENT_BASELINE` 明確代表改版前的 Dense＋Reranker；`DENSE_RAW` 只供診斷，不是 Release Baseline。

以下為硬性品質 Release Gate，必須全部成立：

1. `TARGET` 整體 `MRR@20 >= CURRENT_BASELINE MRR@20`。

2. `TARGET` 整體 `Hit Rate@8 >= CURRENT_BASELINE Hit Rate@8`。

3. `TARGET` 在 `semantic_paraphrase` 子集的 Hit Rate@8，不得比 `CURRENT_BASELINE` 少超過 1 題。

4. `exact_identifier` 子集使用下列 ceiling-aware 規則：

   - 若 `CURRENT_BASELINE Hit Rate@5 < 100%`，`TARGET` 至少多命中 1 題。

   - 若 `CURRENT_BASELINE Hit Rate@5 = 100%`，`TARGET Hit Rate@5` 必須維持 100%，且 `TARGET exact_identifier MRR@20 >= CURRENT_BASELINE`；本子集不再要求不可能的 Hit Rate 提升。

5. 除維持上述非劣條件外，`TARGET` 必須在下列預先指定指標至少一項嚴格優於 `CURRENT_BASELINE`：整體 MRR@20、整體 Hit Rate@8、`exact_identifier` MRR@20、`mixed_semantic_exact` Hit Rate@5。

6. Evaluation 全程沒有降級、資料集錯誤或必要元件錯誤。

7. 五次 Trial 的所有 ranking signature 完全一致，未出現 `NON_DETERMINISTIC`。

8. 本次 Run 的 `run_purpose` 為 `acceptance`，且 Dataset、Config、模型、`evaluated_commit` 與 Pipeline fingerprint 均能寫入有效發布 Manifest。

9. Acceptance Worktree Preflight／Postflight 通過，且品質指標的精確分數資料完整。

若第 5 點所有候選指標在 `CURRENT_BASELINE` 都已達理論滿分，則改為要求 `TARGET` 全部維持滿分；此時規格判定為「品質非劣但無額外可證明收益」，Hybrid 可以保留為選配，但不得只因 Benchmark 滿分就改成預設啟用。是否預設啟用需另以真實使用資料建立未飽和資料集後決定。

判定範例：

- Baseline 精確識別字由 9/10 提升為 TARGET 10/10，**只能證明第 4 條的 exact_identifier Gate 通過**；仍必須另外滿足第 1～3、6～9 條，且第 5 條四個預先指定指標中至少一項嚴格改善，才可判定：**通過**。不得僅因多命中 1 題就宣告整體 Acceptance 通過。

- Baseline 精確識別字已為 10/10，TARGET 維持 10/10、該子集 MRR@20 非劣，且混合查詢 Hit Rate@5 提升：**通過**。

- Baseline 精確識別字已為 10/10，TARGET 維持 10/10，但所有未飽和的預先指定指標都沒有提升：**不符合預設啟用條件**。

- 精確識別字提升但整體 MRR@20 或 Hit Rate@8 下降：**不通過**。

若未通過，保留功能開關並調整 Tokenizer、候選數或 RRF 參數；不得以少數人工案例取代固定 Benchmark。

### 14.3 效能驗收

以 `hybrid-eval-v1` 固定資料集，在相同機器與模型狀態下：

- BM25＋RRF 額外 P95 Latency 目標小於 100 ms，不包含 Dense、Reranker 與 LLM；依第 12.6 節量測。

- 100 ms 在參考硬體尚未固定前是警示型預算，不是硬性 Release Gate；超標不得省略或視為通過，必須明確列入報告與後續事項。

- 建庫後 `source_document_count` 必須等於總 Chunk 數，`searchable_document_count` 必須等於斷詞後非空的 Chunk 數；兩者可不同。

- 不得因 Hybrid Search 重複呼叫 Embedding 模型。

- 同一題、同一 Trial、同一評測組的一次 Reranker 呼叫內，不得包含重複 Chunk ID。`CURRENT_BASELINE` 與 `TARGET` 可各自處理相同 Chunk；不同 Trial 必須依第 12.4 節重新計算。

- Dense、BM25 固定順序執行，各組總耗時與 BM25＋RRF 額外 P95 必須依第 12.6 節逐筆計算；不得使用共享流程整段耗時或相加階段 P95。

## 15. 實作順序

0. 先建立固定 Enum、Session State Transaction helper、穩定 error_code、Config/JCS 與 Acceptance import-scope 基礎契約。

1. 新增 Chunk Registry、Chunk ID、ordinal 與跨檢索器一致性測試。

2. 新增固定文法、正規化、中文／一般 Tokenizer 與 I/O 測試。

3. 新增鎖定套件版本、支援版本化預設／自訂參數的 BM25 Store 與合法 Empty Store。

4. 新增 RRF 與 Hybrid Retriever。

5. 新增 Reranker revision／權重驗證與錯誤分類。

6. 擴充設定、發布預設政策與 `.env.example`。

7. 整合建庫原子提交與 Session State。

8. 整合正式問答失敗矩陣、UI Count／Status 及進度事件。

9. 建立固定 Evaluation 語料、Gold 包含語意與 Preflight。

10. 實作四組共享執行、五次 Trial、Determinism Gate、版本與結果保存。

11. 執行單元測試、整合測試與 `run_purpose=tuning` Benchmark。

12. 參數定案後建立新 Pipeline Config，執行 `run_purpose=acceptance` Benchmark。

13. 依第 7.1 節決定是否建立發布 Manifest 與 Promotion commit。

14. 更新 README、架構與限制說明。

## 16. 預設決策摘要

| 決策 | 本版本選擇 |

|---|---|

| 是否替換 FAISS | 否 |

| Dense 模型 | 沿用 BGE-M3 |

| Hybrid 發布預設 | Benchmark 未執行／失敗／stale／全滿分無收益時為 `false`；通過且有未飽和指標改善才 Promotion 為 `true` |

| Sparse 演算法 | `rank-bm25==0.2.2` 的 BM25Okapi；初始預設 `k1=1.5`、`b=0.75`、`epsilon=0.25`，實際值由 Runtime／Pipeline Config 決定 |

| 中文斷詞 | `jieba==0.42.1`＋固定字典＋識別字文法 |

| 排名融合 | RRF |

| Reranker | `BAAI/bge-reranker-v2-m3`，revision `953dc6f6...`，權重 SHA-256 `d9e3e081...` |

| Dense 候選數 | 20 |

| BM25 候選數 | 20 |

| 融合候選數 | 30 |

| 最終 Context Chunk 數 | 依 `TOP_K`，程式與 `.env.example` 預設皆為 8 |

| Evaluation 排名深度 | 固定 20，MRR 明確為 MRR@20 |

| Evaluation 執行 | 1 個 50 題 Warm-up＋5 個 50 題 Trial；同 Trial 四組共用 Dense／BM25 結果 |

| Dense／BM25 執行模式 | v1 固定先 Dense、後 BM25 順序執行；變更模式須建立新 Config 並重跑 Acceptance |

| Evaluation 總耗時 | 四組依各自階段逐題加總，再以各自 250 筆樣本計算 P50／P95 |

| 品質聚合 | 五次 Top-20 排名必須一致；Hit Rate／MRR 以 Fraction 精確聚合與比較，顯示 Decimal 不參與 Gate |

| 品質 Baseline | `CURRENT_BASELINE`（Dense＋Reranker） |

| 固定資料集 | `hybrid-eval-v1`，3 份語料、50 題 |

| Hybrid 關閉 | 不建立／驗證 BM25；重新啟用後需重建知識庫 |

| 正式查詢失敗 | 單路或 Reranker 可見降級；兩路失敗或不變量錯誤則中止 |

| 可降級例外 | 僅 `DegradableRetrievalError`；Integrity、Invariant、State、Config 與未知例外中止 |

| Evaluation 失敗 | Fail-fast，不以降級結果計分 |

| BM25 非正分結果 | 排除且不補滿 |

| Query 正規化 | 只套用 BM25；Dense 與 Reranker 維持原文 `strip()` |

| Excel Gold 列位置 | Gold 答案列區間須被 Retrieved Chunk 列範圍完整包含，不要求完全相等 |

| 結果版本 | Dataset Version＋Pipeline Config SHA-256＋不可覆寫 Run ID＋`evaluated_commit`／Pipeline fingerprint |

| Fingerprint | 固定 `pipeline-fingerprint-v2` Schema、相對 POSIX 路徑、原始 bytes SHA-256 與 RFC 8785 JCS |

| Acceptance Worktree | Pipeline／Import／Evaluation 設定作用範圍必須乾淨；執行前後 fingerprint 必須一致 |

| UI Count | 未執行／失敗為 `null`；成功但無候選為 `0` |

| 向量索引類型 | 沿用目前 FAISS 預設 |

| 正式索引持久化 | 本版本不處理 |

## 17. v1.1 缺口關閉對照

| # | 缺口 | v1.1 決策 | 規格位置 |

|---:|---|---|---|

| 1 | 評測深度矛盾 | 正式回答依 `TOP_K`（預設 8）；Evaluation 保留 Top 20，指標命名為 MRR@20 | 5.2、6.5、12.2 |

| 2 | Hybrid 關閉行為 | 不建立、不載入、不驗證 BM25／RRF；重新啟用後必須重建 | 5.1、7 |

| 3 | 查詢失敗策略 | 正式查詢允許可見的單路／Reranker 降級；Evaluation Fail-fast | 11 |

| 4 | Chunk ID 定義不足 | 來源 bytes 雜湊＋來源類型＋標準位置＋內容雜湊；改名穩定、重複內容拒絕 | 9 |

| 5 | 評測資料未固定 | `hybrid-eval-v1`、三份固定語料、50 題、固定設定與 Gold Target | 12.3 |

| 6 | 品質驗收歧義 | `CURRENT_BASELINE` 為唯一 Release Baseline；整體持平且精確子集達標可通過 | 12.1、14.2 |

| 7 | BM25 邊界 | 只收有限正分、不補滿；非有限值報錯；同分按 ID；零 Chunk 拒絕（全部無 Token 行為由 v1.2 第 18.6 項取代） | 6.2 |

| 8 | 斷詞細節 | 完整識別字＋子詞；先抽識別字，再處理相連中文與標點 | 6.3 |

| 9 | 正規化範圍 | 只套用 BM25；Dense、Reranker 與 Gold 判定維持原文 | 6.3、6.5 |

| 10 | RRF 排序細節 | 缺席貢獻 0；單路保持排名；單一列表先去重；不一致 ID 中止 | 6.4 |

| 11 | UI 與效能 | 明訂每個計數時點、跳過／降級事件、250 樣本 P95 與警示型 100 ms 預算 | 10、12.6、14.3 |

## 18. v1.2 缺口關閉對照

| # | 缺口 | v1.2 決策 | 規格位置 |

|---:|---|---|---|

| 1 | Baseline 滿分無法提升 | 改用 ceiling-aware Gate；滿分時維持滿分並檢查 MRR，預設啟用仍需至少一個未飽和指標改善 | 14.2 |

| 2 | 正式回答是否固定 8 | `TOP_K` 可設定，程式與 `.env.example` 預設統一為 8；Evaluation 固定 `answer_top_k=8` | 5.2、7、12.2 |

| 3 | 重啟後知識庫生命週期 | 目前無持久化，任何方向切換重啟後都必須重新上傳並建庫 | 7 |

| 4 | 單路失敗與零結果交叉狀況 | 只有倖存路徑有候選才降級；一方 error、另一方 empty 必須中止 | 11.1 |

| 5 | Tokenizer 缺少確切案例 | 固定 jieba 版本、字典、掃描優先序及 6 組完整 I/O Token 契約 | 6.3 |

| 6 | 全部文件沒有 Token | 建立合法 `EmptyBM25Store`、搜尋回空、建庫成功但持續警告；零 Chunk 仍拒絕 | 6.2、10、13.1 |

## 19. v1.3 缺口關閉對照

| # | 缺口 | v1.3 決策 | 規格位置 |

|---:|---|---|---|

| 1 | Hybrid 發布預設政策 | 未執行、失敗、stale 與全滿分無收益皆預設關閉；通過且有未飽和指標改善才 Promotion 開啟 | 7.1 |

| 2 | 識別字完整匹配文法 | 固定 ASCII 文法、邊界、最長匹配、優先序、長度上限與 query string／fragment 行為 | 6.3.1 |

| 3 | Tokenizer 邊界規則 | 固定一般英文、純數字、CamelCase／縮寫與單次匹配局部去重規則 | 6.3.2 |

| 4 | BM25 實作與參數 | v1.3 鎖定 `rank-bm25==0.2.2`、BM25Okapi 與初始三個數值；v1.4 進一步澄清數值是版本化預設 | 6.2、20 |

| 5 | Chunk ordinal 分組鍵 | PDF 按頁／類型／解析方式；圖片按檔案／類型；Excel 按工作表，皆明訂歸零與順序 | 9.2.1 |

| 6 | Excel Gold 位置 | Gold 答案列區間須被 Chunk 完整包含，不要求範圍完全相等 | 12.3 |

| 7 | 四組評測執行 | 四組共用同 Trial 的 Dense／BM25；1 次完整暖機、5 次 Trial、固定 seed 與問題級洗牌 | 12.4 |

| 8 | 重複評測品質聚合 | Top-20 ranking signature 五次必須一致；否則非決定性失敗，通過後採算術平均 | 12.5 |

| 9 | 錯誤分類 | 只有列舉的 Degradable 錯誤可降級；Reranker 非有限／數量不符為 Output Error | 11.3 |

| 10 | 跨檢索器一致性 | 以 Chunk Registry 驗證內容、來源、類型、位置、檔名及重算 ID | 9.4 |

| 11 | Reranker 模型版本 | 鎖定官方 commit revision 與 `model.safetensors` SHA-256；不符為 Integrity Fatal | 6.5 |

| 12 | 調參與評測版本 | Dataset Version、Config SHA-256、Run ID 三層識別；結果與版本檔不可覆寫 | 12.7 |

| 13 | UI 失敗與跳過 | 未執行／失敗 Count=`null`、成功空結果=`0`；補齊 no-candidate skip 與 BM25 disabled 欄位 | 10 |

## 20. v1.4 缺口關閉對照

| # | 缺口 | v1.4 決策 | 規格位置 |

|---:|---|---|---|

| 1 | Promotion 後 Manifest 立即 stale | Manifest 記錄 `evaluated_commit`；Promotion 要求祖先關係、相同 fingerprint 與允許 Diff，不要求自我 commit SHA | 7.1、12.7 |

| 2 | Tokenizer 順序與引號衝突 | 同位置最長匹配、同長才看優先序；單／雙引號終止 API target，百分比編碼必須完整 | 6.3.1、6.3.2、13.1 |

| 3 | BM25 固定值與可調設定衝突 | 套件版本鎖定，數值為版本化預設；Runtime／Evaluation 各使用明確設定並記錄實際值 | 6.2、7、12.7、14.1 |

| 4 | Reranker disabled／no-candidate 衝突 | 固定 Fatal、disabled、enabled-empty、execute 優先序；每題最多一次 skip | 10 |

| 5 | Baseline 重排範圍不一致 | Baseline 重排完整實際 Dense 候選，Target 重排完整實際 Fusion 候選，最後才保留 Top 20 | 12.2、12.4 |

| 6 | 共用計算後的總耗時未定義 | v1 固定 Dense 後 BM25；四組以自身階段逐題加總，再由各自 250 筆樣本計算 P50／P95 | 8.1、12.4、12.6、14.3 |

| 7 | 「抽查全部」矛盾 | 提交前逐一驗證全部 Chunk，查詢時驗證實際候選 | 9.4 |

| 8 | Reranker 重複限制範圍不明 | 去重限制在同題、同 Trial、同組的單次呼叫；Baseline／Target 與不同 Trial 可重算 | 14.3 |

| 9 | Reranker 身分待查證 | 已記錄官方查證日期與來源；下載後仍驗證本機實際檔案 SHA-256 | 6.5、13.1 |

## 21. v1.5 缺口關閉對照

| # | 缺口 | v1.5 決策 | 規格位置 |

|---:|---|---|---|

| 1 | API Segment 與 `%` 驗證歧義 | 使用獨立 Regex；Segment 可混合一般字元／`%HH`，Path 與 Query 都要求完整候選 `fullmatch()` | 6.3.1、13.1 |

| 2 | Fingerprint 無唯一算法 | 固定 Schema、檔案集合、相對 POSIX 路徑、原始 bytes SHA-256、RFC 8785 JCS 與 Fatal 條件 | 12.7.1 |

| 3 | Acceptance 工作目錄可能不一致 | 執行前檢查 `evaluated_commit`、Staged／Unstaged／Untracked，執行後複驗 fingerprint | 12.7.2、13.1、14.1 |

| 4 | Reranker Output 降級文字衝突 | 正式查詢只降級本節明列的 `DegradableRetrievalError`，包含符合條件的 Operational／Output Error | 11.3 |

| 5 | Config 零值測試衝突 | Top-K／RRF K／K1 拒絕 0；B／epsilon 接受 0，並各自驗證範圍與有限值 | 7、13.1 |

| 6 | 品質平均浮點相等歧義 | Hit Rate／MRR 使用 Fraction 保存、聚合與比較；Decimal 僅供顯示 | 12.5、13.1、14.1 |

## 22. v1.6 缺口關閉對照

| # | 問題 | 修正 | 位置 |

|---:|---|---|---|

| 1 | 快取與乾淨工作目錄契約不清 | 外部快取、模型與 bytecode 政策 | 12.7.2、12.7.3 |

| 2 | Windows 換行比對歧義 | LF 與 Git blob 原始 bytes 比對 | 12.7.4 |

| 3 | 實際依賴未驗證 | 完整環境 Manifest 與 fingerprint v2 | 12.7.1、12.7.5 |

| 4 | Dense-only 同分規則缺失 | 保留輸入候選順序 | 6.5 |

| 5 | 路徑句點規則誤讀 | 禁止點路徑片段，允許副檔名句點 | 12.7.1 |

| 6 | 時間 Regex 表格跳脫 | 獨立 TIME_PATTERN | 6.3.1 |

v1.6 交付範圍為規格文件；實際環境 Manifest、程式、測試與 Benchmark 由後續實作產生。本次未重新下載模型驗證權重；第 6.5 節既有查證紀錄沿用來源文件，下載後本機完整性驗證仍為必要條件。