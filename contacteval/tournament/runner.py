import asyncio
import logging
from typing import Dict, List
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from contacteval.game.engine import GameEngine
from contacteval.game.models import GameConfig, GameResult
from contacteval.players.base import Player
from contacteval.ranking.leaderboard import LeaderboardManager
from contacteval.storage.json_store import JsonStorage
from contacteval.words.bank import Dictionary

logger = logging.getLogger(__name__)

class TournamentRunner:
    """
    Executes a series of games and updates the leaderboard.
    """
    
    def __init__(
        self, 
        players: Dict[str, Player], 
        dictionary: Dictionary, 
        storage: JsonStorage,
        leaderboard: LeaderboardManager
    ):
        self.players = players
        self.dictionary = dictionary
        self.storage = storage
        self.leaderboard = leaderboard
        self.engine = GameEngine(dictionary)

    async def run_tournament(self, configs: List[GameConfig]):
        """
        Runs multiple games concurrently (with rate limiting if needed).
        For now, let's run them sequentially or in small batches to avoid API limits.
        """
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Running games...", total=len(configs))
            
            for config in configs:
                progress.update(task, description=f"[cyan]Game: {config.word}")
                
                try:
                    holder = self.players[config.holder_id]
                    attackers = [self.players[aid] for aid in config.attacker_ids]
                    
                    result = await self.engine.run_game(config, holder, attackers)
                    
                    # Store result
                    self.storage.save_game(result)
                    
                    # Update leaderboard
                    self.leaderboard.process_game(result)
                    self.storage.save_ratings(self.leaderboard.ratings)
                    
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to run game for word {config.word}: {e}")
                
                progress.advance(task)
                
        return results
