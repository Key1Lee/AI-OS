"""Initialize the new database; ingestion remains an explicit secured API operation."""
from app.config import Settings
from app.storage import initialize

if __name__ == "__main__":
    initialize(Settings())
    print("Policy schema initialized")
