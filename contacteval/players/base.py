from abc import ABC, abstractmethod
from contacteval.game.models import AttackerSubmission, Round

class Player(ABC):
    """
    Abstract base class for any LLM player in ContactEval.
    Contributors implement this to add new models.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def submit_attacker_guess(
        self,
        prefix: str,
        history: list[Round],
        error_msg: str | None = None,
    ) -> AttackerSubmission:
        """
        Attacker role: submit a word starting with prefix, or guess the full secret word.
        """
        pass

    @abstractmethod
    async def submit_holder_guess(
        self,
        prefix: str,
        history: list[Round],
        num_contacts: int,
    ) -> str:
        """
        Holder role: guess the contact word.
        """
        pass
