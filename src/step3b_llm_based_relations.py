import json
import os
import time
from itertools import combinations
from string import Template
import google.generativeai as genai

# --- 定数 ---
DELAY_SECONDS = 15 # API呼び出しごとの待機時間（レート制限対策で延長）
ENTITY_PAIR_BATCH_SIZE = 50 # 1回のLLM呼び出しで処理するエンティティペアの数
OUTPUT_FILE = "output/relations.jsonl"
MAX_TOTAL_BATCHES = 2 # テスト用に最大バッチ数を設定

print(f"デバッグ: ENTITY_PAIR_BATCH_SIZE: {ENTITY_PAIR_BATCH_SIZE}")
print(f"デバッグ: DELAY_SECONDS: {DELAY_SECONDS}")
print(f"デバッグ: MAX_TOTAL_BATCHES: {MAX_TOTAL_BATCHES}")

# --- APIキーとモデルの設定 ---
print("デバッグ: APIキーの設定を開始します...")
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise KeyError("GEMINI_API_KEY 環境変数が設定されていません。")
    genai.configure(api_key=api_key)
    print("デバッグ: APIキーの設定が完了しました。")
    
    print("デバッグ: Geminiモデルの初期化を開始します...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("デバッグ: Geminiモデルの初期化が完了しました。")
except KeyError as e:
    print(f"エラー: {e}")
    exit(1)
except Exception as e:
    print(f"エラー: モデルの初期化中に予期せぬエラーが発生しました: {e}")
    exit(1)

def load_prompt_template(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return Template(f.read())
    except FileNotFoundError:
        print(f"エラー: プロンプトファイルが見つかりません: {file_path}")
        return None

def extract_relations_in_batches(paragraph, entities_in_paragraph, prompt_template, total_batch_counter):
    if len(entities_in_paragraph) < 2:
        return

    all_pairs = list(combinations(entities_in_paragraph, 2))
    
    for i in range(0, len(all_pairs), ENTITY_PAIR_BATCH_SIZE):
        if total_batch_counter >= MAX_TOTAL_BATCHES:
            print("\nテスト用の最大バッチ数に達したため、処理を停止します。")
            return

        batch_pairs = all_pairs[i:i + ENTITY_PAIR_BATCH_SIZE]
        entity_pairs_json = json.dumps([{"source": e1['term'], "target": e2['term']} for e1, e2 in batch_pairs], ensure_ascii=False, indent=2)

        prompt = prompt_template.substitute(
            context_paragraph=paragraph,
            entity_pairs=entity_pairs_json
        )

        try:
            print(f"  - バッチ {total_batch_counter + 1}/{MAX_TOTAL_BATCHES} (段落内 {i//ENTITY_PAIR_BATCH_SIZE + 1}/{(len(all_pairs) + ENTITY_PAIR_BATCH_SIZE - 1)//ENTITY_PAIR_BATCH_SIZE}): {len(batch_pairs)}ペアを処理中...")
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            json_start = response_text.find('[')
            json_end = response_text.rfind(']')
            
            if json_start != -1 and json_end != -1:
                json_response_str = response_text[json_start:json_end+1]
                relations = json.loads(json_response_str)
                print(f"    -> {len(relations)}件の関係を抽出しました。")
                for rel in relations:
                    yield rel
            else:
                print(f"    -> 警告: レスポンスから有効なJSON配列が見つかりませんでした。")

        except json.JSONDecodeError:
            print(f"    -> エラー: LLMのレスポンスのJSONパースに失敗しました。")
            print(f"       LLM Response: {response_text}")
        except Exception as e:
            if "429" in str(e):
                print("    -> エラー: APIレート制限に達しました。60秒待機します...")
                time.sleep(60)
            else:
                print(f"    -> LLM呼び出し中に予期せぬエラーが発生しました: {e}")
        
        total_batch_counter += 1
        yield total_batch_counter # ジェネレータから更新されたカウンタを返す

        time.sleep(DELAY_SECONDS)

def main():
    print("--- ステップ: step3b を開始します ---")
    
    # デバッグ: ファイルの存在確認と初期化
    print(f"デバッグ: {OUTPUT_FILE} の初期化を試みます...")
    try:
        # 出力ディレクトリが存在しない場合は作成
        output_dir = os.path.dirname(OUTPUT_FILE)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"デバッグ: 出力ディレクトリ {output_dir} を作成しました。")
        
        with open(OUTPUT_FILE, "w") as f:
            pass # ファイルを空にする
        print(f"デバッグ: {OUTPUT_FILE} の初期化完了。")
    except Exception as e:
        print(f"エラー: {OUTPUT_FILE} の初期化に失敗しました: {e}")
        return

    # 入力ファイルの読み込み
    try:
        print("デバッグ: output/cleaned_text.json の読み込みを開始します...")
        with open("output/cleaned_text.json", "r", encoding="utf-8") as f:
            cleaned_text = json.load(f)
        print("デバッグ: output/cleaned_text.json の読み込み完了。")
        
        print("デバッグ: output/entities.json の読み込みを開始します...")
        with open("output/entities.json", "r", encoding="utf-8") as f:
            entities = json.load(f)
        print("デバッグ: output/entities.json の読み込み完了。")

    except FileNotFoundError as e:
        print(f"エラー: 入力ファイルが見つかりません: {e.filename}")
        return
    except Exception as e:
        print(f"エラー: 入力ファイルの読み込み中に予期せぬエラーが発生しました: {e}")
        return

    prompt_template = load_prompt_template("relation_extraction_batch_prompt.md")
    if not prompt_template:
        return

    total_relations_found = 0
    total_batch_counter = 0
    for i, item in enumerate(cleaned_text):
        if total_batch_counter >= MAX_TOTAL_BATCHES:
            break
        paragraph = item["paragraph"]
        source_pages = item["source_pages"]
        
        print(f"\n段落 {i+1}/{len(cleaned_text)} を処理中 (出典ページ: {source_pages})...")
        
        entities_in_paragraph = [entity for entity in entities if entity['term'] in paragraph]

        relations_generator = extract_relations_in_batches(paragraph, entities_in_paragraph, prompt_template, total_batch_counter)
        
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            for result in relations_generator:
                if isinstance(result, int):
                    total_batch_counter = result
                else:
                    result['source_pages'] = source_pages
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    total_relations_found += 1

    print(f"\n処理が完了しました。合計 {total_relations_found} 件の関係を {OUTPUT_FILE} に保存しました。")
    print("--- ステップ: step3b が完了しました ---")

if __name__ == "__main__":
    main()