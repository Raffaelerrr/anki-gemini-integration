DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MODEL_OPTIMIZE = "gemini-2.5-flash-lite"
DEFAULT_MODEL_CHAT = "gemini-2.5-flash"
DEFAULT_THINKING_BUDGET_OPTIMIZE = 0
DEFAULT_THINKING_BUDGET_CHAT = -1
DEFAULT_PROMPT_CACHE_MIN_TOKENS = 2048
DEFAULT_PROMPT_CACHE_MIN_CHARS = DEFAULT_PROMPT_CACHE_MIN_TOKENS * 4
GEMINI_API_HOST = "generativelanguage.googleapis.com"
GEMINI_AI_STUDIO_BILLING_URL = "https://aistudio.google.com/billing"
GEMINI_AI_STUDIO_USAGE_URL = "https://aistudio.google.com/usage"
GEMINI_API_BILLING_DOCS_URL = "https://ai.google.dev/gemini-api/docs/billing"
GEMINI_API_PATH = "/v1beta/models/{model}:generateContent"
GEMINI_STREAM_API_PATH = "/v1beta/models/{model}:streamGenerateContent"
GEMINI_MODELS_LIST_PATH = "/v1beta/models"

# Stable / common Gemini text models, newest first; lite before flash before pro.
GEMINI_MODEL_CHOICES: tuple[str, ...] = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
)
