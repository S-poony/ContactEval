import asyncio
import json
import logging
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from contacteval.players.factory import create_player
from contacteval.ranking.leaderboard import LeaderboardManager
from contacteval.storage.json_store import JsonStorage
from contacteval.tournament.runner import TournamentRunner
from contacteval.tournament.scheduler import TournamentScheduler
from contacteval.words.bank import Dictionary

app = typer.Typer(help="ContactEval: A multiplayer word game benchmark for LLMs.")
console = Console()

@app.command()
def run(
    models_file: str = typer.Option("models.json", help="Path to models configuration"),
    dictionary_file: str = typer.Option("data/words_en.json", help="Path to word dictionary"),
    num_games: int = typer.Option(10, help="Number of games to run per model as attacker"),
    results_dir: str = typer.Option("results", help="Directory for results")
):
    """
    Runs a tournament among the specified models.
    """
    asyncio.run(_async_run(models_file, dictionary_file, num_games, results_dir))

async def _async_run(models_file, dictionary_file, num_games, results_dir):
    # 1. Load configuration
    try:
        with open(models_file, "r") as f:
            model_configs = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: {models_file} not found. Create a models.json file.[/red]")
        return

    # 2. Setup storage and leaderboard
    storage = JsonStorage(results_dir)
    leaderboard = LeaderboardManager()
    leaderboard.ratings = storage.load_ratings()  # Resume from previous if exists

    # 3. Initialize players
    players = {}
    for m in model_configs:
        try:
            players[m["name"]] = create_player(m["name"], m["provider"], m["model_id"])
        except Exception as e:
            console.print(f"[yellow]Warning: Could not initialize player {m['name']}: {e}[/yellow]")

    if len(players) < 4:
        console.print("[red]Error: Need at least 4 models to run a tournament.[/red]")
        return

    # 4. Load Dictionary
    dictionary = Dictionary.from_file(dictionary_file)
    with open(dictionary_file, "r") as f:
        all_words = json.load(f)

    # 5. Schedule games
    scheduler = TournamentScheduler(list(players.keys()), "en_v1")
    # For a real tournament, avoid using the same words too often
    configs = scheduler.generate_games(all_words, games_per_model_as_attacker=num_games)

    # 6. Run tournament
    runner = TournamentRunner(players, dictionary, storage, leaderboard)
    await runner.run_tournament(configs)

    console.print("[green]Tournament completed![/green]")
    _print_leaderboards(leaderboard)

@app.command()
def leaderboard(results_dir: str = typer.Option("results", help="Directory for results")):
    """
    Displays the current leaderboards.
    """
    storage = JsonStorage(results_dir)
    manager = LeaderboardManager()
    manager.ratings = storage.load_ratings()
    _print_leaderboards(manager)

def _print_leaderboards(manager):
    for role in ["attacker", "holder"]:
        players = manager.get_top_players(role)
        table = Table(title=f"{role.capitalize()} Leaderboard")
        table.add_column("Rank", justify="right")
        table.add_column("Model", style="cyan")
        table.add_column("Rating (μ-2σ)", style="bold green")
        table.add_column("Skill (μ)", justify="right")
        table.add_column("Uncertainty (σ)", justify="right")
        table.add_column("Games", justify="right")
        table.add_column("Status")

        for i, p in enumerate(players):
            status = "Official" if not p.is_provisional else "[yellow]Provisional[/yellow]"
            table.add_row(
                str(i + 1),
                p.player_id,
                f"{p.display_rating:.2f}",
                f"{p.mu:.2f}",
                f"{p.sigma:.2f}",
                str(p.games_played),
                status
            )
        console.print(table)

if __name__ == "__main__":
    app()
