import itertools
import random
from typing import List, Tuple
from contacteval.game.models import GameConfig

class TournamentScheduler:
    """
    Generates game configurations for a tournament with role rotation.
    """
    
    def __init__(self, model_ids: List[str], dictionary_id: str):
        self.model_ids = model_ids
        self.dictionary_id = dictionary_id

    def generate_games(self, words: List[str], games_per_model_as_attacker: int = 30) -> List[GameConfig]:
        """
        Creates a list of GameConfigs such that each model plays the Attacker role 
        approximately the requested number of times, rotating through all models.
        """
        if len(self.model_ids) < 4:
            raise ValueError("Need at least 4 models for a standard 3 v 1 game.")

        configs = []
        # Total attacker slots needed = N_models * games_per_model_as_attacker
        # Games needed = total_slots / 3
        total_games = (len(self.model_ids) * games_per_model_as_attacker) // 3
        
        # Round-robin combinations
        # We pick 1 holder and 3 attackers from N models
        combinations = list(itertools.permutations(self.model_ids, 4))
        random.shuffle(combinations)
        
        # Cycle through words and combinations
        for i in range(total_games):
            word = words[i % len(words)]
            combo = combinations[i % len(combinations)]
            
            configs.append(GameConfig(
                word=word,
                holder_id=combo[0],
                attacker_ids=list(combo[1:]),
                dictionary_id=self.dictionary_id
            ))
            
        return configs
