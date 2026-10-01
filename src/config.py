import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    search_results_per_query: int = int(os.getenv("SEARCH_RESULTS_PER_QUERY", "10"))
    analyze_limit: int = int(os.getenv("ANALYZE_LIMIT", "50"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    candidate_profile: str = os.getenv("CANDIDATE_PROFILE", "Final-year software engineering student seeking a 6-month PFE.")
settings = Settings()
