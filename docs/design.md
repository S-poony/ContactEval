# ContactEval — Technical Design Document

*Version 0.1 — Draft*

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Game Specification](#2-game-specification)
3. [Scoring System](#3-scoring-system)
4. [Rating System](#4-rating-system)
5. [Architecture & Infrastructure](#5-architecture--infrastructure)
6. [Open Contribution Model](#6-open-contribution-model)
7. [Word Bank Design](#7-word-bank-design)
8. [Prompt Design](#8-prompt-design)
9. [Data Model](#9-data-model)
10. [Future Directions](#10-future-directions)

---

## 1. Motivation

### 1.1 The Limits of Static Benchmarks

The current generation of LLM benchmarks suffers from three structural weaknesses:

**Saturation.** Models increasingly score near-perfect on benchmarks like MMLU, GSM8K, and HumanEval. Once a benchmark saturates, it loses discriminative power. ContactEval's adversarial, multiplayer nature means performance is relative to opponents — it cannot saturate.

**Contamination.** Static benchmarks can be (and are) inadvertently or intentionally included in training data. ContactEval games are generated dynamically — every game is unique, and optimal play depends on your specific opponents.

**Surface-level evaluation.** Most benchmarks test pattern matching and knowledge retrieval. They do not measure the ability to *model other agents* — a capability widely considered central to general intelligence in cognitive science (see: [Theory of Mind](https://en.wikipedia.org/wiki/Theory_of_mind), [Metacognition](https://en.wikipedia.org/wiki/Metacognition)).

### 1.2 Why Word Games?

Word games have a long history as tests of intelligence, from crossword puzzles to Scrabble tournaments. The game of Contact is particularly interesting because it requires a rare combination of skills:

| Skill | Relevance to General Intelligence |
|:---|:---|
| **Convergent social reasoning** | "What word will *other agents* think of?" Requires modeling the knowledge, biases, and reasoning patterns of others. |
| **Adversarial thinking** | The Holder is actively trying to predict and block you. You must think about what your opponent *thinks you'll think*. |
| **Constrained creativity** | As obvious words get exhausted, players must find increasingly creative solutions within strict constraints. |
| **Bayesian deduction** | Each revealed letter updates the probability space of possible secret words. Strong players maintain and update these probabilities. |
| **Risk assessment** | Guessing the full word early is high-reward but high-risk. Timing this correctly requires calibrated confidence. |

These skills map directly to capabilities that matter in real-world AI applications: negotiation, strategic planning, collaborative problem-solving, and robust generalization.

### 1.3 Why Multiplayer?

Single-player and pairwise benchmarks miss the dynamics of multi-agent interaction. In ContactEval:

- **Attackers must coordinate without communicating** — they need to independently converge on the same word, which requires predicting what other models are likely to guess.
- **The Holder must model a group** — predicting the most likely convergence point among multiple opponents.
- **Group composition matters** — a model's performance changes depending on who it's playing with, creating rich, non-trivial rating dynamics.

---

## 2. Game Specification

### 2.1 Setup

| Parameter | Value |
|:---|:---|
| Players per game | 1 Holder + 3 Attackers |
| Secret word source | Assigned from curated dictionary (not chosen by Holder) |
| Initial information | First letter of the secret word |
| Valid guesses | Must be a word in the game's dictionary, must not have been guessed before in this game |
| Game end condition | An Attacker correctly guesses the full secret word |

### 2.2 Round Structure

Each round proceeds as follows:

**Step 1 — Attacker Submissions.** Each Attacker independently submits:
- A dictionary word starting with the currently revealed prefix, **or**
- A guess for the full secret word

All submissions are simultaneous (no Attacker sees another's submission before committing).

**Step 2 — Contact Detection.** If two or more Attackers submitted the same word, a *Contact* is established for that word. Multiple distinct Contacts can occur in the same round.

**Step 3 — Full Word Check.** If any Attacker correctly guessed the secret word, the game ends immediately. The Holder does not get to respond.

**Step 4 — Holder Defense.** For each Contact, the Holder is informed that a Contact exists (but not what the word is) and submits **exactly one guess** to identify the Contact word.

**Step 5 — Resolution.**
- For each Contact: if the Holder guessed the word → *Blocked* (no letter reveal). If not → *Successful Contact* (one letter is revealed).
- If no Contact was established → *Failed round* (no letter reveal, no block).
- If multiple Contacts exist in the same round, the Holder submits one guess per Contact. Only one additional letter is revealed regardless of how many Contacts succeed.

**Step 6 — Update.** The full round history (all submissions, contacts, blocks, reveals) is appended to the game log. All players see this history in subsequent rounds.

### 2.3 Termination

The game ends when:
- An Attacker guesses the full secret word (**normal end**), or
- All letters of the secret word have been revealed and an Attacker submits it (**revealed end**)

There is no "Holder wins" condition. The Holder's performance is measured by *how long* they delayed the inevitable.

### 2.4 Infinite Loop Prevention

Rather than imposing a maximum number of attempts per prefix, we prevent infinite loops structurally:

1. All guesses must be valid dictionary words starting with the current prefix
2. No word may be guessed twice in the same game
3. The dictionary is finite → the pool of legal guesses shrinks every round
4. The secret word is in the dictionary — as the pool shrinks, attackers will inevitably find it

---

## 3. Scoring System

### 3.1 Attacker Scoring

Each Attacker accumulates points within a single game:

| Action | Points | Rationale |
|:---|:---|:---|
| Part of a successful Contact (unblocked) | **1** | Contributed to revealing one letter |
| Part of a blocked Contact | **0** | The attempt was neutralized |
| Submitted a word with no Contact | **0** | No impact on game state |
| Correctly guessed the full word at position K (out of L letters) | **L − K** | Equivalent to skipping L−K letter reveals |
| Part of a Contact via auto-assigned word | **0** | Word was assigned by the system, not chosen by the player |

**Why L − K for full word guesses?**

A successful Contact reveals one letter — it advances the game by exactly one step. Guessing the full word from position K skips all remaining L − K steps. Therefore, a correct full-word guess is worth exactly L − K Contacts.

This creates the right incentive structure:
- Guessing "ELEPHANT" after seeing only "E" (K=1, L=8) → **7 points** (extremely impressive)
- Guessing "ELEPHANT" after seeing "ELEPHAN" (K=7, L=8) → **1 point** (nearly trivial)
- A successful Contact → **1 point** (solid contribution)

### 3.2 Holder Scoring

The Holder's score for a single game:

```
holder_score = total_failed_rounds / word_length
```

Where `total_failed_rounds` = rounds where attackers failed to make contact or contact was blocked. Higher score = stronger defense. A score of 3.0 means the Holder forced 3× as many failed attempts as the word has letters.

### 3.3 Per-Game Attacker Ranking

After a game, Attackers are ranked by total points (ties broken by fewer total submissions — efficiency matters). This ranking is the input to the rating system.

---

## 4. Rating System

### 4.1 Why Not ELO or TrueSkill?

ContactEval is a **point-based game**, not a win/loss game. Each attacker earns a continuous score (0 to L−1). Each holder earns a continuous defense score. Traditional rating systems are a poor fit:

| System | Problem for ContactEval |
|:---|:---|
| **ELO** | Designed for 1v1 win/loss. No multiplayer support, no uncertainty tracking. |
| **Glicko-2** | Better than ELO (tracks uncertainty), but still 1v1 win/loss. |
| **TrueSkill** | Supports multiplayer, but expects **rankings** (1st/2nd/3rd), not scores. Converting points to rankings discards margin information: scoring 7 vs 6 is treated the same as 7 vs 0. |

### 4.2 Score-Based Bayesian Rating

Instead, we use a **custom Bayesian system** that works directly with point scores.

#### Model

Each player has a skill estimate represented as a Gaussian: **N(μ, σ²)**

- **μ** (mu): Estimated skill level. Starts at 0.
- **σ** (sigma): Uncertainty. Starts high (~5.0), shrinks with each game.
- **Conservative rating**: μ − 2σ. Used for leaderboard ranking.

Each word has a **difficulty parameter** `d`, calibrated empirically.

#### Update Rule

After a game, we observe each attacker's score `s`. The update is:

```
residual     = s - (μ + d)            # How much better/worse than expected
kalman_gain  = σ² / (σ² + v²)         # How much to trust the observation (v = noise variance)

μ_new = μ + kalman_gain × residual    # Shift skill toward observed performance
σ_new = σ × sqrt(1 - kalman_gain)     # Shrink uncertainty
```

This is a **conjugate Gaussian update** — the same math that powers Kalman filters. It's ~10 lines of code, well-understood, and uses raw scores instead of discarding them into rankings.

#### Key Properties

| Property | How it works |
|:---|:---|
| **Margin-preserving** | Scoring 7 vs 0 produces a very different update than 7 vs 6 |
| **Uncertainty-aware** | New models start with wide σ (low confidence). σ shrinks with data. |
| **Word difficulty built-in** | The `d` parameter absorbs word-level effects, so ratings are fair across different words |
| **Works for both roles** | Attacker scores and Holder scores are both continuous — same update rule applies |
| **Provisional ratings** | Models with high σ are flagged as provisional until σ drops below a threshold |

### 4.3 Word Difficulty Calibration

Some words are inherently harder to defend or attack. The difficulty parameter `d` is calibrated empirically:

1. Initially, all words start with `d = 0`
2. After ≥ 10 games on a word, `d` is updated to the average residual across all players on that word
3. This means: if all players score low on "RHYTHM", `d` shifts negative (hard word), and future low scores on it don't unfairly penalize players

### 4.4 Minimum Games Threshold

A model must play at least **30 games** to appear on the official leaderboard. Until then, it appears in a "Provisional" tier with its current μ ± σ displayed.

### 4.5 Separate Attacker and Holder Ratings

The Holder role involves a different cognitive layer: instead of *"What word fits this prefix?"* it's *"What word will these specific opponents converge on?"*. This meta-reasoning is related but distinct.

ContactEval maintains **two separate leaderboards**:

| Leaderboard | Measures | Input Signal |
|:---|:---|:---|
| **Attacker Leaderboard** | Convergent reasoning, deduction, creativity | Per-game attacker points (contacts + word guesses) |
| **Holder Leaderboard** | Meta-prediction, adversarial blocking | Per-game holder score (failed_rounds / word_length) |

Both use the same Bayesian update rule. A model may rank differently on each leaderboard — that's expected and informative.

### 4.6 Cost Estimation

#### Per-Game Token Usage

A typical game lasts ~12–20 rounds. With 3 Attackers and 1 Holder, each round produces:
- **3 Attacker API calls** (one per attacker, always)
- **~0.4 Holder API calls** on average (only called when a Contact occurs; estimated ~40% of rounds)

Prompt size grows as history accumulates:

| Round | Avg Input Tokens (per call) | Output Tokens (per call) |
|:---|:---|:---|
| Round 1 | ~400 | ~50 |
| Round 8 | ~1,200 | ~50 |
| Round 15 | ~2,000 | ~50 |
| **Weighted average** | **~1,000** | **~50** |

**Per-game totals** (assuming 15 rounds):
- Total API calls: 15 × 3.4 ≈ **51 calls**
- Total input tokens: ~51,000
- Total output tokens: ~2,550

#### Per-Game Cost by Model Tier

| Model | Input $/1M | Output $/1M | Cost per Game | Notes |
|:---|:---|:---|:---|:---|
| GPT-4o | $2.50 | $10.00 | **~$0.15** | Premium tier |
| Claude Sonnet | $3.00 | $15.00 | **~$0.19** | Premium tier |
| GPT-4o-mini | $0.15 | $0.60 | **~$0.009** | Budget tier |
| Gemini Flash | $0.10 | $0.40 | **~$0.006** | Budget tier |
| Claude Haiku | $0.80 | $4.00 | **~$0.05** | Mid tier |
| Llama 3 (Ollama) | Free | Free | **$0** | Local, requires GPU |

> Prices are approximate and based on early 2025 public pricing. Actual costs may vary.

#### Games Needed for Confident Ratings

Bayesian σ (uncertainty) decreases with each game:

| Games Played | Approximate σ | Confidence Level |
|:---|:---|:---|
| 5 | ~6.0 | Very low — directional only |
| 15 | ~4.0 | Low — rough ranking |
| **30** | **~2.5** | **Moderate — leaderboard-ready** |
| 50 | ~1.8 | High — stable ranking |
| 100 | ~1.2 | Very high — definitive |

**Minimum for leaderboard**: 30 games as Attacker.

With **4 models** in a round-robin (each game = 3 Attackers + 1 Holder, rotating):
- Each game gives 3 models one Attacker data point
- To get 30 Attacker games per model: **30 × 4 / 3 = 40 total games**

#### Budget Scenarios (4 Models, 40 Games to Confident Ratings)

| Scenario | Models | Total Cost | Time (est.) |
|:---|:---|:---|:---|
| **All premium** | 4× GPT-4o | ~$6.00 | ~3 hours |
| **Mixed** | 2× premium + 2× budget | ~$3.50 | ~3 hours |
| **All budget** | 4× GPT-4o-mini | ~$0.36 | ~3 hours |
| **Local only** | 4× Llama 3 (Ollama) | **$0** | ~6 hours (depends on GPU) |

> Time estimates assume ~5 min per game with API latency. Local models may be slower depending on hardware.

---

## 5. Architecture & Infrastructure

### 5.1 Design Principles

| Principle | Implementation |
|:---|:---|
| **Contributor-friendly** | Simple adapter interface; adding a model is ~30 lines of Python |
| **Auditable** | Full prompt/response traces in every game log |
| **Portable** | No database required; JSON files for everything |
| **Web-ready** | Pydantic models serialize cleanly to JSON; CLI output is structured |
| **Async-first** | All LLM calls are async — attacker submissions run concurrently |

### 5.2 Project Structure

```
ContactEval/
├── contacteval/
│   ├── __init__.py
│   ├── game/
│   │   ├── engine.py           # Async game loop orchestrator
│   │   ├── rules.py            # Contact detection, blocking, validation
│   │   ├── state.py            # Game state machine (prefix, history, legal moves)
│   │   └── models.py           # Pydantic data models
│   ├── players/
│   │   ├── base.py             # Abstract Player interface
│   │   ├── openai.py           # OpenAI API adapter
│   │   ├── anthropic.py        # Anthropic API adapter
│   │   ├── google.py           # Google Gemini adapter
│   │   └── ollama.py           # Local models via Ollama
│   ├── prompts/
│   │   ├── holder.py           # Holder prompt construction
│   │   └── attacker.py         # Attacker prompt construction
│   ├── ranking/
│   │   ├── system.py           # Bayesian rating + difficulty calibration
│   │   └── leaderboard.py      # Leaderboard rendering (JSON, Markdown)
│   ├── tournament/
│   │   ├── scheduler.py        # Round-robin scheduling with role rotation
│   │   └── runner.py           # Async tournament execution
│   ├── words/
│   │   └── bank.py             # Word list loading, filtering, difficulty tags
│   └── storage/
│       └── json_store.py       # File-based storage for games and ratings
├── data/
│   └── words_en.json           # Curated English word list
├── results/                    # Output directory for game logs and leaderboards
├── cli.py                      # CLI entry point (Typer)
└── tests/
```

### 5.3 Player Interface

The core abstraction that enables open contribution:

```python
from abc import ABC, abstractmethod
from contacteval.game.models import Round

class Player(ABC):
    """Interface for any LLM to participate in ContactEval."""

    name: str  # Display name, e.g. "gpt-4o"

    @abstractmethod
    async def submit_attacker_guess(
        self,
        prefix: str,
        history: list[Round],
    ) -> AttackerSubmission:
        """
        Attacker role: submit a word starting with `prefix` 
        from `available_words`, or guess the full secret word.
        
        Returns an AttackerSubmission with either a prefix_word 
        or a full_word_guess (or both).
        """
        ...

    @abstractmethod
    async def submit_holder_guess(
        self,
        prefix: str,
        history: list[Round],
        num_contacts: int,
    ) -> str:
        """
        Holder role: guess the contact word.
        
        Returns your single guess for what the 
        Attackers converged on.
        """
        ...
```

A contributor adds a new model by subclassing `Player` and implementing these two methods.

### 5.4 Technology Choices

| Component | Choice | Rationale |
|:---|:---|:---|
| Language | **Python 3.11+** | Standard for ML/AI; rich async; contributors already know it |
| Data models | **Pydantic v2** | Typed, validated, JSON-serializable; future API-ready |
| Async runtime | **asyncio** | Native Python; LLM API calls are I/O bound |
| CLI framework | **Typer** | Clean, typed CLI from the same data models |
| Rating system | **Custom Bayesian** | Score-based; preserves margins; ~10 lines of core math |
| Storage | **JSON files** | Zero dependencies; easy migration to SQLite or Postgres |
| Testing | **pytest + pytest-asyncio** | Standard Python testing stack |

### 5.5 Preparing for Web

While web is not Phase 1, the architecture is designed for easy migration:

- **Pydantic models** → direct FastAPI request/response schemas
- **JSON storage** → swap `json_store.py` for a database adapter
- **Leaderboard generation** → already outputs structured JSON
- **Game logs** → already contain all data needed for replays and visualization
- **CLI commands** → map 1:1 to API endpoints

When the time comes, adding a FastAPI server + a simple frontend is a clean layering exercise, not a rewrite.

---

## 6. Open Contribution Model

### 6.1 How It Works

```
Contributor                         ContactEval
    │                                    │
    │  pip install contacteval           │
    │  ──────────────────────────────►   │
    │                                    │
    │  Implement Player adapter          │
    │  (30 lines of Python)              │
    │                                    │
    │  contacteval play \                │
    │    --attackers my-model ...         │
    │  ──────────────────────────────►   │
    │                                    │
    │  Game runs locally                 │
    │  (using contributor's API keys)    │
    │                                    │
    │  Game log produced (JSON)          │
    │  ◄──────────────────────────────   │
    │                                    │
    │  Submit log via CLI or PR          │
    │  ──────────────────────────────►   │
    │                                    │
    │  Log verified, ratings updated     │
    │  ◄──────────────────────────────   │
```

### 6.2 Trust & Verification

Since games run on contributor machines, we need to trust the results. Our approach:

1. **Full trace logging**: Every game log includes the exact prompts sent and raw responses received. Anyone can audit.
2. **Deterministic replay**: Given the same prompts and a temperature=0 setting, games can be reproduced.
3. **Statistical validation**: Anomalous results (outlier win rates, suspiciously fast games) are flagged for review.
4. **Community auditing**: Game logs are public. The community can spot and report irregularities.
5. **Hash chains**: Each game log is hashed; the hash references prior games. Tampering with history is detectable.

### 6.3 Contribution Paths

| Contribution | Effort | Impact |
|:---|:---|:---|
| Run games with existing models | Low | Expands game data, refines ratings |
| Add new model adapter | Low-Medium | Brings a new model to the leaderboard |
| Curate word bank | Low | Improves game quality and difficulty calibration |
| Improve prompts | Medium | Better prompts → more signal per game |
| Improve rating system | High | More accurate and fair rankings |

---

## 7. Word Bank Design

### 7.1 Requirements

The word bank is a curated list of English words that serve as secret words for the Holder. Quality here directly impacts benchmark quality.

| Criterion | Rationale |
|:---|:---|
| Common enough that educated humans know them | Prevents trivial Holder wins from obscurity |
| Long enough to produce interesting games (5+ letters) | Short words end too quickly |
| No proper nouns | Reduces ambiguity |
| Tagged with difficulty metadata | Enables difficulty normalization |
| Minimum ~500 words for sufficient variety | Prevents memorization effects |

### 7.2 Difficulty Classification

Words are tagged with estimated difficulty based on:

- **Length** (longer = more possible prefixes = more rounds)
- **Frequency** (rarer words are harder to guess)
- **Prefix ambiguity** (words with common prefixes like "con-" are harder — many words share the prefix)
- **Letter distribution** (words with uncommon letter sequences narrow faster)

Initial difficulty tags are heuristic. They are recalibrated empirically as game data accumulates.

### 7.3 Dictionary for Attacker Guesses

Attackers choose from a broader dictionary (~10,000–50,000 common English words). This dictionary is shared across all players and filtered in real-time to exclude already-used words.

**Validation strategy**: LLMs guess freely. The server validates each guess against the dictionary.

| Attempt | What happens |
|:---|:---|
| Valid word | Accepted |
| Invalid word (1st–2nd fail) | Re-prompt: *"[WORD] is not in the dictionary. Please try again."* |
| Invalid word (3rd fail) | **Auto-assign**: a random valid word is chosen for the player |

Auto-assigned words participate in Contact detection normally (to keep the game moving), but the player who received the auto-word **earns no points** from it — even if it results in a successful Contact. Other players who independently chose the same word still earn their points.

---

## 8. Prompt Design

### 8.1 Principles

Prompt design is critical for fair evaluation. Our principles:

1. **Identical instructions for identical roles** — all Attackers get the same template
2. **No hidden advantages** — all game-relevant information is in the prompt
3. **Full history** — every prior round's submissions, contacts, and blocks are included
4. **Clear output format** — structured output (JSON) to minimize parsing errors
5. **Role-aware strategy hints** — light guidance on what makes a good guess (without biasing toward specific strategies)
6. **No word list** — LLMs guess freely; invalid guesses are rejected with a re-prompt (max 3 retries, then auto-assigned)

### 8.2 Example: Attacker Prompt

```text
You are playing the word game CONTACT as an Attacker.

RULES:
- The Holder has a secret word. You see the first K letters (the prefix).
- Each round, you and the other Attackers each independently guess a word 
  starting with the prefix.
- If 2+ Attackers guess the SAME word (Contact!), the Holder must guess 
  what that word was.
  - If the Holder guesses correctly: blocked. No letter is revealed.
  - If the Holder guesses wrong: the next letter of the secret word is revealed.
- You may also guess the full secret word at any time.
- Your word must be a common English word. Invalid words will be rejected.

GAME STATE:
Prefix: "ELE"
Round: 5
Previous rounds:
  Round 1 | Prefix "E" | You guessed "EAGLE" | Contact with Player_B on "EAGLE" | Blocked by Holder
  Round 2 | Prefix "E" | You guessed "ENGINE" | No contact
  Round 3 | Prefix "E" | You guessed "EMBER" | Contact with Player_C on "EMBER" | Holder failed to block → Prefix extended
  Round 4 | Prefix "EL" | You guessed "ELBOW" | Contact with Player_B on "ELBOW" | Holder failed to block → Prefix extended
  ...

STRATEGY TIPS:
- Pick a word that OTHER Attackers are likely to also think of (you need a match for Contact)
- But pick a word that the HOLDER is unlikely to predict (or the Contact gets blocked)
- Consider guessing the full secret word if you're fairly confident

Respond in JSON:
{
  "prefix_word": "your word starting with the prefix",
  "full_word_guess": "your guess for the secret word, or null"
}
```

### 8.3 Example: Holder Prompt

```text
You are playing the word game CONTACT as the Holder.

Your secret word is: ELEPHANT
Revealed prefix: "ELE"

RULES:
- The Attackers have submitted words starting with the prefix.
- A "Contact" occurred: 2+ Attackers chose the same word, which was not the secret word.
- You must guess what that word is to BLOCK the Contact.
- If you guess correctly, no letter is revealed. 
- If you fail, the next letter is revealed.

You have 1 guess. The Contact word starts with "ELE" and is in the game's dictionary.

Previous rounds:
  Round 1 | Prefix "E" | Contact word was "EAGLE" | You guessed: "EAGLE" → Blocked ✓
  Round 2 | Prefix "E" | Contact word was "EMBER" | You guessed: "ENGINE" → Failed ✗
  ...

STRATEGY TIPS:
- Think: what is the most "obvious" word starting with this prefix?
- Consider what words the Attackers have been gravitating toward
- Words already used cannot be reused, so eliminate those

Respond in JSON:
{
  "guess": "your_single_guess"
}
```

---

## 9. Data Model

### 9.1 Core Types

```python
class GameConfig(BaseModel):
    word: str                    # The secret word (imposed)
    holder_id: str               # Model acting as Holder
    attacker_ids: list[str]      # Models acting as Attackers
    max_holder_guesses: int = 1  # Holder gets exactly one guess per contact
    dictionary_id: str           # Which word bank version

class AttackerSubmission(BaseModel):
    player_id: str
    prefix_word: str | None      # Word starting with prefix
    full_word_guess: str | None  # Guess for secret word
    auto_assigned: bool = False  # True if word was assigned after 3 failed guesses

class Contact(BaseModel):
    word: str
    attacker_ids: list[str]      # Who submitted this word
    holder_guess: str            # Holder's single guess
    blocked: bool                # Did holder guess correctly?

class Round(BaseModel):
    round_number: int
    prefix: str                  # Prefix at start of round
    submissions: list[AttackerSubmission]
    contacts: list[Contact]
    letter_revealed: bool        # Did prefix grow this round?
    full_word_guessed_by: str | None  # Winner, if any

class GameResult(BaseModel):
    config: GameConfig
    rounds: list[Round]
    winner: str | None           # Attacker who guessed the word
    holder_score: float          # failed_rounds / word_length
    attacker_scores: dict[str, float]  # player_id → total points
    duration_seconds: float
    timestamp: datetime
```

### 9.2 Rating State

```python
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
```

---

## 10. Future Directions

### 10.1 Multilingual Support
Curate word banks in French, Spanish, German, etc. This tests whether models can play Contact in languages other than English — a strong signal for true multilingual reasoning (not just translation).

### 10.2 Cross-Model Teams
Instead of all Attackers being different models, have *teams* of the same model. This tests whether a model can coordinate with copies of itself — a form of self-modeling.

### 10.3 Web Arena
A hosted platform where models are registered via API endpoints and games run continuously. Includes a live leaderboard, game replay viewer, and match history.

### 10.4 Composite Rating
Once both leaderboards are stable, explore a weighted composite rating that captures a model's overall Contact ability across both roles.

### 10.5 Difficulty Progression
Adaptive word selection that matches word difficulty to player skill levels, similar to computerized adaptive testing (CAT). This produces more informative games and faster rating convergence.

### 10.6 Human Participation
Allow humans to play as Attackers or Holders against LLMs. This provides a powerful calibration anchor: how does model performance compare to human social reasoning?

---

*This is a living document. It will be updated as the project evolves.*
