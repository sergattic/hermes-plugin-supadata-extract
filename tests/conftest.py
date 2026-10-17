"""Stub Hermes' agent.web_search_provider and load the plugin dir as a package, as Hermes does."""

import importlib.util
import json as _json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {}

if "agent.web_search_provider" not in sys.modules:
    agent = types.ModuleType("agent")
    wsp = types.ModuleType("agent.web_search_provider")

    class WebSearchProvider:
        def is_keyless_available(self):
            return False

    wsp.WebSearchProvider = WebSearchProvider
    wsp.get_provider_env = lambda name: ENV.get(name, "")
    agent.web_search_provider = wsp
    sys.modules["agent"] = agent
    sys.modules["agent.web_search_provider"] = wsp

PKG = ROOT.name.replace("-", "_")
spec = importlib.util.spec_from_file_location(PKG, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
mod = importlib.util.module_from_spec(spec)
sys.modules[PKG] = mod
spec.loader.exec_module(mod)


class Resp:
    def __init__(self, status=200, json_body=None, text="", headers=None):
        self.status_code = status
        self.text = _json.dumps(json_body) if json_body is not None else text
        self.headers = headers or {}

    def json(self):
        return _json.loads(self.text)


class FakeHttp:
    def __init__(self, *responses):
        self.queue, self.calls = list(responses), []

    def get(self, url, **kw):
        self.calls.append({"url": url, **kw})
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
