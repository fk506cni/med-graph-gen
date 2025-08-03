import json
from collections import defaultdict
import time
from .llm_utils import get_gemini_model, llm_generate_with_retry
from itertools import combinations
from string import Template
import os


# --- 定数 ---
# --- Constants ---
ENTITY_PAIR_BATCH_SIZE = 100 # 1回のLLM呼び出しで処理するエンティティペアの数 / Number of entity pairs to process in a single LLM call
INPUT_CLEANED_TEXT_PATH = "output/step2a_cleaned_text.json"
INPUT_ENTITIES_PATH = "output/step2b_entities.json"
OUTPUT_FILE = "output/step3b_relations.jsonl"
MAX_TOTAL_BATCHES = None # テスト用に最大バッチ数を設定 (Noneで無制限) / Set a maximum number of batches for testing (None for unlimited)

def load_prompt_template(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return Template(f.read())
    except FileNotFoundError:
        print(f"エラー: プロンプトファイルが見つかりません: {file_path} / Error: Prompt file not found: {file_path}")
        return None

def extract_relations_in_batches(model, paragraph, entities_in_paragraph, prompt_template, total_batch_counter, wait=60, retries=3):
    if len(entities_in_paragraph) < 2:
        return

    all_pairs = list(combinations(entities_in_paragraph, 2))
    
    for i in range(0, len(all_pairs), ENTITY_PAIR_BATCH_SIZE):
        if MAX_TOTAL_BATCHES is not None and total_batch_counter >= MAX_TOTAL_BATCHES:
            print("\nテスト用の最大バッチ数に達したため、処理を停止します。 / Reached the maximum number of batches for testing. Stopping processing.")
            return

        batch_pairs = all_pairs[i:i + ENTITY_PAIR_BATCH_SIZE]
        entity_pairs_json = json.dumps([{"source": e1['term'], "target": e2['term']} for e1, e2 in batch_pairs], ensure_ascii=False, indent=2)

        prompt = prompt_template.substitute(
            context_paragraph=paragraph,
            entity_pairs=entity_pairs_json
        )

        try:
            log_message = f"  - バッチ {total_batch_counter + 1}"
            if MAX_TOTAL_BATCHES is not None:
                log_message += f"/{MAX_TOTAL_BATCHES}"
            log_message += f" (段落内 {i//ENTITY_PAIR_BATCH_SIZE + 1}/{(len(all_pairs) + ENTITY_PAIR_BATCH_SIZE - 1)//ENTITY_PAIR_BATCH_SIZE}): {len(batch_pairs)}ペアを処理中... / Processing {len(batch_pairs)} pairs..."
            print(log_message)
            
            response = llm_generate_with_retry(model, prompt, retries=retries)
            response_text = response.text.strip()
            
            json_start = response_text.find('[')
            json_end = response_text.rfind(']')
            
            if json_start != -1 and json_end != -1:
                json_response_str = response_text[json_start:json_end+1]
                relations = json.loads(json_response_str)
                print(f"    -> {len(relations)}件の関係を抽出しました。 / Extracted {len(relations)} relations.")
                for rel in relations:
                    yield rel
            else:
                print(f"    -> 警告: レスポンスから有効なJSON配列が見つかりませんでした。 / Warning: No valid JSON array found in the response.")

        except json.JSONDecodeError:
            print(f"    -> エラー: LLMのレスポンスのJSONパースに失敗しました。 / Error: Failed to parse JSON from LLM response.")
            print(f"       LLM Response: {response_text}")
        except Exception as e:
            print(f"    -> LLM呼び出し中に致命的なエラーが発生しました: {e} / A fatal error occurred during the LLM call: {e}")
        
        total_batch_counter += 1
        yield total_batch_counter # ジェネレータから更新されたカウンタを返す / Return the updated counter from the generator

        if i + ENTITY_PAIR_BATCH_SIZE < len(all_pairs):
            time.sleep(wait)

def main(model_name='gemini-1.5-flash-latest', wait=60, retries=3):
    print("--- ステップ: step3b を開始します --- / --- Starting step: step3b ---")
    
    model = get_gemini_model(model_name)

    try:
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        output_dir = os.path.dirname(OUTPUT_FILE)
        print(f"DEBUG: Trying to use output directory: {output_dir}")
        print(f"DEBUG: Absolute path of output directory: {os.path.abspath(output_dir)}")
        print(f"DEBUG: Does output directory exist? {os.path.exists(output_dir)}")
        if not os.path.exists(output_dir):
            print(f"DEBUG: Output directory does not exist. Creating it...")
            try:
                os.makedirs(output_dir)
                print(f"DEBUG: Successfully created directory: {output_dir}")
            except Exception as e:
                print(f"FATAL: Failed to create directory {output_dir}: {e}")
                return
        print(f"DEBUG: Trying to open {OUTPUT_FILE} for writing...")
        with open(OUTPUT_FILE, "w") as f:
            pass
        print(f"DEBUG: Successfully initialized {OUTPUT_FILE}")
    except Exception as e:
        print(f"エラー: {OUTPUT_FILE} の初期化に失敗しました: {e} / Error: Failed to initialize {OUTPUT_FILE}: {e}")
        return

    try:
        with open(INPUT_CLEANED_TEXT_PATH, "r", encoding="utf-8") as f:
            cleaned_text = json.load(f)
        with open(INPUT_ENTITIES_PATH, "r", encoding="utf-8") as f:
            entities = json.load(f)
    except FileNotFoundError as e:
        print(f"エラー: 入力ファイルが見つかりません: {e.filename} / Error: Input file not found: {e.filename}")
        return

    prompt_template = load_prompt_template("relation_extraction_batch_prompt.md")
    if not prompt_template:
        return

    total_relations_found = 0
    total_batch_counter = 0
    for i, item in enumerate(cleaned_text):
        if MAX_TOTAL_BATCHES is not None and total_batch_counter >= MAX_TOTAL_BATCHES:
            break
        paragraph = item["paragraph"]
        source_pages = item["source_pages"]
        
        print(f"\n段落 {i+1}/{len(cleaned_text)} を処理中 (出典ページ: {source_pages})... / Processing paragraph {i+1}/{len(cleaned_text)} (source pages: {source_pages})...")
        
        entities_in_paragraph = [entity for entity in entities if entity['term'] in paragraph]

        relations_generator = extract_relations_in_batches(model, paragraph, entities_in_paragraph, prompt_template, total_batch_counter, wait=wait, retries=retries)
        
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            for result in relations_generator:
                if isinstance(result, int):
                    total_batch_counter = result
                else:
                    result['source_pages'] = source_pages
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    total_relations_found += 1

    print(f"\n処理が完了しました。合計 {total_relations_found} 件の関係を {OUTPUT_FILE} に保存しました。 / Process completed. A total of {total_relations_found} relations have been saved to {OUTPUT_FILE}.")
    print("--- ステップ: step3b が完了しました --- / --- Step: step3b completed ---")


if __name__ == "__main__":
    main()
