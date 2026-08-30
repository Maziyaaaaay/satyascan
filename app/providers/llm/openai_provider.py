import json
from typing import List, Optional, Type

from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._model_name = model_name

    def _client(self):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed. Install with: pip install -e '.[real]'") from exc
        return AsyncOpenAI(api_key=self._api_key)

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        client = self._client()
        kwargs: dict = {}
        if response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
            # OpenAI rejects response_format=json_object with a 400 unless
            # the literal word "json" appears somewhere in the messages -
            # confirmed live ("'messages' must contain the word 'json'...").
            # Callers' prompts (see app/agents/prompts/) aren't written
            # with OpenAI's API in mind, so this can't rely on them - append
            # the instruction here instead of at every call site.
            system_prompt = f"{system_prompt}\n\nRespond with valid JSON only."

        completion = await client.chat.completions.create(
            model=self._model_name,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        text = completion.choices[0].message.content or ""
        parsed = json.loads(text) if response_schema is not None else None
        return LLMResponse(text=text, parsed=parsed, model=self._model_name, is_mock=False)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        client = self._client()
        response = await client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
