from typing import Dict
from contacteval.players.base import Player
from contacteval.players.adapters import (
    OpenAIPlayer, 
    AnthropicPlayer, 
    GeminiPlayer, 
    OllamaPlayer,
    MockPlayer
)

def create_player(name: str, provider: str, model_id: str, **kwargs) -> Player:
    provider = provider.lower()
    if provider == "openai":
        return OpenAIPlayer(name, model=model_id, **kwargs)
    elif provider == "anthropic":
        return AnthropicPlayer(name, model=model_id, **kwargs)
    elif provider == "google":
        return GeminiPlayer(name, model=model_id, **kwargs)
    elif provider == "ollama":
        return OllamaPlayer(name, model=model_id, **kwargs)
    elif provider == "mock":
        return MockPlayer(name)
    else:
        raise ValueError(f"Unknown provider: {provider}")
