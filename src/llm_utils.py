
def get_gemini_model(model_name):
    """
    APIキーを環境変数から読み込み、Geminiモデルを初期化して返します。
    Loads the API key from environment variables, initializes and returns a Gemini model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'GEMINI_API_KEY' が設定されていません。 / Environment variable 'GEMINI_API_KEY' is not set.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

def llm_generate_with_retry(model, prompt, retries=3, wait_seconds_on_retry=5):
    """
    リトライ機能付きでLLMのAPIを呼び出します。
    Calls the LLM API with retry functionality.

    Args:
        model: 使用する生成AIモデル。 / The generative AI model to use.
        prompt: LLMに送信するプロンプト。 / The prompt to send to the LLM.
        retries: 最大リトライ回数。 / Maximum number of retries.
        wait_seconds_on_retry: リトライ時の待機時間（秒）。 / Wait time in seconds before retrying.

    Returns:
        APIからの正常なレスポンス。 / A successful response from the API.

    Raises:
        Exception: 全てのリトライが失敗した場合の最終的な例外。 / Final exception if all retries fail.
    """
    last_exception = None
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            print(f"LLM APIの呼び出しに失敗しました (試行 {attempt + 1}/{retries})。エラー: {e} / LLM API call failed (attempt {attempt + 1}/{retries}). Error: {e}")
            last_exception = e
            if attempt < retries - 1:
                print(f"{wait_seconds_on_retry}秒後に再試行します... / Retrying in {wait_seconds_on_retry} seconds...")
                time.sleep(wait_seconds_on_retry)
    
    print("全てのリトライに失敗しました。 / All retries failed.")
    raise last_exception

