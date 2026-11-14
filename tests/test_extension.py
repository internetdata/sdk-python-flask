"""The extension, through a real Flask request cycle, plus the shared corpus.

A test client connects from ``127.0.0.1``, which is a bogon and is answered locally
without a request. Anything that needs a served answer therefore has to arrive wearing
a public address, through a selector.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
from typing import Any

import httpx
import pytest
from flask import Flask, g, jsonify
from internetdata import InternetData as Client
from internetdata.middleware import Lookup
from internetdata.models import to_result

from internetdata_flask import (
    InternetData,
    block_if,
    default_ip_selector,
    header_ip_selector,
    lookup,
    xff_ip_selector,
)

CORPUS = json.loads(
    (pathlib.Path(__file__).parent.parent / "testdata/testdata.json").read_text()
)
MIDDLEWARE = CORPUS["middleware"]
# Served answers from the lookup corpus: Unlimited's, and a paid plan's.
ANSWERS: dict[str, dict[str, Any]] = {case["name"]: case["body"] for case in CORPUS["lookup"]}
UNLIMITED = ANSWERS["unlimited-answer"]
PAID = ANSWERS["paid-full-shape"]
ELSEWHERE = {**UNLIMITED, "location": {**UNLIMITED["location"], "country": "FR"}}
PUBLIC_IP = PAID["ip"]
EMBARGO = {"location": {"country": ["DE", "AT"]}}


def serving(body: dict[str, Any], *, status: int = 200) -> Client:
    """A client whose every answer is ``body`` for the address asked about, recording
    those addresses."""

    def handle(request: httpx.Request) -> httpx.Response:
        ip = request.url.path.lstrip("/")
        asked.append(ip)
        return httpx.Response(status, json={**body, "ip": ip})

    asked: list[str] = []
    client = Client(cache=False, retries=0, transport=httpx.MockTransport(handle))
    client.asked = asked  # type: ignore[attr-defined]
    return client


def describe() -> Any:
    found = lookup()
    result = found.result if found else None
    return jsonify(
        {
            "ip": found.ip if found else None,
            "country": result.location.country if result else None,
            "is_vpn": result.is_vpn if result else None,
            "is_bogon": result.is_bogon if result else None,
            "error": type(found.error).__name__ if found and found.error else None,
            "attached": found is not None,
        }
    )


def app_with(*, guard: dict[str, Any] | None = None, **options: Any) -> Flask:
    """An app with the extension, whose ``/guarded`` view carries ``block_if(**guard)``."""
    app = Flask(__name__)
    InternetData(app, **options)
    app.route("/", endpoint="index")(describe)
    app.route("/guarded", endpoint="guarded")(
        block_if(**(guard or {"condition": EMBARGO}))(describe)
    )
    return app


def get(
    app: Flask, headers: dict[str, str] | None = None, url: str = "/"
) -> tuple[int, dict[str, Any]]:
    response = app.test_client().get(url, headers=headers or {})
    return response.status_code, response.get_json()


def fixed_ip(_request: Any) -> str:
    return PUBLIC_IP


def test_enriches_the_request_and_leaves_the_decision_to_the_app() -> None:
    client = serving(UNLIMITED)
    status, body = get(app_with(client=client, ip_selector=fixed_ip))
    assert status == 200
    assert body["attached"] is True and body["country"] == "AT" and body["ip"] == PUBLIC_IP
    assert body["is_vpn"] is None, "Unlimited leaves is_vpn out, and absent is not false"
    assert client.asked == [PUBLIC_IP]


def test_blocks_on_a_country_and_the_view_never_runs() -> None:
    status, body = get(
        app_with(client=serving(UNLIMITED), ip_selector=fixed_ip, block_condition=EMBARGO)
    )
    assert status == 403
    assert body == {"error": "access denied"}

    status, _ = get(
        app_with(client=serving(ELSEWHERE), ip_selector=fixed_ip, block_condition=EMBARGO)
    )
    assert status == 200


def test_blocks_on_a_network_type_and_on_anonymity() -> None:
    status, _ = get(
        app_with(
            client=serving(UNLIMITED),
            ip_selector=fixed_ip,
            block_condition={"asn": {"type": "hosting"}},
        )
    )
    assert status == 403, "the network's type is served on every plan"

    status, _ = get(
        app_with(
            client=serving(PAID),
            ip_selector=fixed_ip,
            block_condition=[{"is_tor": True}, {"is_vpn": True}],
        )
    )
    assert status == 403


def test_a_condition_reaches_the_evidence_fields() -> None:
    status, _ = get(
        app_with(
            client=serving(PAID),
            ip_selector=fixed_ip,
            block_condition={"vpn": {"provider": "nordvpn"}},
        )
    )
    assert status == 200, "a different provider must not match"

    status, _ = get(
        app_with(
            client=serving(PAID),
            ip_selector=fixed_ip,
            block_condition={"vpn": {"provider": "MULLVAD"}},
        )
    )
    assert status == 403, "a provider must compare without case"


def test_on_blocked_replaces_the_refusal() -> None:
    app = app_with(
        client=serving(UNLIMITED),
        ip_selector=fixed_ip,
        block_condition=EMBARGO,
        on_blocked=lambda found: (jsonify({"why": found.result.location.country}), 451),
    )
    response = app.test_client().get("/")
    assert response.status_code == 451
    assert response.get_json() == {"why": "AT"}


def test_skip_leaves_the_request_untouched() -> None:
    client = serving(UNLIMITED)
    status, body = get(
        app_with(
            client=client,
            ip_selector=fixed_ip,
            block_condition=EMBARGO,
            skip=lambda request: request.path == "/",
        )
    )
    assert status == 200 and body["attached"] is False
    assert client.asked == []


def test_a_failing_lookup_lets_the_visitor_through() -> None:
    failing = serving({"error": "boom"}, status=500)
    status, body = get(app_with(client=failing, ip_selector=fixed_ip, block_condition=EMBARGO))
    assert status == 200
    assert body["error"] == "InternetDataError"


# The test that matters. Every other assertion here would pass whether or not the
# selector is right, because a direct connection has nothing to confuse.
def test_a_forged_x_forwarded_for_is_ignored_by_default() -> None:
    client = serving(UNLIMITED)
    _, body = get(app_with(client=client), {"X-Forwarded-For": PUBLIC_IP})
    assert body["ip"] == "127.0.0.1", "remote_addr is the socket peer; the header is a forgery"
    assert client.asked == [], "and a bogon is answered locally, so nothing was asked"

    explicit = serving(UNLIMITED)
    _, body = get(
        app_with(client=explicit, ip_selector=xff_ip_selector()), {"X-Forwarded-For": PUBLIC_IP}
    )
    assert body["ip"] == PUBLIC_IP
    assert explicit.asked == [PUBLIC_IP]


def test_a_header_selector_reads_the_edge_that_writes_it() -> None:
    client = serving(UNLIMITED)
    _, body = get(
        app_with(client=client, ip_selector=header_ip_selector("CF-Connecting-IP")),
        {"CF-Connecting-IP": "45.83.91.9"},
    )
    assert body["ip"] == "45.83.91.9"
    assert client.asked == ["45.83.91.9"]


def test_depth_counts_trusted_hops_from_the_right() -> None:
    client = serving(UNLIMITED)
    get(
        app_with(client=client, ip_selector=xff_ip_selector(1)),
        {"X-Forwarded-For": f"{PUBLIC_IP}, 70.41.3.18, 150.172.238.178"},
    )
    assert client.asked == ["150.172.238.178"]


def test_a_private_client_address_is_answered_locally_and_never_blocks() -> None:
    client = serving(UNLIMITED)
    status, body = get(
        app_with(
            client=client,
            block_condition={"asn": {"type": "hosting"}},
            ip_selector=default_ip_selector,
        )
    )
    assert status == 200, "local development must not lock you out of your own app"
    assert body["is_bogon"] is True
    assert client.asked == []


def test_a_condition_that_constrains_nothing_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="constrains nothing"):
        InternetData(block_condition={"is_vpn": False})


@pytest.mark.parametrize("case", MIDDLEWARE["conditions"], ids=lambda c: c["name"])
def test_corpus_conditions(case: dict[str, Any]) -> None:
    ip = case.get("bogon") or case["body"]["ip"]
    client = serving(case.get("body") or {})
    warnings: list[str] = []
    status, _ = get(
        app_with(
            client=client,
            ip_selector=lambda _request, ip=ip: ip,
            block_condition=case["condition"],
            on_warn=warnings.append,
        )
    )
    assert status == (403 if case["expect"]["blocked"] else 200), case["why"]
    reported = [w for w in warnings if "does not include" in w]
    assert len(reported) == (1 if case["expect"]["missing"] else 0), case["why"]
    for member in case["expect"]["missing"]:
        assert member in reported[0], case["why"]


def test_block_if_refuses_only_the_view_it_decorates() -> None:
    client = serving(UNLIMITED)
    app = app_with(client=client, ip_selector=fixed_ip)
    status, body = get(app, url="/guarded")
    assert status == 403
    assert body == {"error": "access denied"}
    status, body = get(app)
    assert status == 200, "the extension itself has no condition, so other views are open"
    assert body["country"] == "AT"
    assert client.asked == [PUBLIC_IP, PUBLIC_IP], (
        "one lookup per request, none by the decorator"
    )

    status, body = get(
        app_with(client=serving(ELSEWHERE), ip_selector=fixed_ip), url="/guarded"
    )
    assert status == 200
    assert body["attached"] is True


def test_block_if_on_blocked_replaces_the_refusal() -> None:
    def refuse(found: Any) -> Any:
        return jsonify({"why": found.result.location.country}), 451

    app = app_with(
        client=serving(UNLIMITED),
        ip_selector=fixed_ip,
        guard={"condition": EMBARGO, "on_blocked": refuse},
    )
    status, body = get(app, url="/guarded")
    assert status == 451
    assert body == {"why": "AT"}


def test_block_if_lets_a_skipped_request_through() -> None:
    client = serving(UNLIMITED)
    app = app_with(client=client, ip_selector=fixed_ip, skip=lambda request: True)
    status, body = get(app, url="/guarded")
    assert status == 200
    assert body["attached"] is False
    assert client.asked == []


def test_block_if_fails_open_unless_told_to_fail_closed() -> None:
    failing = serving({"error": "boom"}, status=500)
    status, body = get(app_with(client=failing, ip_selector=fixed_ip), url="/guarded")
    assert status == 200
    assert body["error"] == "InternetDataError"

    closed = app_with(
        client=failing,
        ip_selector=fixed_ip,
        guard={"condition": EMBARGO, "fail_closed": True},
    )
    status, body = get(closed, url="/guarded")
    assert status == 403
    assert body == {"error": "access denied"}


def test_block_if_without_the_extension_is_an_error() -> None:
    app = Flask(__name__)
    app.testing = True
    app.route("/guarded")(block_if(EMBARGO)(describe))
    with pytest.raises(RuntimeError, match="register the InternetData extension"):
        app.test_client().get("/guarded")


def test_block_if_refuses_a_condition_that_constrains_nothing() -> None:
    with pytest.raises(ValueError, match="constrains nothing"):
        block_if({"is_vpn": False})(describe)


def test_block_if_warns_once_naming_the_view() -> None:
    warnings: list[str] = []
    app = app_with(
        client=serving(UNLIMITED),
        ip_selector=fixed_ip,
        guard={"condition": {"location": {"city": "Vienna"}}, "on_warn": warnings.append},
    )
    get(app, url="/guarded")
    get(app, url="/guarded")
    assert len(warnings) == 1
    assert warnings[0].startswith("block_if on describe names location.city")


# Flask runs an async view only with its async extra installed, so the wrapper is driven
# directly here, inside a request the extension has already looked up.
def test_block_if_guards_an_async_view() -> None:
    async def checkout() -> str:
        return "served"

    guarded = block_if(EMBARGO)(checkout)
    assert asyncio.iscoroutinefunction(guarded)
    app = app_with()
    for body, expected in ((UNLIMITED, 403), (ELSEWHERE, 200)):
        with app.test_request_context("/"):
            g.internetdata = Lookup(blocked=False, ip=PUBLIC_IP, result=to_result(body))
            answer = asyncio.run(guarded())
            status = answer.status_code if expected == 403 else 200
            assert status == expected
            assert (answer == "served") is (expected == 200)


@pytest.mark.parametrize("case", MIDDLEWARE["conditions"], ids=lambda c: c["name"])
def test_corpus_conditions_through_block_if(case: dict[str, Any]) -> None:
    ip = case.get("bogon") or case["body"]["ip"]
    client = serving(case.get("body") or {})
    warnings: list[str] = []
    app = app_with(
        client=client,
        ip_selector=lambda _request, ip=ip: ip,
        guard={"condition": case["condition"], "on_warn": warnings.append},
    )
    status, _ = get(app, url="/guarded")
    assert status == (403 if case["expect"]["blocked"] else 200), case["why"]
    reported = [w for w in warnings if "does not include" in w]
    assert len(reported) == (1 if case["expect"]["missing"] else 0), case["why"]
    for member in case["expect"]["missing"]:
        assert member in reported[0], case["why"]


# Built exactly as the README builds it: the key from the environment and nothing else.
# Every other test hands the extension a client, so none of them could see a core that
# cannot start from a key alone. The test client's loopback peer is a bogon, answered
# with no request.
@pytest.mark.parametrize("key", ["a-key", None])
def test_the_extension_starts_the_way_the_readme_builds_it(
    monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    if key is None:
        monkeypatch.delenv("INTERNETDATA_API_KEY", raising=False)
    else:
        monkeypatch.setenv("INTERNETDATA_API_KEY", key)
    status, body = get(app_with(api_key=os.environ.get("INTERNETDATA_API_KEY")))

    assert status == 200
    assert body["attached"] is True
    assert body["is_bogon"] is True
    assert body["error"] is None


# The README's extension again, served a PUBLIC peer with a forged X-Forwarded-For: the key
# must reach the API when it is set and no Authorization go out when it is not, and the
# socket address must be the one looked up. The test above is answered with no request, so
# it passed with the key dropped. httpx's own transport answers for the API's host alone,
# so nothing leaves the machine.
@pytest.mark.parametrize("key", ["a-key", None])
def test_the_readme_extension_sends_its_key_for_a_public_peer(
    monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    sent: list[tuple[str, str | None]] = []

    def handle(_transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.internetdata.io":
            raise httpx.ConnectError("only the API's host answers here", request=request)
        sent.append((request.url.path, request.headers.get("Authorization")))
        return httpx.Response(200, json={**UNLIMITED, "ip": PUBLIC_IP})

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    if key is None:
        monkeypatch.delenv("INTERNETDATA_API_KEY", raising=False)
    else:
        monkeypatch.setenv("INTERNETDATA_API_KEY", key)
    app = app_with(api_key=os.environ.get("INTERNETDATA_API_KEY"))
    response = app.test_client().get(
        "/", headers={"X-Forwarded-For": "1.1.1.1"}, environ_base={"REMOTE_ADDR": PUBLIC_IP}
    )
    status, body = response.status_code, response.get_json()

    assert status == 200
    assert body["ip"] == PUBLIC_IP, "the socket peer is looked up; the header is a forgery"
    assert body["error"] is None and body["country"] == "AT"
    assert len(sent) == 1 and sent[0][0].endswith(PUBLIC_IP)
    assert sent[0][1] == (f"Bearer {key}" if key else None)
