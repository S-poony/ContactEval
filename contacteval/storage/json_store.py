import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from contacteval.game.models import GameResult, PlayerRating

class JsonStorage:
    """
    Handles persistence of game results and player ratings to JSON files.
    """
    
    def __init__(self, base_path: str = "results"):
        self.base_path = Path(base_path)
        self.games_path = self.base_path / "games"
        self.ratings_path = self.base_path / "ratings.json"
        
        # Ensure directories exist
        self.games_path.mkdir(parents=True, exist_ok=True)

    def save_game(self, result: GameResult):
        filename = f"game_{result.timestamp.strftime('%Y%m%d_%H%M%S')}_{result.config.word}.json"
        file_path = self.games_path / filename
        with open(file_path, 'w') as f:
            f.write(result.model_dump_json(indent=2))

    def load_all_games(self) -> List[GameResult]:
        games = []
        for file in self.games_path.glob("*.json"):
            with open(file, 'r') as f:
                data = json.load(f)
                games.append(GameResult.model_validate(data))
        return games

    def save_ratings(self, ratings: Dict[str, Dict[str, PlayerRating]]):
        """
        Saves the nested ratings dict {player_id: {role: PlayerRating}}.
        """
        # Convert to serializable format
        serializable = {}
        for pid, roles in ratings.items():
            serializable[pid] = {role: r.model_dump() for role, r in roles.items()}
            
        with open(self.ratings_path, 'w') as f:
            json.dump(serializable, f, indent=2)

    def load_ratings(self) -> Dict[str, Dict[str, PlayerRating]]:
        if not self.ratings_path.exists():
            return {}
            
        with open(self.ratings_path, 'r') as f:
            data = json.load(f)
            
        deserialized = {}
        for pid, roles in data.items():
            deserialized[pid] = {role: PlayerRating.model_validate(r) for role, r in roles.items()}
        return deserialized
