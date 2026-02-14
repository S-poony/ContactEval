<p align="center">
  <h1 align="center">🎯 ContactEval</h1>
  <p align="center">
    <strong>A multiplayer word game benchmark for evaluating LLM intelligence</strong>
  </p>
  <p align="center">
    <a href="#why-contacteval">Why</a> •
    <a href="#the-game">The Game</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#quickstart">Quickstart</a> •
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

## The Problem with Current Benchmarks

Most LLM benchmarks test **what a model knows**. MMLU checks factual recall. HumanEval checks code generation. They are static, they saturate, and they can be gamed by training on the test set.

None of them test what may be the deepest marker of general intelligence: **the ability to model what another agent is thinking**.

## Why ContactEval

ContactEval turns the classic party game [Contact](https://en.wikipedia.org/wiki/Contact_(word_game)) into a continuous, adversarial LLM benchmark. It measures capabilities that no existing benchmark captures:

| Capability | How ContactEval Tests It |
|:---|:---|
| **Theory of Mind** | Can you predict what word another LLM will guess? |
| **Strategic Reasoning** | Can you choose a word that's likely enough for others to match, but obscure enough that the defender can't predict it? |
| **Deductive Reasoning** | Given a growing prefix, can you narrow down the secret word? |
| **Creativity under Constraints** | Can you find the right word when the obvious ones are exhausted? |

### Key advantages over static benchmarks

- **🔄 Dynamic** — Performance depends on who you're playing against. Ratings never saturate.
- **🛡️ Ungameable** — You can't memorize answers because the game is adversarial and live.
- **📊 Continuous** — Models can be re-evaluated endlessly, producing ever-more-precise ratings.
- **🌍 Open** — Anyone can run games with their own models and API keys, then submit results to the public leaderboard.

---

## The Game

Contact is a word game typically played at parties. One player knows a secret word and progressively reveals its letters. The others try to guess it. Here's how we've adapted it for LLMs:

### Roles

| Role | Who | Goal |
|:---|:---|:---|
| **Holder** | 1 LLM | Defend a secret word by predicting what the Attackers will guess |
| **Attackers** | 3 LLMs | Force the Holder to reveal letters, then guess the secret word |

> The word is **assigned** to the Holder — we evaluate the guessing game, not word selection.

### A Round of Contact

```
Secret word: ELEPHANT          Revealed prefix: EL
                                              ─────
Attacker A  →  "ELBOW"     ┐
Attacker B  →  "ELBOW"     ├─ Contact! Two attackers picked the same word.
Attacker C  →  "ELEVATOR"  ┘

Holder gets ONE guess to identify the contact word...
  Holder guesses "ELECTRIC" → Wrong!

✨ New letter revealed:  E L E
```

**Contact** happens when two or more Attackers independently choose the same word. The Holder gets **one guess** to identify it. If the Holder fails — a new letter is revealed. If the Holder succeeds — the guess is blocked, and Attackers must try again with the same prefix.

### Full Game Flow

1. A word from the dictionary is assigned to the Holder. The first letter is revealed.
2. Each Attacker independently submits a dictionary word starting with the revealed prefix.
3. **Contact?**
   - **Yes** (2+ Attackers chose the same word) → Holder gets **one guess**.
     - Holder correct → *Blocked*. Same prefix, try again.
     - Holder wrong → *Letter revealed*. Prefix grows by one.
   - **No** → Same prefix, try again.
4. Attackers may also guess the **full secret word** at any point.
5. The game ends when the secret word is guessed.

All guesses must be valid dictionary words that haven't been used before in the current game. This naturally prevents infinite loops and generates rich data at every step.

### Why This Design is Intelligent

The beauty of Contact is that **being random doesn't work**. If you guess an obscure word, no other Attacker will match you — no Contact, no progress. If you guess the most obvious word, the Holder will predict it and block you. 

The sweet spot — finding a word that's *predictable enough* for your allies but *surprising enough* for your opponent — is exactly the kind of social reasoning that distinguishes truly intelligent systems.

---

## How It Works

### Scoring

**Attackers** earn points for contributions to the game:

| Action | Points | Why |
|:---|:---|:---|
| Part of a successful Contact (letter revealed) | **1** | You helped reveal one letter |
| Guessed the full word at position K out of L | **L − K** | Equivalent to skipping (L−K) letter reveals |

Guessing "ELEPHANT" after only seeing "EL" (K=2, L=8) is worth **6 points** — you effectively skipped 6 rounds of play. Guessing it after seeing "ELEPHAN" (K=7) is worth only **1 point**.

**Holders** are scored by how long they held the word: `failed_guesses / word_length`. A Holder who forces 24 failed attempts on an 8-letter word scores 3.0 — they made the game three times harder than the baseline.

### Rating System

We use a **custom score-based Bayesian rating** designed specifically for ContactEval. Unlike ELO or TrueSkill (which expect win/loss or rankings), our system works directly with **raw point scores** — preserving the full signal from every game.

Each model's rating is a Gaussian distribution (μ ± σ):
- **μ** (mu) = estimated skill level
- **σ** (sigma) = uncertainty (shrinks as the model plays more games)
- **Display rating** = μ − 2σ (conservative estimate)

Attacker and Holder ratings are tracked on **separate leaderboards** — they test different cognitive skills. Word difficulty is calibrated automatically as game data accumulates.

### Open & Decentralized

ContactEval is designed so **anyone can participate**:

1. Install the Python package
2. Add your model (implement a simple adapter interface — ~30 lines of code)
3. Run games locally with your own API keys
4. Submit game logs to the public leaderboard

All game logs include full prompt/response traces, making results auditable and reproducible. No central server required.

---

## Architecture

```
ContactEval/
├── contacteval/
│   ├── game/          # Core engine: rules, state machine, game loop
│   ├── players/       # LLM adapters (OpenAI, Anthropic, Google, Ollama, ...)
│   ├── prompts/       # Prompt templates for each role
│   ├── ranking/       # TrueSkill implementation + leaderboard
│   ├── tournament/    # Match scheduling and async execution
│   ├── words/         # Word bank management
│   └── storage/       # JSON storage (designed for easy DB migration)
├── data/              # Curated word lists
├── results/           # Game logs and ratings
├── cli.py             # Command-line interface
└── tests/
```

**Tech stack**: Python, async/await, Pydantic models, custom Bayesian rating. No heavy frameworks — designed for contributors to jump in quickly.

---

## Quickstart

> 🚧 **Coming soon** — The game engine is under active development.

```bash
# Install
pip install contacteval

# Run a game
contacteval play --attackers gpt-4o claude-sonnet gemini-flash --holder gpt-4o-mini

# View leaderboard
contacteval leaderboard
```

---

## Contributing

ContactEval is built to be community-driven. Here's how you can help:

### Add a New Model
Implement the `Player` interface (~30 lines of Python) to connect any LLM:

```python
class MyModelPlayer(Player):
    async def guess_word(self, prefix: str, history: list[Round]) -> str:
        # Call your model's API and return a word
        ...
```

### Run Games
Run games between models using your own API keys and submit the logs. Every game contributes to the global leaderboard.

### Improve the Benchmark
- Curate the word bank (add words, tag difficulty)
- Refine prompt templates
- Improve the rating system
- Add support for new languages

---

## Philosophy

We believe the next frontier of AI evaluation is **social intelligence** — not what a model knows, but how well it can reason about the reasoning of others. Contact is a deceptively simple game that creates a rich testbed for this capability.

By making ContactEval open, decentralized, and continuously running, we aim to create a living benchmark that evolves with the models it evaluates.

---

## License

MIT — Use it, fork it, build on it.
