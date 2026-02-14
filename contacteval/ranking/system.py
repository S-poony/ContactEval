import math
from typing import Dict, List, Tuple
from contacteval.game.models import PlayerRating

class BayesianRatingSystem:
    """
    Implements a score-based Bayesian rating system (conjugate Gaussian update).
    Preserves margins and handles continuous scores for both roles.
    """
    
    def __init__(self, noise_variance: float = 4.0):
        # noise_variance (v^2) represents how much a single game's score 
        # might deviate from the player's true skill (higher = slower updates)
        self.noise_variance = noise_variance

    def update_rating(
        self, 
        rating: PlayerRating, 
        observed_score: float, 
        word_difficulty: float = 0.0
    ) -> PlayerRating:
        """
        Updates a single player's rating based on an observed score.
        score_expectation = mu + word_difficulty
        """
        mu = rating.mu
        sigma_sq = rating.sigma ** 2
        
        # 1. Prediction error (residual)
        # Higher score is better. mu represents skill. 
        # word_difficulty > 0 means the word is easier for the role.
        # word_difficulty < 0 means the word is harder.
        residual = observed_score - (mu + word_difficulty)
        
        # 2. Kalman Gain
        # K = P / (P + R) where P is system covariance and R is observation noise
        kalman_gain = sigma_sq / (sigma_sq + self.noise_variance)
        
        # 3. Update mu and sigma
        new_mu = mu + kalman_gain * residual
        new_sigma = math.sqrt(sigma_sq * (1 - kalman_gain))
        
        # 4. Increment games and check provisional status
        new_games_played = rating.games_played + 1
        is_provisional = new_games_played < 30
        
        return PlayerRating(
            player_id=rating.player_id,
            role=rating.role,
            mu=new_mu,
            sigma=new_sigma,
            games_played=new_games_played,
            is_provisional=is_provisional
        )

class DifficultyCalibrator:
    """
    Calibrates word difficulty parameters empirically.
    """
    def __init__(self):
        # word_id -> (role -> total_residual, count)
        self.stats = {}

    def add_observation(self, word_id: str, role: str, residual: float):
        if word_id not in self.stats:
            self.stats[word_id] = {}
        if role not in self.stats[word_id]:
            self.stats[word_id][role] = {"total": 0.0, "count": 0}
        
        self.stats[word_id][role]["total"] += residual
        self.stats[word_id][role]["count"] += 1

    def get_difficulty(self, word_id: str, role: str) -> float:
        """
        Returns the difficulty parameter 'd'.
        d = average residual observed on this word so far for this role.
        Only returns if sufficient data exists (e.g., 10+ games).
        """
        word_stats = self.stats.get(word_id, {}).get(role)
        if word_stats and word_stats["count"] >= 10:
            return word_stats["total"] / word_stats["count"]
        return 0.0
