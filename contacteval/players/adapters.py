import json
import logging
import os
import re
import aiohttp
from contacteval.game.models import AttackerSubmission, Round
from contacteval.players.base import Player
from contacteval.prompts.templates import (
    ATTACKER_SYSTEM_PROMPT,
    ATTACKER_USER_TEMPLATE,
    HOLDER_SYSTEM_PROMPT,
    HOLDER_USER_TEMPLATE,
    format_history
)

logger = logging.getLogger(__name__)

def extract_json(text: str) -> dict:
    """
    Robustly extracts JSON from a string, handling markdown blocks and preambles.
    """
    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 2. Try to find content between ```json and ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # 3. Try to find anything between { and }
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try:
            # Simple balancing check for nested braces could be added here
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    return {}

class LLMPlayer(Player):
    """
    Base class for LLM players with shared logic.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.secret_word = None

    async def submit_attacker_guess(
        self, 
        prefix: str, 
        history: list[Round], 
        error_msg: str | None = None
    ) -> AttackerSubmission:
        history_str = format_history(history)
        if error_msg:
            history_str += f"\n\n🚨 IMPORTANT: {error_msg}"
            
        user_prompt = ATTACKER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            history=history_str
        )
        
        try:
            response_text = await self._call_api(ATTACKER_SYSTEM_PROMPT, user_prompt)
            data = extract_json(response_text)
            return AttackerSubmission(
                player_id=self.name,
                prefix_word=data.get("prefix_word"),
                full_word_guess=data.get("full_word_guess")
            )
        except Exception as e:
            logger.error(f"Error in submit_attacker_guess for {self.name}: {e}")
            return AttackerSubmission(player_id=self.name)

    async def submit_holder_guess(self, prefix: str, history: list[Round], num_contacts: int) -> str:
        if not self.secret_word:
            logger.error(f"Holder {self.name} called without secret_word set")
            return ""

        system_prompt = HOLDER_SYSTEM_PROMPT.format(secret_word=self.secret_word)
        user_prompt = HOLDER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            num_contacts=num_contacts,
            history=format_history(history)
        )
        
        try:
            response_text = await self._call_api(system_prompt, user_prompt)
            data = extract_json(response_text)
            return data.get("guess", "")
        except Exception as e:
            logger.error(f"Error in submit_holder_guess for {self.name}: {e}")
            return ""

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError()

class OpenAIPlayer(LLMPlayer):
    def __init__(self, name: str, model: str = "gpt-4o", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.url = "https://api.openai.com/v1/chat/completions"

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"OpenAI API error: {resp.status} - {text}")
                    return "{}"
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

class AnthropicPlayer(LLMPlayer):
    def __init__(self, name: str, model: str = "claude-3-5-sonnet-20240620", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.url = "https://api.anthropic.com/v1/messages"

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 1024
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Anthropic API error: {resp.status} - {text}")
                    return "{}"
                data = await resp.json()
                return data["content"][0]["text"]

class GeminiPlayer(LLMPlayer):
    def __init__(self, name: str, model: str = "gemini-1.5-flash", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Google API error: {resp.status} - {text}")
                    return "{}"
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

class OllamaPlayer(LLMPlayer):
    def __init__(self, name: str, model: str = "llama3", base_url: str = "http://localhost:11434"):
        super().__init__(name)
        self.model = model
        self.base_url = f"{base_url}/api/chat"

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Ollama API error: {resp.status} - {text}")
                    return "{}"
                data = await resp.json()
                return data["message"]["content"]
