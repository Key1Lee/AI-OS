"""Browser smoke server with an ephemeral profile, never learner evidence."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import uvicorn

from apps.api.main import create_app
from trainer.config import ROOT,Settings


if __name__ == "__main__":
    (ROOT/'data').mkdir(exist_ok=True)
    with TemporaryDirectory(prefix='ae-e2e-',dir=ROOT/'data') as temporary:
        application=create_app(Settings(database_path=Path(temporary)/'smoke.db'))
        uvicorn.run(application,host='127.0.0.1',port=8123,access_log=False)
