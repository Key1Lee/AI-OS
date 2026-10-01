"""Original synthetic metadata; no authored assessment answers or learner records."""
import json
from importlib.resources import files


def load_artifacts():
    directory = files(__package__).joinpath('commerce')
    return {name: json.loads(directory.joinpath(name).read_text()) for name in
            ['manifest.json', 'run_results.json', 'catalog.json', 'sources.json']}
