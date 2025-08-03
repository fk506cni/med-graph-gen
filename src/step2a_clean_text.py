import json
import time
from .llm_utils import get_gemini_model, llm_generate_with_retry

def load_structured_text(file_path):
    """構造化されたテキストデータを読み込む
    Loads structured text data."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_paragraphs_with_source(pages):
    """ページ分割されたテキストから、出典情報付きの段落リストを作成する
    Creates a list of paragraphs with source information from paginated text."""
    paragraphs = []
    current_paragraph = ""
    current_pages = set()

    for page in pages:
        page_number = page['page_number']
        text = page['text']
        # ページ内のテキストを空行で分割
        # Split the text within a page by blank lines
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # 行が空でなく、前の段落が続いている場合
            # If the line is not empty and the previous paragraph continues
            if line.strip() and current_paragraph:
                current_paragraph += " " + line
            # 行が空でなく、新しい段落が始まる場合
            # If the line is not empty and a new paragraph begins
            elif line.strip():
                current_paragraph = line
            # 行が空（段落の区切り）で、現在の段落に内容がある場合
            # If the line is empty (paragraph break) and the current paragraph has content
            elif not line.strip() and current_paragraph:
                paragraphs.append({
                    "paragraph": current_paragraph.strip(),
                    "source_pages": sorted(list(current_pages))
                })
                current_paragraph = ""
                current_pages = set()
            
            # 現在の段落にページ番号を追加
            # Add the page number to the current paragraph
            if current_paragraph:
                current_pages.add(page_number)

            # ページの最後の行で、まだ段落が続いている場合
            # If it is the last line of the page and the paragraph is still continuing
            if i == len(lines) - 1 and current_paragraph:
                # 次のページに続く可能性があるため、ここでは段落を確定しない
                # Do not finalize the paragraph here as it may continue on the next page
                pass

    # 最後の段落を追加
    # Add the last paragraph
    if current_paragraph:
        paragraphs.append({
            "paragraph": current_paragraph.strip(),
            "source_pages": sorted(list(current_pages))
        })

    return paragraphs

def load_prompt_template(file_path):
    """プロンプトテンプレートを読み込む
    Loads the prompt template."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def clean_paragraphs_with_llm_batch(paragraphs_with_source, prompt_template, model, wait=60, retries=3, batch_size=5):
    """LLMを使用して段落をクレンジングする（バッチ処理＆リトライ機能付き）
    Cleans paragraphs using an LLM (with batch processing and retry functionality)."""
    cleaned_data = []
    
    paragraphs_to_clean = [item['paragraph'] for item in paragraphs_with_source]

    for i in range(0, len(paragraphs_to_clean), batch_size):
        batch_paragraphs = paragraphs_to_clean[i:i + batch_size]
        batch_source_info = paragraphs_with_source[i:i + batch_size]

        batch_json = json.dumps(batch_paragraphs, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{{JSON_INPUT}}", batch_json)
        
        try:
            print(f"段落バッチ {i // batch_size + 1} のクレンジングを開始... ({len(batch_paragraphs)}段落) / Starting cleaning for paragraph batch {i // batch_size + 1} ... ({len(batch_paragraphs)} paragraphs)")
            response = llm_generate_with_retry(model, prompt, retries=retries)
            
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_json_str = response_text[len("```json"):-len("```")].strip()
            else:
                response_json_str = response_text

            batch_cleaned_data = json.loads(response_json_str)
            cleaned_paragraphs_batch = batch_cleaned_data.get('cleaned_paragraphs', [])
            
            for idx, cleaned_text in enumerate(cleaned_paragraphs_batch):
                if cleaned_text and idx < len(batch_source_info):
                    original_source = batch_source_info[idx]['source_pages']
                    cleaned_data.append({
                        "paragraph": cleaned_text,
                        "source_pages": original_source
                    })

            print(f"段落バッチ {i // batch_size + 1} のクレンジングが完了しました。 / Cleaning of paragraph batch {i // batch_size + 1} completed.")

        except Exception as e:
            print(f"バッチ処理中に致命的なエラーが発生しました: {e} / A fatal error occurred during batch processing: {e}")
            # エラーが発生したバッチはスキップして次のバッチへ
            # Skip the batch where the error occurred and proceed to the next one
            continue
        finally:
            # APIのレート制限を避けるために待機
            # Wait to avoid API rate limits
            if i + batch_size < len(paragraphs_to_clean):
                print(f"{wait}秒待機します... / Waiting for {wait} seconds...")
                time.sleep(wait)
            
    return cleaned_data

def main(model_name='gemini-1.5-flash-latest', wait=60, retries=3):
    """メイン処理
    Main process"""
    input_path = "output/step1_structured_text.json"
    prompt_template_path = "paragraph_cleaning_prompt.md"
    output_cleaned_text_path = "output/step2a_cleaned_text.json"

    print("構造化されたテキストを読み込み中... / Loading structured text...")
    pages = load_structured_text(input_path)

    print("テキストを段落に分割し、出典情報を付与中... / Splitting text into paragraphs and adding source information...")
    paragraphs_with_source = create_paragraphs_with_source(pages)
    print(f"{len(paragraphs_with_source)}個の段落に分割されました。 / The text has been split into {len(paragraphs_with_source)} paragraphs.")

    print("プロンプトテンプレートを読み込み中... / Loading prompt template...")
    prompt_template = load_prompt_template(prompt_template_path)

    print("LLMモデルを初期化中... / Initializing LLM model...")
    model = get_gemini_model(model_name)

    print("LLMを使用して段落をクレンジング中（バッチ処理）... / Cleaning paragraphs using LLM (batch processing)...")
    cleaned_paragraphs = clean_paragraphs_with_llm_batch(
        paragraphs_with_source, 
        prompt_template, 
        model, 
        wait=wait, 
        retries=retries
    )

    print(f"クレンジングされた段落を {output_cleaned_text_path} に保存中... / Saving cleaned paragraphs to {output_cleaned_text_path}...")
    with open(output_cleaned_text_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_paragraphs, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。 / Process completed.")

if __name__ == "__main__":
    # main.pyから呼び出されることを想定しているため、
    # 直接実行する場合の引数処理は省略しています。
    # Since this is expected to be called from main.py,
    # argument processing for direct execution is omitted.
    main()

