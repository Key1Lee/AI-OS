import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from py_dev.config import ModelSettings
from py_dev.decision_config import DecisionSettings
from py_dev.models import ProviderResult
from py_dev.provider_health import provider_health


class HealthTests(unittest.TestCase):
    def test_keys_and_sdks_do_not_prove_authentication(self):
        with patch.dict(os.environ,{"OPENAI_API_KEY":"secret"}), patch("importlib.util.find_spec",return_value=object()):
            result=provider_health(settings=ModelSettings(openai_enabled=True,openai_model="configured"),decision_settings=DecisionSettings())
        self.assertTrue(result["openai"]["configured"])
        self.assertTrue(result["openai"]["credential_present"])
        self.assertIsNone(result["openai"]["authenticated"])
        self.assertFalse(result["openai"]["tested"])
        self.assertFalse(result["openai"]["available"])
        self.assertNotIn("secret",str(result))

    def test_local_generation_failure_cannot_be_available(self):
        report=NS(model_alias="requested")
        with patch("py_dev.local_runtime.inspect_local",return_value=report), patch("py_dev.providers.qwen_local.QwenLocalProvider.generate",side_effect=RuntimeError()):
            result=provider_health(settings=ModelSettings(qwen_model="requested"),decision_settings=DecisionSettings(),probe=True)
        self.assertFalse(result["qwen_local"]["available"])
        self.assertFalse(result["qwen_local"]["tested"])

    def test_same_endpoint_and_model_are_inspected_and_executed(self):
        observed=[]
        def inspect(config,**kwargs):
            observed.append((config.get("runtime","endpoint"),config.get("runtime","model")))
            return NS(model_alias="requested")
        settings=ModelSettings(qwen_model="requested",qwen_base_url="http://127.0.0.1:19999/v1")
        with patch("py_dev.local_runtime.inspect_local",side_effect=inspect),patch("py_dev.providers.qwen_local.QwenLocalProvider.generate",return_value=ProviderResult('{"ready":true}',"requested","stop",1)) as generate:
            result=provider_health(settings=settings,decision_settings=DecisionSettings(),probe=True)
        self.assertEqual(observed,[(settings.qwen_base_url,"requested")])
        self.assertTrue(result["qwen_local"]["available"])
        self.assertEqual(generate.call_count,1)

    def test_wrong_returned_model_cannot_claim_tested(self):
        with patch("py_dev.local_runtime.inspect_local",return_value=NS(model_alias="requested")),patch("py_dev.providers.qwen_local.QwenLocalProvider.generate",return_value=ProviderResult('{"ready":true}',"unrequested","stop",1)):
            result=provider_health(settings=ModelSettings(qwen_model="requested"),decision_settings=DecisionSettings(),probe=True)
        self.assertFalse(result["qwen_local"]["tested"])


if __name__=="__main__":unittest.main()
