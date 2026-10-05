from pathlib import Path
import shutil
import tempfile
import unittest

from py_dev.runtime_config import RuntimeConfigResolver, RuntimeConfigError


class ProjectIdentityTests(unittest.TestCase):
    def test_display_and_stable_names_have_same_config(self):
        resolver=RuntimeConfigResolver()
        self.assertEqual(resolver.resolve(project="Toptal-Testing System").values,resolver.resolve(project="Toptal-Testing").values)
        self.assertEqual(resolver.resolve(project="Northstar").values,resolver.resolve(project="n8n System").values)
        resolver.resolve(project="Semantic & Metrics System")

    def test_path_traversal_rejected(self):
        for name in ("..", ".", "../projects", "foo/bar", "/tmp", "a\0b"):
            with self.assertRaises(RuntimeConfigError):RuntimeConfigResolver().resolve(project=name)

    def test_alias_collision_and_symlink_escape_rejected(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);shutil.copytree(root/"config",tmp/"config")
            (tmp/"projects/One").mkdir(parents=True);(tmp/"projects/Two").mkdir()
            for name in ("One","Two"):
                (tmp/"projects"/name/"aios.toml").write_text('[project]\nname="same"\n')
            with self.assertRaises(RuntimeConfigError):RuntimeConfigResolver(tmp).resolve(project="same")
            (tmp/"projects/Escape").symlink_to(tmp/"config",target_is_directory=True)
            with self.assertRaises(RuntimeConfigError):RuntimeConfigResolver(tmp).resolve(project="Escape")

    def test_unrelated_invalid_config_is_isolated(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);shutil.copytree(root/"config",tmp/"config")
            (tmp/"projects/Good").mkdir(parents=True);(tmp/"projects/Unrelated").mkdir()
            (tmp/"projects/Unrelated/aios.toml").write_text('[broken')
            RuntimeConfigResolver(tmp).resolve(project="Good")
            with self.assertRaises(RuntimeConfigError):RuntimeConfigResolver(tmp).resolve(project="Unrelated")


if __name__=="__main__":unittest.main()
