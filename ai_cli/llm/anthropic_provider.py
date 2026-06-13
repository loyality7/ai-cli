"""Anthropic (Claude) provider."""

from typing import Any, Generator, Optional

from ai_cli.llm.base import BaseProvider, LLMMessage, LLMResponse


class AnthropicProvider(BaseProvider):
    """Claude via the Anthropic API."""

    name = "anthropic"

    def _init_client(self) -> Any:
        import anthropic
        return anthropic.Anthropic(
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            kwargs["system"] = system

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def complete(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.name,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason or "",
        )
