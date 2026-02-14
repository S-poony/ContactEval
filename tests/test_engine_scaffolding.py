import asyncio
import json
from contacteval.game.engine import GameEngine
from contacteval.game.models import GameConfig, AttackerSubmission
from contacteval.players.base import Player
from contacteval.words.bank import Dictionary

class MockPlayer(Player):
    def __init__(self, name: str, strategy: dict):
        super().__init__(name)
        self.strategy = strategy  # round -> guess

    async def submit_attacker_guess(self, prefix: str, history: list) -> AttackerSubmission:
        round_num = len(history) + 1
        guess = self.strategy.get(round_num, {}).get("attacker")
        if isinstance(guess, str):
            if "guess_secret" in guess:
                return AttackerSubmission(player_id=self.name, full_word_guess=guess.split(":")[1])
            return AttackerSubmission(player_id=self.name, prefix_word=guess)
        return AttackerSubmission(player_id=self.name, prefix_word=f"{prefix}X") # Default invalid

    async def submit_holder_guess(self, prefix: str, history: list, num_contacts: int) -> str:
        round_num = len(history) + 1
        return self.strategy.get(round_num, {}).get("holder", "")

async def test_simple_game():
    with open("data/words_en.json", "r") as f:
        words = json.load(f)
    dictionary = Dictionary(words)
    engine = GameEngine(dictionary)
    
    # Secret word: ELEPHANT
    config = GameConfig(
        word="ELEPHANT",
        holder_id="H1",
        attacker_ids=["A1", "A2", "A3"],
        dictionary_id="en_v1"
    )
    
    # Strategies to trigger a contact and a win
    # Round 1: A1 & A2 guess EAGLE (Contact), Holder fails
    # Round 2: A1 & A3 guess ELBOW (Contact), Holder fails
    # Round 3: A1 guesses ELEPHANT (Win)
    p1 = MockPlayer("A1", {
        1: {"attacker": "EAGLE"},
        2: {"attacker": "ELBOW"},
        3: {"attacker": "guess_secret:ELEPHANT"}
    })
    p2 = MockPlayer("A2", {
        1: {"attacker": "EAGLE"},
        2: {"attacker": "ELEVATOR"}
    })
    p3 = MockPlayer("A3", {
        1: {"attacker": "ENGINE"},
        2: {"attacker": "ELBOW"}
    })
    holder = MockPlayer("H1", {
        1: {"holder": "ENGINE"}, # Wrong guess
        2: {"holder": "WRONG"}   # Wrong guess
    })
    
    result = await engine.run_game(config, holder, [p1, p2, p3])
    
    print(f"Game Over!")
    print(f"Winner: {result.winner}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Holder Score: {result.holder_score}")
    print(f"Attacker Scores: {result.attacker_scores}")
    
    # Assertions
    assert result.winner == "A1"
    assert len(result.rounds) == 3
    assert result.rounds[0].letter_revealed is True # EAGLE matched
    assert result.rounds[1].letter_revealed is True # ELBOW matched

if __name__ == "__main__":
    asyncio.run(test_simple_game())
