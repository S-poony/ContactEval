import json
import logging
import os
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

class OpenAIPlayer(Player):
    def __init__(self, name: str, model: str = "gpt-4o", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.url = "https://api.openai.com/v1/chat/completions"
        self.secret_word = None # Set by engine when acting as Holder

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

    async def submit_attacker_guess(self, prefix: str, history: list[Round]) -> AttackerSubmission:
        user_prompt = ATTACKER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            history=format_history(history)
        )
        
        try:
            response_text = await self._call_api(ATTACKER_SYSTEM_PROMPT, user_prompt)
            data = json.loads(response_text)
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
            logger.error("Holder called without secret_word set")
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
            data = json.loads(response_text)
            return data.get("guess", "")
        except Exception as e:
            logger.error(f"Error in submit_holder_guess for {self.name}: {e}")
            return ""

class AnthropicPlayer(Player):
    def __init__(self, name: str, model: str = "claude-3-5-sonnet-20240620", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.url = "https://api.anthropic.com/v1/messages"
        self.secret_word = None

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

    async def submit_attacker_guess(self, prefix: str, history: list[Round]) -> AttackerSubmission:
        user_prompt = ATTACKER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            history=format_history(history)
        )
        
        try:
            response_text = await self._call_api(ATTACKER_SYSTEM_PROMPT, user_prompt)
            data = json.loads(response_text)
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
            data = json.loads(response_text)
            return data.get("guess", "")
        except Exception as e:
            logger.error(f"Error in submit_holder_guess for {self.name}: {e}")
            return ""

class GeminiPlayer(Player):
    def __init__(self, name: str, model: str = "gemini-1.5-flash", api_key: str = None):
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        self.secret_word = None

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

    async def submit_attacker_guess(self, prefix: str, history: list[Round]) -> AttackerSubmission:
        user_prompt = ATTACKER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            history=format_history(history)
        )
        
        try:
            response_text = await self._call_api(ATTACKER_SYSTEM_PROMPT, user_prompt)
            data = json.loads(response_text)
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
            data = json.loads(response_text)
            return data.get("guess", "")
        except Exception as e:
            logger.error(f"Error in submit_holder_guess for {self.name}: {e}")
            return ""

class OllamaPlayer(Player):
    def __init__(self, name: str, model: str = "llama3", base_url: str = "http://localhost:11434"):
        super().__init__(name)
        self.model = model
        self.base_url = f"{base_url}/api/chat"
        self.secret_word = None

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

    async def submit_attacker_guess(self, prefix: str, history: list[Round]) -> AttackerSubmission:
        user_prompt = ATTACKER_USER_TEMPLATE.format(
            prefix=prefix,
            round_number=len(history) + 1,
            history=format_history(history)
        )
        
        try:
            response_text = await self._call_api(ATTACKER_SYSTEM_PROMPT, user_prompt)
            data = json.loads(response_text)
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
            data = json.loads(response_text)
            return data.get("guess", "")
        except Exception as e:
            logger.error(f"Error in submit_holder_guess for {self.name}: {e}")
            return ""
