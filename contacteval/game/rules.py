from typing import Iterable
from contacteval.game.models import AttackerSubmission, Contact, GameConfig, Round

def detect_contacts(submissions: list[AttackerSubmission], secret_word: str) -> list[Contact]:
    """
    Identifies words submitted by 2+ attackers that are not the secret word.
    """
    word_counts = {}
    for sub in submissions:
        if sub.prefix_word:
            word = sub.prefix_word.upper()
            if word == secret_word.upper():
                continue  # Secret word doesn't count as a Contact
            if word not in word_counts:
                word_counts[word] = []
            word_counts[word].append(sub.player_id)
    
    contacts = []
    for word, player_ids in word_counts.items():
        if len(player_ids) >= 2:
            contacts.append(Contact(
                word=word,
                attacker_ids=player_ids
            ))
    return contacts

def resolve_round(
    round_num: int,
    prefix: str,
    secret_word: str,
    submissions: list[AttackerSubmission],
    contacts: list[Contact]
) -> Round:
    """
    Determines if a letter is revealed or if the game is won.
    """
    winner = None
    for sub in submissions:
        if sub.full_word_guess and sub.full_word_guess.upper() == secret_word.upper():
            winner = sub.player_id
            break
        if sub.prefix_word and sub.prefix_word.upper() == secret_word.upper():
             winner = sub.player_id
             break

    letter_revealed = False
    if not winner:
        # A letter is revealed if there is at least one successful (unblocked) contact
        for contact in contacts:
            if not contact.blocked:
                letter_revealed = True
                break
    
    return Round(
        round_number=round_num,
        prefix=prefix,
        submissions=submissions,
        contacts=contacts,
        letter_revealed=letter_revealed,
        full_word_guessed_by=winner
    )

def calculate_scores(config: GameConfig, rounds: list[Round]) -> tuple[float, dict[str, float]]:
    """
    Calculates final scores for Holder and Attackers.
    """
    word_len = len(config.word)
    failed_rounds = 0
    attacker_scores = {aid: 0.0 for aid in config.attacker_ids}
    
    for rd in rounds:
        # Holder score logic: count rounds where no letter was revealed and no win occurred
        if not rd.letter_revealed and not rd.full_word_guessed_by:
            failed_rounds += 1
            
        # Attacker score logic
        # 1. Full word guess
        if rd.full_word_guessed_by:
            # Points = L - K (letters revealed so far)
            k = len(rd.prefix)
            points = max(1.0, float(word_len - k))
            attacker_scores[rd.full_word_guessed_by] += points
            
        # 2. Contacts
        if rd.letter_revealed:
            # Any attacker who was part of a successful contact gets 1 point
            # Unless they were auto-assigned the word
            for contact in rd.contacts:
                if not contact.blocked:
                    for pid in contact.attacker_ids:
                        # Check if this player used an auto-assigned word in this round
                        sub = next((s for s in rd.submissions if s.player_id == pid), None)
                        if sub and not sub.auto_assigned:
                            attacker_scores[pid] += 1.0

    holder_score = failed_rounds / word_len
    return holder_score, attacker_scores
