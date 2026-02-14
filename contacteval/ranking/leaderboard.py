from typing import Dict, List, Optional
from contacteval.game.models import GameResult, PlayerRating
from contacteval.ranking.system import BayesianRatingSystem, DifficultyCalibrator

class LeaderboardManager:
    """
    Manages the overall rating state and provides leaderboard views.
    """
    
    def __init__(self):
        self.system = BayesianRatingSystem()
        self.calibrator = DifficultyCalibrator()
        # player_id -> role -> PlayerRating
        self.ratings = {}

    def process_game(self, result: GameResult):
        """
        Processes a single game result and updates ratings.
        """
        word_id = result.config.word.upper()
        
        # 1. Update Holder
        holder_id = result.config.holder_id
        h_rating = self._get_rating(holder_id, "holder")
        h_diff = self.calibrator.get_difficulty(word_id, "holder")
        
        old_h_mu = h_rating.mu
        new_h_rating = self.system.update_rating(h_rating, result.holder_score, h_diff)
        self.ratings[holder_id]["holder"] = new_h_rating
        
        # Log residual for calibration
        self.calibrator.add_observation(word_id, "holder", result.holder_score - old_h_mu)

        # 2. Update Attackers
        for attacker_id, score in result.attacker_scores.items():
            a_rating = self._get_rating(attacker_id, "attacker")
            a_diff = self.calibrator.get_difficulty(word_id, "attacker")
            
            old_a_mu = a_rating.mu
            new_a_rating = self.system.update_rating(a_rating, score, a_diff)
            self.ratings[attacker_id]["attacker"] = new_a_rating
            
            # Log residual for calibration
            self.calibrator.add_observation(word_id, "attacker", score - old_a_mu)

    def _get_rating(self, player_id: str, role: str) -> PlayerRating:
        if player_id not in self.ratings:
            self.ratings[player_id] = {}
        if role not in self.ratings[player_id]:
            self.ratings[player_id][role] = PlayerRating(player_id=player_id, role=role)
        return self.ratings[player_id][role]

    def get_top_players(self, role: str) -> List[PlayerRating]:
        """
        Returns players sorted by conservative rating (mu - 2*sigma).
        """
        players = []
        for pid in self.ratings:
            if role in self.ratings[pid]:
                players.append(self.ratings[pid][role])
        
        # Sort by conservative rating descending
        # Non-provisional players first? Or just sort by rating and mark provisional.
        return sorted(players, key=lambda x: x.display_rating, reverse=True)

    def format_markdown(self, role: str) -> str:
        players = self.get_top_players(role)
        lines = [
            f"### {role.capitalize()} Leaderboard",
            "",
            "| Rank | Model | Rating (μ-2σ) | Skill (μ) | Uncertainty (σ) | Games | Status |",
            "|:---|:---|:---|:---|:---|:---|:---|"
        ]
        
        for i, p in enumerate(players):
            status = "Official" if not p.is_provisional else "Provisional"
            lines.append(
                f"| {i+1} | {p.player_id} | **{p.display_rating:.2f}** | {p.mu:.2f} | {p.sigma:.2f} | {p.games_played} | {status} |"
            )
        
        return "\n".join(lines)
