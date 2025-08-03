
import os
import time
import google.generativeai as genai

def get_gemini_model(model_name):
    """
    APIキーを環境変数から読み込み、Geminiモデルを初期化して返します。
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'GEMINI_API_KEY' が設定されていません。")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

def llm_generate_with_retry(model, prompt, retries=3, wait_seconds_on_retry=5):
    """
    リトライ機能付きでLLMのAPIを呼び出します。

    Args:
        model: 使用する生成AIモデル。
        prompt: LLMに送信するプロンプト。
        retries: 最大リトライ回数。
        wait_seconds_on_retry: リトライ時の待機時間（秒）。

    Returns:
        APIからの正常なレスポンス。

    Raises:
        Exception: 全てのリトライが失敗した場合の最終的な例外。
    """
    last_exception = None
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            print(f"LLM APIの呼び出しに失敗しました (試行 {attempt + 1}/{retries})。エラー: {e}")
            last_exception = e
            if attempt < retries - 1:
                print(f"{wait_seconds_on_retry}秒後に再試行します...")
                time.sleep(wait_seconds_on_retry)
    
    print("全てのリトライに失敗しました。")
    raise last_exception

