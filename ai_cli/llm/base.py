"""
Abstract base for all LLM providers.

Every provider must implement:
  - stream()      → yield chunks of text
  - complete()    → return full response (non-streaming)
  - validate()    → check if API key works
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str       # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Complete response from the LLM."""
    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)  # input_tokens, output_tokens
    finish_reason: str = ""


class BaseProvider(ABC):
    """
    Abstract LLM provider.

    All providers share the same interface so the rest of the app
    doesn't care which one is active.
    """

    name: str = "base"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self._client: Any = None

    @abstractmethod
    def _init_client(self) -> Any:
        """Initialize the provider-specific client."""
        ...

    @property
    def client(self) -> Any:
        """Lazy client initialization."""
        if self._client is None:
            self._client = self._init_client()
        return self._client

    @abstractmethod
    def stream(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Stream response chunks. Yields text strings."""
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Get a complete (non-streaming) response."""
        ...

    def validate(self) -> bool:
        """
        Check if the API key and model are valid.
        Sends a tiny test request.
        """
        try:
            response = self.complete(
                messages=[LLMMessage(role="user", content="hi")],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False
