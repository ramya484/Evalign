"""Create LLM instances from env-driven config (provider-agnostic)."""
from app.config.settings import settings
from app.utils.logging import get_logger
logger = get_logger(__name__)

def create_llm():
    provider = settings.LLM_PROVIDER.lower()
    logger.info("Creating LLM: provider=%s model=%s", provider, settings.LLM_MODEL)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.LLM_API_KEY, temperature=settings.LLM_TEMPERATURE, max_tokens=settings.LLM_MAX_TOKENS)
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=settings.LLM_MODEL, google_api_key=settings.LLM_API_KEY, temperature=settings.LLM_TEMPERATURE)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.LLM_MODEL, api_key=settings.LLM_API_KEY, temperature=settings.LLM_TEMPERATURE, max_tokens=settings.LLM_MAX_TOKENS)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Use openai|google|anthropic")
