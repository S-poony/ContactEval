import json
import random
from typing import Set

class Dictionary:
    """
    Manages the word bank and provides validation/random selection.
    """
    
    def __init__(self, words: list[str]):
        # Store as uppercase for consistent comparison
        self.all_words = {w.upper() for w in words}
        # Pre-index by prefix for efficiency (optional, but good for large lists)
        self._prefix_index = {}
        for w in self.all_words:
            for i in range(1, len(w) + 1):
                prefix = w[:i]
                if prefix not in self._prefix_index:
                    self._prefix_index[prefix] = []
                self._prefix_index[prefix].append(w)

    @classmethod
    def from_file(cls, filepath: str):
        with open(filepath, 'r') as f:
            words = json.load(f)
        return cls(words)

    def is_valid(self, word: str) -> bool:
        return word.upper() in self.all_words

    def get_matches(self, prefix: str, exclude: Set[str] = None) -> list[str]:
        exclude = exclude or set()
        prefix = prefix.upper()
        matches = self._prefix_index.get(prefix, [])
        return [m for m in matches if m not in exclude]

    def get_random_word(self, prefix: str, exclude: Set[str] = None) -> str | None:
        matches = self.get_matches(prefix, exclude)
        if not matches:
            return None
        return random.choice(matches)
