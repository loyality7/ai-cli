"""OpenAI provider — also works for OpenRouter and any OpenAI-compatible endpoint."""

from typing import Any, Generator, Optional

from ai_cli.llm.base import BaseProvider, LLMMessage, LLMResponse


class OpenAIProvider(BaseProvider):
    """
    OpenAI-compatible provider.

    Works with:
      - OpenAI directly
      - OpenRouter (set base_url to https://openrouter.ai/api/v1)
      - Any custom OpenAI-compatible endpoint (LM Studio, Ollama, vLLM, etc.)
    """

    name = "openai"

    def _init_client(self) -> Any:
        from openai import OpenAI

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url

        return OpenAI(**kwargs)

    def stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        api_messages: list[dict[str, str]] = []

        if system:
            api_messages.append({"role": "system", "content": system})

        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def complete(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        api_messages: list[dict[str, str]] = []

        if system:
            api_messages.append({"role": "system", "content": system})

        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.name,
            usage={
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason or "",
        )
