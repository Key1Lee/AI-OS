from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from trainer.config import Settings
from trainer.exercises.bank import Bank
from trainer.repositories.store import Store

settings=Settings.from_env()
store=Store(settings.database_path)
store.migrate()
bank=Bank(settings.root)
store.seed(bank)
print(f"Validated and seeded {len(bank.exercises)} exercise versions; learner evidence preserved.")
