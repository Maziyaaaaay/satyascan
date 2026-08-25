import json
from typing import List, Optional, Type

from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse, WebSearchResult
from app.providers.llm._gemini_schema import to_gemini_schema

# "-latest" alias so this doesn't silently break again next time Google
# retires a dated model (gemini-1.5-flash was retired between when this
# adapter was first written and when it was first tested against a live key).
DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
REQUEST_TIMEOUT_SECONDS = 20


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
                # Passing just response_mime_type isn't enough - confirmed against
                # a live key that Gemini then free-associates a JSON shape from
                # the prompt text instead of matching the caller's schema (e.g.
                # returning a bare list instead of {"claims": [...]}). And
                # passing the pydantic class directly for the SDK to
                # auto-convert breaks on any field with a default value
                # ("ValueError: Unknown field for Schema: default", also
                # confirmed live) - to_gemini_schema() produces the sanitized
                # dict shape Gemini's Schema proto actually accepts.
                generation_config["response_schema"] = to_gemini_schema(response_schema)

            model = genai.GenerativeModel(self._model_name, system_instruction=system_prompt)
            response = await model.generate_content_async(
                user_prompt,
                generation_config=generation_config,
                request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
            )
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

    async def search_grounded(self, query: str) -> Optional[WebSearchResult]:
        # Best-effort: grounding support depends on the resolved model
        # version and can fail for reasons unrelated to the claim itself
        # (unsupported tool, quota, transient error) - any failure here
        # must just mean "no live-search evidence available", never break
        # the pipeline the way a raised exception would.
        try:
            import google.generativeai as genai
        except ImportError:
            return None

        try:
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model_name)
            # Confirmed live: this deprecated SDK's dict-shorthand tool spec
            # (tools=[{"google_search": {}}]) is misparsed as a
            # FunctionDeclaration ("Unknown field for FunctionDeclaration:
            # google_search"), and the older GoogleSearchRetrieval proto is
            # explicitly rejected by the API for this model family ("400
            # google_search_retrieval is not supported. Please use
            # google_search tool instead") - the nested Tool.GoogleSearch
            # message below is the form that actually works.
            search_tool = genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())
            response = await model.generate_content_async(
                query,
                tools=[search_tool],
                request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
            )
            summary = response.text
            if not summary:
                return None

            source_urls: List[str] = []
            for candidate in getattr(response, "candidates", None) or []:
                grounding_metadata = getattr(candidate, "grounding_metadata", None)
                for chunk in getattr(grounding_metadata, "grounding_chunks", None) or []:
                    web = getattr(chunk, "web", None)
                    uri = getattr(web, "uri", None)
                    if uri:
                        source_urls.append(uri)

            return WebSearchResult(summary=summary, source_urls=source_urls)
        except Exception:
            return None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install with: pip install -e '.[real]'"
            ) from exc

        genai.configure(api_key=self._api_key)

        def _embed_all():
            vectors = []
            for text in texts:
                result = genai.embed_content(
                    model=DEFAULT_EMBEDDING_MODEL,
                    content=text,
                    request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
                )
                vectors.append(list(result["embedding"]))
            return vectors

        import asyncio

        # embed_content is synchronous (blocking) - the deprecated
        # google-generativeai SDK has no async variant, so this must be
        # offloaded to a thread or it would block the event loop under load.
        return await asyncio.to_thread(_embed_all)
