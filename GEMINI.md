## Project Status: Initial Implementation Complete

**Objective:** Develop a system to generate a knowledge graph CSV from a PDF document.

**Current State:**

1.  **Project Structure:** The directory structure (`build`, `src`, `input`, `output`) has been created.
2.  **Development Environment:**
    *   A `Dockerfile` and a fully pinned `requirements.txt` have been created in the `build/` directory.
    *   The Docker image `knowledge-graph-builder` now builds successfully.
    *   Gemini APIキーは、ホストの`.env`ファイルに記載し、コンテナ実行時に`--env-file`オプションで渡すように変更しました。これにより、APIキーがDockerイメージに焼き込まれることを防ぎ、セキュリティを向上させています。
3.  **Source Files:**
    *   `src/step1_extract.py`: PDFから全てのテキストをページ単位で抽出するように実装を修正しました。
    *   `src/step2_entities.py`: LLM（Gemini）を使用して、抽出されたテキストから医学的に無関係な情報（参考文献、引用番号、目次など）をクレンジングし、エンティティを抽出するように実装を修正しました。APIのレートリミットを考慮し、バッチ処理とAPI呼び出し間のウェイト（待機時間）を導入しています。
    *   `src/main.py`: `step1_extract.py`と`step2_entities.py`を順次実行するように修正しました。
    *   `empty_extract_prompt.md`と`batch_extract_prompt.md`: LLMによるテキストクレンジング用のプロンプトテンプレートを作成しました。

**Next Steps:**

*   Proceed with the implementation of the Python scripts as defined in `README.md`, starting with `src/step3a_rule_based_relations.py`.