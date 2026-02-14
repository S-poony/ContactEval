from datetime import datetime
from pydantic import BaseModel, Field

class GameConfig(BaseModel):
    word: str                    # The secret word (imposed)
    holder_id: str               # Model acting as Holder
    attacker_ids: list[str]      # Models acting as Attackers
    max_holder_guesses: int = 1  # Holder gets exactly one guess per contact
    dictionary_id: str           # Which word bank version

class AttackerSubmission(BaseModel):
    player_id: str
    prefix_word: str | None = None      # Word starting with prefix
    full_word_guess: str | None = None  # Guess for secret word
    auto_assigned: bool = False         # True if word was assigned after 3 failed guesses

class Contact(BaseModel):
    word: str
    attacker_ids: list[str]      # Who submitted this word
    holder_guess: str | None = None     # Holder's single guess
    blocked: bool = False               # Did holder guess correctly?

class Round(BaseModel):
    round_number: int
    prefix: str                  # Prefix at start of round
    submissions: list[AttackerSubmission]
    contacts: list[Contact]
    letter_revealed: bool        # Did prefix grow this round?
    full_word_guessed_by: str | None = None  # Winner, if any

class GameResult(BaseModel):
    config: GameConfig
    rounds: list[Round]
    winner: str | None = None           # Attacker who guessed the word
    holder_score: float                 # failed_rounds / word_length
    attacker_scores: dict[str, float]   # player_id -> total points
    duration_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)

class PlayerRating(BaseModel):
    player_id: str
    role: str                    # "attacker" or "holder"
    mu: float = 0.0              # Skill estimate
    sigma: float = 5.0           # Uncertainty
    games_played: int = 0
    is_provisional: bool = True  # True until 30+ games

    @property
    def display_rating(self) -> float:
        return self.mu - 2 * self.sigma
