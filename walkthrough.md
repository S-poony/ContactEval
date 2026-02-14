ContactEval Benchmark — Implementation Walkthrough
ContactEval is now fully implemented. This walkthrough covers the core components, their functionality, and how to run your first evaluation.

🚀 Quick Start: Run a Mock Tournament
You can verify the entire pipeline (scheduling, orchestrating, scoring, and ranking) locally without API keys using the provided mock players.

bash
# Set PYTHONPATH to the current directory
$env:PYTHONPATH = "."
# Run a small tournament with 1 game per model as attacker
python contacteval/cli.py run --models-file models_mock.json --num-games 1
🏗️ Project Architecture
The project is organized into modular components:

contacteval/game/: Core logic including rules.py (scoring/contacts), models.py (Pydantic schemas), and engine.py (the round-by-round orchestrator).
contacteval/players/: LLM adapters. Use the factory.py to instantiate OpenAI, Anthropic, Google, Ollama, or Mock players.
contacteval/ranking/: The score-based Bayesian Rating System. It handles continuous scores and margin-preserving skill updates.
contacteval/tournament/: Scheduling logic (role rotation) and the main tournament runner.
contacteval/words/: Dictionary and word bank management.
🛠️ Key Features
1. 3-Retry Validation & Auto-Fallback
To prevent infinite loops with local or "stubborn" LLMs, the engine validates every guess. If an LLM fails 3 times (e.g., word doesn't match prefix, already used, or not in dictionary), the engine provides a descriptive error message on retry. On the 4th failure, a random valid word is auto-assigned.

2. Score-Based Bayesian Rating
Instead of win/loss (like ELO/TrueSkill), we use a custom Bayesian system that directly consumes:

Attacker score: Points for contacts (1.0) or full word guesses ($L-K$).
Holder score: Defense ratio (failed rounds / word length).
It separate Attacker and Holder leaderboards as requested.

3. Robust JSON Interaction
The adapters use a robust extraction helper (extract_json) that handles preambles, markdown code blocks, and malformed trailing characters ensuring high reliability even with smaller models.

📊 Viewing the Leaderboard
Results are saved to results/ by default. You can view the current rankings at any time:

bash
python contacteval/cli.py leaderboard
📝 Configuration
To run a real tournament, create a models.json file like this:

json
[
  {
    "name": "GPT-4o",
    "provider": "openai",
    "model_id": "gpt-4o"
  },
  {
    "name": "Claude-3.5-Sonnet",
    "provider": "anthropic",
    "model_id": "claude-3-5-sonnet-20240620"
  },
  {
    "name": "Gemini-1.5-Pro",
    "provider": "google",
    "model_id": "gemini-1.5-pro"
  },
  {
    "name": "Llama-3-Local",
    "provider": "ollama",
    "model_id": "llama3"
  }
]
Ensure you have the required API keys set in your environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).