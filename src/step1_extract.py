import fitz  # PyMuPDF
import json
import os

def extract_text_from_pdf(pdf_path, start_page=None, end_page=None):
    """PDFから指定されたページ範囲のテキストを抽出する"""
    doc = fitz.open(pdf_path)
    text_by_page = []
    
    # ページ範囲の指定がない場合は全ページを対象とする
    if start_page is None:
        start_page = 1
    if end_page is None:
        end_page = doc.page_count

    # PyMuPDFのページ番号は0から始まるため調整
    start_index = start_page - 1
    end_index = end_page - 1

    # ページ範囲が妥当かチェック
    if start_index < 0 or end_index >= doc.page_count or start_index > end_index:
        raise ValueError(f"Invalid page range: {start_page}-{end_page}")

    for page_num in range(start_index, end_index + 1):
        page = doc.load_page(page_num)
        text = page.get_text()
        # ページ番号は1から始まるように+1する
        text_by_page.append({"page_number": page_num + 1, "text": text})
        
    doc.close()
    return text_by_page

def main(start_page=None, end_page=None):
    """メイン処理"""
    pdf_path = "input/c00543.pdf"
    output_path = "output/step1_structured_text.json"

    # outputディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if start_page and end_page:
        print(f"PDFから {start_page}ページから{end_page}ページまでのテキストを抽出中...")
    else:
        print("PDFから全ページのテキストを抽出中...")

    structured_data = extract_text_from_pdf(pdf_path, start_page=start_page, end_page=end_page)

    print(f"構造化されたデータを {output_path} に保存中...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。")

if __name__ == "__main__":
    main()