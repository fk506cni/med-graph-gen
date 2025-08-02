import json
import os
import re
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

def create_paragraphs_with_source(pages):
    """ページ分割されたテキストから、出典情報付きの段落リストを作成する"""
    paragraphs = []
    current_paragraph = ""
    current_pages = set()

    for page in pages:
        page_number = page['page_number']
        text = page['text']
        # ページ内のテキストを空行で分割
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # 行が空でなく、前の段落が続いている場合
            if line.strip() and current_paragraph:
                current_paragraph += " " + line
            # 行が空でなく、新しい段落が始まる場合
            elif line.strip():
                current_paragraph = line
            # 行が空（段落の区切り）で、現在の段落に内容がある場合
            elif not line.strip() and current_paragraph:
                paragraphs.append({
                    "paragraph": current_paragraph.strip(),
                    "source_pages": sorted(list(current_pages))
                })
                current_paragraph = ""
                current_pages = set()
            
            # 現在の段落にページ番号を追加
            if current_paragraph:
                current_pages.add(page_number)

            # ページの最後の行で、まだ段落が続いている場合
            if i == len(lines) - 1 and current_paragraph:
                # 次のページに続く可能性があるため、ここでは段落を確定しない
                pass

    # 最後の段落を追加
    if current_paragraph:
        paragraphs.append({
            "paragraph": current_paragraph.strip(),
            "source_pages": sorted(list(current_pages))
        })

    return paragraphs

def load_prompt_template(file_path):
    """プロンプトテンプレートを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def clean_paragraphs_with_llm_batch(paragraphs_with_source, prompt_template, model_name, wait=60, batch_size=5):
    """LLMを使用して段落をクレンジングする（バッチ処理）"""
    model = genai.GenerativeModel(model_name)
    cleaned_data = []
    
    # 入力は段落オブジェクトのリスト
    paragraphs_to_clean = [item['paragraph'] for item in paragraphs_with_source]

    for i in range(0, len(paragraphs_to_clean), batch_size):
        batch_paragraphs = paragraphs_to_clean[i:i + batch_size]
        batch_source_info = paragraphs_with_source[i:i + batch_size]

        batch_json = json.dumps(batch_paragraphs, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{{JSON_INPUT}}", batch_json)
        
        try:
            print(f"段落バッチ {i // batch_size + 1} のクレンジングを開始... ({len(batch_paragraphs)}段落)")
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_json_str = response_text[len("```json"): -len("```")].strip()
            else:
                response_json_str = response_text

            batch_cleaned_data = json.loads(response_json_str)
            cleaned_paragraphs_batch = batch_cleaned_data.get('cleaned_paragraphs', [])
            
            # クレンジング結果と元の出典情報を組み合わせる
            for idx, cleaned_text in enumerate(cleaned_paragraphs_batch):
                if cleaned_text and idx < len(batch_source_info):
                    original_source = batch_source_info[idx]['source_pages']
                    cleaned_data.append({
                        "paragraph": cleaned_text,
                        "source_pages": original_source
                    })

            print(f"段落バッチ {i // batch_size + 1} のクレンジングが完了しました。")

        except Exception as e:
            print(f"バッチ処理中にエラーが発生しました: {e}")
            continue
        finally:
            time.sleep(wait)
            
    return cleaned_data

def main(model_name='gemini-1.5-flash-latest', wait=60):
    """メイン処理"""
    input_path = "output/step1_structured_text.json"
    prompt_template_path = "paragraph_cleaning_prompt.md"
    output_cleaned_text_path = "output/step2a_cleaned_text.json"

    print("構造化されたテキストを読み込み中...")
    pages = load_structured_text(input_path)

    print("テキストを段落に分割し、出典情報を付与中...")
    paragraphs_with_source = create_paragraphs_with_source(pages)
    print(f"{len(paragraphs_with_source)}個の段落に分割されました。")

    print("プロンプトテンプレートを読み込み中...")
    prompt_template = load_prompt_template(prompt_template_path)

    print("LLMを使用して段落をクレンジング中（バッチ処理）...")
    cleaned_paragraphs = clean_paragraphs_with_llm_batch(paragraphs_with_source, prompt_template, model_name, wait=wait)

    print(f"クレンジングされた段落を {output_cleaned_text_path} に保存中...")
    with open(output_cleaned_text_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_paragraphs, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。")

if __name__ == "__main__":
    main()
