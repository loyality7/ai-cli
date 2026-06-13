"""Google Gemini provider."""

from typing import Any, Generator, Optional

from ai_cli.llm.base import BaseProvider, LLMMessage, LLMResponse


class GoogleProvider(BaseProvider):
    """Google Gemini via the google-genai SDK."""

    name = "google"

    def _init_client(self) -> Any:
        from google import genai
        return genai.Client(api_key=self.api_key)

    def stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        from google.genai import types

        # Gemini uses a flat content list
        contents = [m.content for m in messages if m.role != "system"]

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system.strip()

        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    def complete(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        from google.genai import types

        contents = [m.content for m in messages if m.role != "system"]

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system.strip()

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return LLMResponse(
            content=response.text or "",
            model=self.model,
            provider=self.name,
            usage={
                "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
            },
        )
