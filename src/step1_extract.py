import fitz  # PyMuPDF
import json
import os

def extract_text_from_pdf(pdf_path):
    """PDFからページごとにテキストを抽出する"""
    doc = fitz.open(pdf_path)
    text_by_page = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        text_by_page.append({"page_number": page_num, "text": text})
    doc.close()
    return text_by_page

def main():
    """メイン処理"""
    pdf_path = "input/c00543.pdf"
    output_path = "output/structured_text.json"

    # outputディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("PDFからテキストを抽出中...")
    structured_data = extract_text_from_pdf(pdf_path)

    print(f"構造化されたデータを {output_path} に保存中...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)

    print("処理が完了しました。")

if __name__ == "__main__":
    main()