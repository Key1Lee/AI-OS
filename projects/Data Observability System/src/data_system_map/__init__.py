"""Public consumer facade. Contracts and API adapters are separately importable."""
from pathlib import Path
from .adapters.dbt import ArtifactError
from .contracts import GraphSnapshot
from .security import redact
from .service import DataSystemService


def create_service(database_path: Path, *, seed_demo=False) -> DataSystemService:
    from .repository import MetadataStore
    engine = DataSystemService(MetadataStore(database_path))
    if seed_demo and not any(s['id']=='commerce-demo' for s in engine.systems()):
        from .demo import load_artifacts
        artifacts = load_artifacts()
        engine.import_dbt('commerce-demo','Commerce revenue pipeline',artifacts['manifest.json'],
                          run_results=artifacts['run_results.json'],catalog=artifacts['catalog.json'],freshness=artifacts['sources.json'])
    return engine


__all__ = ['ArtifactError','DataSystemService','GraphSnapshot','create_service','redact']
