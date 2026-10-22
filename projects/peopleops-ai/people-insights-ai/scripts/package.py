"""Package the runnable demo without its environment, caches or local secrets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", ".git", ".pytest_cache", ".ruff_cache", "__pycache__", "dist"}


def main():
    directory = ROOT / "dist"
    directory.mkdir(exist_ok=True)
    archive = directory / "people-insights-ai.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or EXCLUDED.intersection(relative.parts):
                continue
            if path.name == ".env" or path.suffix in (".pyc", ".log"):
                continue
            bundle.write(path, Path("people-insights-ai") / relative)
    with ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise SystemExit("Archive validation failed")
        assert "people-insights-ai/data/ibm_hr.csv" in bundle.namelist()
        assert not any(
            "/.venv/" in name or name.endswith("/.env") for name in bundle.namelist()
        )
    print(f"{archive} ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
