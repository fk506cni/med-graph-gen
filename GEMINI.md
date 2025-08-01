## Project Status: Step 1, 2, & 3b Implemented with Enhancements

**Objective:** Develop a system to generate a knowledge graph CSV from a PDF document.

### Key Developments

1.  **Refined Step 2 (Text Cleansing & Entity Extraction):**
    *   The original `step2_entities.py` was split into `step2a_clean_text.py` and `step2b_extract_entities.py` for better maintainability.
    *   Entity extraction was updated to use the LLM (Gemini), replacing the initial GiNZA-based approach.

2.  **Paragraph-based Processing:**
    *   To handle sentences that span across pages, the pipeline was modified to operate on paragraphs instead of pages.
    *   `step2a` now combines text from all pages, splits it into paragraphs, and then performs cleansing.

3.  **Source-Aware Data Structure:**
    *   To ensure traceability, the data format for intermediate files (`cleaned_text.json`, `entities.json`) was updated. Each paragraph and entity is now stored as a JSON object that includes a `source_pages` field, linking it back to the original page numbers in the PDF.

4.  **Flexible Pipeline Execution:**
    *   `main.py` was enhanced with a command-line argument (`--start-step`) to allow the pipeline to be started from any specific step. This significantly speeds up development and testing by avoiding the need to re-run earlier, time-consuming steps (like API calls).

5.  **Configurable Page Range:**
    *   `step1_extract.py` was modified to allow specifying a `start_page` and `end_page`, making it easier to test and debug the pipeline on specific sections of the PDF.

### Current State

*   The implementation of `step1`, `step2a`, and `step2b` is complete and verified.
*   The system can now extract text from a specified page range, cleanse it at the paragraph level while retaining source page information, and then extract entities with their corresponding source pages.
*   The project structure, Docker environment, and main execution scriptはすべてこれらの変更を反映するように更新されています。

### Recent Updates (August 1, 2025)

*   **Step 3b (LLM-based Relation Extraction) の実装:**
    *   `src/step3b_llm_based_relations.py` にLLMを用いた関係抽出ロジックを実装しました。
    *   APIレート制限を考慮し、エンティティペアを小バッチに分割してLLMに送信し、各バッチの処理後に遅延を設けるようにしました。
    *   抽出された関係は、`output/relations.jsonl` にJSON Lines形式で逐次書き込まれます。
    *   `main.py` から `--start-step step3b` で実行可能です。
*   **GiNZAモデルのロード問題の解決:**
    *   `Dockerfile` および `requirements.txt` を修正し、`spacy.load("ja_core_news_lg")` でGiNZAモデルが正しくロードされるようにしました。
    *   `numpy` のバージョン互換性問題を解決するため、`requirements.txt` に `numpy<2.0` を追加しました。
*   **Docker実行コマンドの修正:**
    *   `README.md` に記載されているDocker実行コマンドを、`$(pwd)` を使用しない絶対パス形式に修正しました。

### Next Steps

*   Proceed with the implementation of `src/step4_normalize.py`.