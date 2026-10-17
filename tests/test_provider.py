import re

import httpx
import pytest

import conftest
from conftest import FakeHttp, Resp
from supadata_extract.provider import SupadataExtractProvider, classify_error

conftest.ENV["SUPADATA_API_KEY"] = "sk-supa-123456"
QUOTA_TRACKER = re.compile(r"usage limit|insufficient credit|error code:\s*402|\b402\b|\b429\b|rate limit exceed|quota exceed|out of credit", re.I)


def prov(*responses):
    p = SupadataExtractProvider()
    p.http = FakeHttp(*responses)
    return p


def test_success():
    p = prov(Resp(200, {"url": "https://e.com/", "content": "# Example\n\ntext", "name": "Example", "description": "d"}))
    r = p.extract(["https://e.com"])[0]
    assert r["title"] == "Example" and r["content"].startswith("# Example")
    assert p.http.calls[0]["headers"]["x-api-key"] == "sk-supa-123456"


@pytest.mark.parametrize("status,body,prefix,tracked", [
    (401, {"error": "unauthorized", "details": "Invalid API Key"}, "auth failed", False),
    (402, {"error": "upgrade-required"}, "auth failed", False),
    (429, {"error": "limit-exceeded", "details": "Plan usage limit was exceeded."}, "quota exceeded", True),
    (429, {"error": "limit-exceeded", "details": "Request rate limit on current plan was exceeded."}, "rate limited", False),
    (404, {"error": "not-found"}, "page not found", False),
    (500, {"error": "internal-error"}, "Supadata server error", False),
])
def test_errors(status, body, prefix, tracked):
    msg = classify_error(status, body, "")
    assert msg.startswith(prefix) and bool(QUOTA_TRACKER.search(msg)) is tracked


def test_empty_content_is_error():
    assert prov(Resp(200, {"content": "  "})).extract(["u"])[0]["error"] == "empty content"


def test_timeout():
    assert prov(httpx.ReadTimeout("t")).extract(["u"])[0]["error"] == "timeout"


def test_target_status_numbers_do_not_trip_quota_tracker():
    from supadata_extract.provider import classify_error as ce
    import inspect
    args = (500, "upstream answered 429 Too Many Requests") if len(inspect.signature(ce).parameters) == 2 else (500, None, "upstream answered 429")
    assert not QUOTA_TRACKER.search(ce(*args))
    args = (418, "teapot 402") if len(inspect.signature(ce).parameters) == 2 else (418, None, "teapot 402")
    assert not QUOTA_TRACKER.search(ce(*args))
