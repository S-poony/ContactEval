ATTACKER_SYSTEM_PROMPT = """
You are playing the word game CONTACT as an Attacker.

RULES:
- The Holder has a secret word. You see the first K letters (the prefix).
- Each round, you and the other Attackers each independently guess a word starting with the prefix.
- If 2+ Attackers guess the SAME word (Contact!), the Holder must guess what that word was.
  - If the Holder guesses correctly: blocked. No letter is revealed.
  - If the Holder guesses wrong: the next letter of the secret word is revealed.
- You may also guess the full secret word at any time.
- Your word must be a common English word. Invalid words will be rejected.

STRATEGY TIPS:
- Pick a word that OTHER Attackers are likely to also think of (you need a match for Contact).
- But pick a word that the HOLDER is unlikely to predict (or the Contact gets blocked).
- Consider guessing the full secret word if you're fairly confident.

Respond in JSON:
{
  "prefix_word": "your word starting with the prefix",
  "full_word_guess": "your guess for the secret word, or null"
}
"""

ATTACKER_USER_TEMPLATE = """
GAME STATE:
Prefix: "{prefix}"
Round: {round_number}

PREVIOUS ROUNDS:
{history}

Respond with your choice for this round.
"""

HOLDER_SYSTEM_PROMPT = """
You are playing the word game CONTACT as the Holder.

RULES:
- You have a secret word: {secret_word}.
- Attackers see the first K letters (the prefix).
- A "Contact" occurred: 2+ Attackers chose the same word, which was not the secret word.
- You must guess what that word is to BLOCK the Contact.
- If you guess correctly, no letter is revealed. 
- If you fail, the next letter is revealed.
- Attackers can also guess the full secret word to win instantly.

Respond in JSON:
{
  "guess": "your single word guess to block the contact"
}
"""

HOLDER_USER_TEMPLATE = """
GAME STATE:
Prefix: "{prefix}"
Round: {round_number}
Number of Contacts to block: {num_contacts}

PREVIOUS ROUNDS:
{history}

What is the word the Attackers converged on?
"""

def format_history(rounds):
    if not rounds:
        return "No previous rounds."
    
    lines = []
    for rd in rounds:
        line = f"Round {rd.round_number} | Prefix \"{rd.prefix}\" | "
        if rd.contacts:
            contact_str = ", ".join([f"Contact on \"{c.word}\"" for c in rd.contacts])
            blocked_str = " | ".join([f"{c.word}: {'Blocked' if c.blocked else 'Failed to block'}" for c in rd.contacts])
            line += f"{contact_str} | {blocked_str}"
        else:
            line += "No contact"
        
        if rd.letter_revealed:
            line += " -> Prefix extended"
        lines.append(line)
    return "\n".join(lines)
