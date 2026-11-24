# [<img src="https://s3.internetdata.io/internetdata-public/brand/mark.svg" alt="InternetData" height="28"/>](https://internetdata.io/) InternetData Flask Extension

[![PyPI](https://img.shields.io/pypi/v/internetdata-flask.svg)](https://pypi.org/project/internetdata-flask/)
[![license](https://img.shields.io/pypi/l/internetdata-flask.svg)](LICENSE)

The official [Flask](https://flask.palletsprojects.com) extension for the [InternetData](https://internetdata.io) API.

It looks up the visitor behind each request, where they are, which network they come from and whether it's a VPN, a proxy, Tor or a hosting server, and hands the answer to your views. Blocking is opt-in.

## Getting Started

```bash
pip install internetdata-flask
```

Requires Python 3.11 or newer and Flask 3.0 or newer.

Without an API key a lookup is on Unlimited, the free plan: the country, the network and the company behind the address, Tor, relay, bot, anycast, carrier and satellite space and the service flags, with no daily or monthly cap. Every lookup your app makes comes from your server's one address, though, so a busy site will see bursts refused. A paid plan answers every field, VPN, the proxy flags, hosting, CDN and the city among them; create a key in the [console](https://app.internetdata.io). A free account tries every field.

```python
from flask import Flask
from internetdata_flask import InternetData

app = Flask(__name__)
InternetData(app, api_key=os.environ.get("INTERNETDATA_API_KEY"))
```

`init_app(app)` is supported for the application-factory pattern.

```python
from internetdata_flask import lookup


@app.route("/")
def index():
    found = lookup()
    country = found.result.location.country_name if found and found.result else "somewhere"
    return f"Hello, visitor from {country}"
```

By default nothing is blocked. Every request gets an answer and your own code decides what it means: a currency to show, a sign-up to review, a page to keep from some countries. A request your `skip` claims gets no answer, and `lookup()` is `None` for it.

## Blocking

Pass a `block_condition` and a matching request is answered with `403` and never reaches your views.

```python
InternetData(
    app,
    api_key=os.environ.get("INTERNETDATA_API_KEY"),
    block_condition={"location": {"country": ["CU", "IR", "KP"]}},
)
```

A condition is written in the shape of a result, keyed by the same names the API uses, and only the members you name are considered, so it can refuse on anything in the answer. The country works on every plan, and so do the first three of these:

```python
{"asn": {"type": "hosting"}}  # the network's type
[{"is_anycast": True}, {"is_satellite": True}]  # anycast and satellite space
{"is_bot": True}  # crawlers, monitors and scanners
[{"is_hosting": True}, {"is_cdn": True}]  # traffic from servers, not people
[{"is_vpn": True}, {"is_tor": True}, {"is_resproxy": True}]  # anonymity: a list is OR
{"is_vpn": True, "vpn": {"provider": "nordvpn"}}  # one provider
{"resproxy": {"hits": {"gte": 5}}}  # a numeric threshold
```

Values are matched by equality, strings without regard to case. A list means any-of. A member the answer holds as a list, such as `web`'s rows or `pubproxy`'s `protocols`, matches when any one element does: `{"web": {"port": 443}}`. A dict of `gte`/`gt`/`lte`/`lt` compares numbers, and every bound you give must hold, so two of them are a range. Members set to `False` or `None` are ignored, so a condition states the signals you act on; one that constrains nothing would match every request, and is refused when the extension is built rather than silently blocking all your traffic.

Replace the refusal with `on_blocked`, which takes the answer and returns a response:

```python
InternetData(
    app,
    api_key=os.environ.get("INTERNETDATA_API_KEY"),
    block_condition={"location": {"country": ["CU", "IR", "KP"]}},
    on_blocked=lambda found: (render_template("unavailable.html"), 451),
)
```

### Blocking one view

`block_condition` applies to every view. To refuse a visitor on some views only, decorate them below the route, sync or async:

```python
from internetdata_flask import block_if


@app.get("/checkout")
@block_if({"location": {"country": ["CU", "IR", "KP"]}})
def checkout(): ...
```

`block_if` takes the same condition, `on_blocked`, `fail_closed` and `on_missing_field`. It judges the answer the extension already attached, so a visitor is looked up once however many views check them, and it warns once for a member your plan doesn't include. A request `skip` claimed reaches the view. The extension still has to be registered: on an app without it, a decorated view raises `RuntimeError` instead of letting everyone through.

## Where the client address comes from

This is the setting that decides whether any of the above works, and it is the one thing only you can get right.

By default the extension uses `request.remote_addr`, which is the socket peer unless you have wrapped the app in werkzeug's `ProxyFix`. Behind a load balancer without it, every visitor looks like the load balancer, and that is the address that gets looked up: every visitor gets your proxy's country and network, and if it is a hosting address, a hosting rule blocks everyone. A load balancer in your own network usually has a private address, which the extension answers locally without a lookup, as an address with no country, and logs a warning. Adding `ProxyFix` is Flask's own answer and everything else here follows from it. It counts proxies from the right (`x_for=1` believes the last `X-Forwarded-For` entry), so it is right only when the app cannot be reached except through those proxies: anyone who connects to the app directly writes that entry themselves.

For an edge that writes the address into its own header, name the header:

```python
from internetdata_flask import header_ip_selector

InternetData(
    app,
    api_key=os.environ.get("INTERNETDATA_API_KEY"),
    ip_selector=header_ip_selector("CF-Connecting-IP"),  # or True-Client-IP, or your own
)
```

`xff_ip_selector()` reads `X-Forwarded-For` directly. Be aware that the left-most entry is whatever the caller sent, because proxies append to that header, so it's only trustworthy when an edge you control overwrites it. If you know how many proxies sit in front, count from the right instead: `xff_ip_selector(1)` is the address your nearest proxy saw.

Anything else, pass your own callable. It receives the request and returns an address.

If the address resolves to a private one, the extension says so once through the `internetdata` logger. That is expected on localhost and is the signal to fix your configuration anywhere else.

## When a lookup fails

The request is let through, and the reason is recorded on the answer's `error`. Our outage should not become yours, so a network failure, a rate limit or a rejected key all fail open. Pass `fail_closed=True` to block instead. Private addresses are answered locally and never fail, so this will not lock you out in development.

## Cost and latency

Answers are cached for an hour, so a returning visitor costs nothing, and private addresses never leave the process. A cache miss is one request to our API, bounded at 2.5 seconds by default and not retried: on a request path, failing open quickly beats holding a visitor while we try again. Both are adjustable with `timeout` and `retries`, and the cache through an `InternetData` client you build yourself and pass as `client`.

Skip what you do not care about:

```python
InternetData(app, skip=lambda request: request.path.startswith("/static"))
```

Beyond a few million distinct visitors a day, stop calling the API per request: look addresses up locally in [our databases](https://internetdata.io/databases) instead.

## Absent is not false

Unlimited, with a key or without one, leaves out `is_vpn`, `is_hosting`, `is_cdn` and the four proxy flags, the detail behind them and `bot`, and the paid members inside `location`, `asn`, `company` and `abuse`, such as `location.city`. A field your plan does not include is `None`, which means "not in your plan" rather than "checked, and no".

```python
lookup().result.flagged("is_vpn")  # False rather than None on a plan without it
```

A `block_condition` naming a member your plan does not serve, `location.city` on Unlimited included, can never match, so the extension warns once instead of failing silently. Pass `on_missing_field="raise"` to make it an error.

## Other Libraries

There are official InternetData client libraries available for many languages including PHP, Python, Go, Java, and Ruby. See our GitHub at https://github.com/internetdata for more.

## About InternetData

Geolocation, anonymity, ownership and network data for IP addresses, AS numbers and domains, as an API and as databases you download and query yourself.

[<img src="https://s3.internetdata.io/internetdata-public/brand/mark.svg" alt="InternetData" height="64"/>](https://internetdata.io/)

## License

This project is licensed under the [MIT License](LICENSE).
