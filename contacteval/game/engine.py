import asyncio
import random
import time
from typing import List
from contacteval.game.models import (
    AttackerSubmission, 
    Contact, 
    GameConfig, 
    GameResult, 
    Round
)
from contacteval.game.rules import detect_contacts, resolve_round, calculate_scores
from contacteval.players.base import Player

class GameEngine:
    """
    Orchestrates a single game of ContactEval.
    """
    
    def __init__(self, dictionary):
        self.dictionary = dictionary

    async def run_game(self, config: GameConfig, holder: Player, attackers: List[Player]) -> GameResult:
        # Initialize holder with the secret word
        holder.secret_word = config.word

        start_time = time.time()
        rounds = []
        current_prefix = config.word[0].upper()
        used_words = set()
        
        while True:
            round_num = len(rounds) + 1
            
            # 1. Attacker submissions (with retries)
            submissions = await self._get_attacker_submissions(
                attackers, current_prefix, rounds, used_words
            )
            
            # Update used words
            for sub in submissions:
                if sub.prefix_word:
                    used_words.add(sub.prefix_word.upper())
            
            # 2. Detect contacts
            contacts = detect_contacts(submissions, config.word)
            
            # 3. Holder defense (for each contact)
            for contact in contacts:
                # Holder gets 1 guess per contact
                guess = await holder.submit_holder_guess(
                    current_prefix, rounds, len(contacts)
                )
                contact.holder_guess = guess
                if guess and guess.upper() == contact.word.upper():
                    contact.blocked = True
            
            # 4. Resolve round
            current_round = resolve_round(
                round_num, current_prefix, config.word, submissions, contacts
            )
            rounds.append(current_round)
            
            # Check for game end
            if current_round.full_word_guessed_by:
                break
                
            # Update prefix if a letter was revealed
            if current_round.letter_revealed:
                next_len = len(current_prefix) + 1
                if next_len <= len(config.word):
                    current_prefix = config.word[:next_len].upper()
                else:
                    # Should not happen if word length is handled correctly
                    break
            
            # Natural termination if all letters revealed and it's guessed
            if current_prefix == config.word.upper():
                # One last "Revealed end" round if not already won
                # This logic is handled by resolve_round checking for secret_word guess
                pass

        # Calculate final scores
        holder_score, attacker_scores = calculate_scores(config, rounds)
        
        return GameResult(
            config=config,
            rounds=rounds,
            winner=rounds[-1].full_word_guessed_by,
            holder_score=holder_score,
            attacker_scores=attacker_scores,
            duration_seconds=time.time() - start_time
        )

    async def _get_attacker_submissions(
        self, 
        attackers: List[Player], 
        prefix: str, 
        history: List[Round],
        used_words: set
    ) -> List[AttackerSubmission]:
        
        tasks = [
            self._get_single_attacker_submission(a, prefix, history, used_words)
            for a in attackers
        ]
        return await asyncio.gather(*tasks)

    async def _get_single_attacker_submission(
        self, 
        attacker: Player, 
        prefix: str, 
        history: List[Round],
        used_words: set
    ) -> AttackerSubmission:
        
        for attempt in range(3):
            submission = await attacker.submit_attacker_guess(prefix, history)
            
            # Validation
            word = submission.prefix_word
            if word:
                word_upper = word.upper()
                is_valid = (
                    word_upper.startswith(prefix.upper()) and 
                    self.dictionary.is_valid(word_upper) and 
                    word_upper not in used_words
                )
                if is_valid:
                    return submission
                
                # If invalid, the re-prompting/retry logic would normally happen in the Player adapter
                # OR we could handle it here if we want the engine to manage retries.
                # The user said: "3 times to guess a valid word ... picks a valid word at random"
            elif submission.full_word_guess:
                # Full word guesses don't necessarily need to be in the dictionary? 
                # Actually they should, but let's be more lenient or validate them too.
                return submission
            else:
                # No word provided?
                pass
                
        # Fallback to random word
        random_word = self.dictionary.get_random_word(prefix, exclude=used_words)
        return AttackerSubmission(
            player_id=attacker.name,
            prefix_word=random_word,
            auto_assigned=True
        )
