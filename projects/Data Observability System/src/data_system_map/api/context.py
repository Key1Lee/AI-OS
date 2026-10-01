from data_system_map import DataSystemService


class MapContext:
    """Consumer extension hooks; the generic router has no learner policy.

    Override view_options to pin a snapshot and choose diagnostic detail. Actions
    are notifications; consumers own their persistence and disclosure rules.
    """
    def __init__(self, engine: DataSystemService):
        self.engine = engine

    def view_options(self, system_id):
        return {'snapshot_id':None,'reveal_diagnostics':True,'audience':'explore'}

    def action(self, system_id, kind, target=None, payload=None):
        pass

    def ensure_import_allowed(self, system_id):
        pass

    def require_explanation(self, system_id):
        pass

    def project_incident(self, value, options):
        return value
