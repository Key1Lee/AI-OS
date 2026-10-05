"""Independent browser smoke server with disposable metadata."""
from pathlib import Path
from tempfile import TemporaryDirectory
import uvicorn
from data_system_map.api.main import create_app
from data_system_map.config import Settings

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix='observability-e2e-') as temporary:
        app=create_app(Settings(database_path=Path(temporary)/'metadata.db',web_dist=root/'web/dist'))
        uvicorn.run(app,host='127.0.0.1',port=8124,access_log=False)
