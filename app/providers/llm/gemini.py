import json
from typing import List, Optional, Type

from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse

DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_EMBEDDING_MODEL = "models/text-embedding-004"


class GeminiProvider(LLMProvider):
    """Real Gemini implementation. Falls back to another LLMProvider (e.g.
    OpenAIProvider) on any API error, if one was supplied."""

    def __init__(self, api_key: str, fallback: Optional[LLMProvider] = None, model_name: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._fallback = fallback
        self._model_name = model_name

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install with: pip install -e '.[real]'"
            ) from exc

        try:
            genai.configure(api_key=self._api_key)
            generation_config: dict = {"temperature": temperature}
            if response_schema is not None:
                generation_config["response_mime_type"] = "application/json"

            model = genai.GenerativeModel(self._model_name, system_instruction=system_prompt)
            response = await model.generate_content_async(user_prompt, generation_config=generation_config)
            text = response.text
            parsed = json.loads(text) if response_schema is not None else None
            return LLMResponse(text=text, parsed=parsed, model=self._model_name, is_mock=False)
        except Exception:
            if self._fallback is not None:
                return await self._fallback.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=response_schema,
                    temperature=temperature,
                )
            raise

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install with: pip install -e '.[real]'"
            ) from exc

        genai.configure(api_key=self._api_key)
        vectors = []
        for text in texts:
            result = genai.embed_content(model=DEFAULT_EMBEDDING_MODEL, content=text)
            vectors.append(list(result["embedding"]))
        return vectors
