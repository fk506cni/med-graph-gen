import json
import os
import spacy
import google.generativeai as genai
import time

# APIキーを環境変数から取得
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=api_key)

def load_structured_text(file_path):
    """構造化されたテキストデータを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_prompt_template(file_path):
    """プロンプトテンプレートを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def clean_text_with_llm_batch(pages, prompt_template, batch_size=10, delay=60):
    """LLMを使用して不要なテキストを除去する（バッチ処理）"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    cleaned_pages = []
    
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        batch_input = []
        for page in batch:
            batch_input.append({"page_number": page['page_number'], "text": page['text']})
        
        batch_json = json.dumps({"pages": batch_input}, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{{BATCH_JSON}}", batch_json)
        
        try:
            response = model.generate_content(prompt)
            # LLMの出力からJSON部分を抽出
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_json_str = response_text[len("```json"): -len("```")].strip()
            else:
                response_json_str = response_text

            batch_cleaned_data = json.loads(response_json_str)
            
            for cleaned_page_data in batch_cleaned_data['cleaned_pages']:
                if cleaned_page_data['cleaned_text']:
                    cleaned_pages.append({"page_number": cleaned_page_data['page_number'], "text": cleaned_page_data['cleaned_text']})
                    print(f"ページ {cleaned_page_data['page_number']} のクレンジングが完了しました。")
                else:
                    print(f"ページ {cleaned_page_data['page_number']} は無関係な情報のみと判断され、除外されました。")
        except Exception as e:
            print(f"バッチ処理中にエラーが発生しました: {e}")
            # エラーが発生したバッチのページはスキップ
            for page in batch:
                print(f"ページ {page['page_number']} の処理中にエラーが発生したためスキップされました。")
            continue
        finally:
            # レートリミットを避けるためにAPI呼び出しの間にウェイトを設ける
            time.sleep(delay)
            
    return cleaned_pages

def extract_entities(pages):
    """テキストからエンティティを抽出する"""
    nlp = spacy.load("ja_ginza_electra")
    entities = set()

    for page in pages:
        doc = nlp(page['text'])
        for ent in doc.ents:
            if ent.label_ in ["Disease", "Symptom", "Drug", "Treatment"]:
                entities.add(ent.text)
    return list(entities)

def main():
    """メイン処理"""
    input_path = "output/structured_text.json"
    prompt_template_path = "batch_extract_prompt.md" # 変更
    output_entities_path = "output/entities.json"
    output_cleaned_text_path = "output/cleaned_text.json"

    print("構造化されたテキストを読み込み中...")
    pages = load_structured_text(input_path)

    print("プロンプトテンプレートを読み込み中...")
    prompt_template = load_prompt_template(prompt_template_path)

    print("LLMを使用してテキストをクレンジング中（バッチ処理）...")
    cleaned_pages = clean_text_with_llm_batch(pages, prompt_template)

    print(f"クレンジングされたテキストを {output_cleaned_text_path} に保存中...")
    with open(output_cleaned_text_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_pages, f, ensure_ascii=False, indent=2)

    print("エンティティを抽出中...")
    entities = extract_entities(cleaned_pages)

    print(f"抽出されたエンティティを {output_entities_path} に保存中...")
    with open(output_entities_path, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。")

if __name__ == "__main__":
    main()