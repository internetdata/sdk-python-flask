# Changelog

What each release changed for you, newest first. Each line is a commit's summary, linked to its full description and diff.

## 1.0.2 - 2026-11-19

### Fixes

- Require internetdata 2.15.1: cap_reached on a paid answer past its overage cap ([`714a9eb`](https://github.com/internetdata/sdk-python-flask/commit/714a9ebe0b038d7ad7eb9cb09560ae901bd7c174))

## 1.0.1 - 2026-11-14

### Fixes

- Require internetdata 2.12.1: a 403 can mean the key lacks the ip.lookup scope ([`e084a6e`](https://github.com/internetdata/sdk-python-flask/commit/e084a6ef78e157babf8ec301f184bbfb4d297864))

## 1.0.0 - 2026-11-14

### Features

- Attach the visitor's InternetData record to every request, read with `lookup()`: the location, the network and the company behind the address, and the anonymity and hosting flags your plan serves ([`c4884fd`](https://github.com/internetdata/sdk-python-flask/commit/c4884fd4f098a724145f92abed8b722df2cb95a6))
- Refuse a request with a `block_condition` written in the shape of a result, by country, network type, anonymity or any other member, with 403 or an `on_blocked` of your own ([`c4884fd`](https://github.com/internetdata/sdk-python-flask/commit/c4884fd4f098a724145f92abed8b722df2cb95a6))
- Refuse one view with the `block_if` decorator, sync or async, judging the answer the extension already attached ([`c4884fd`](https://github.com/internetdata/sdk-python-flask/commit/c4884fd4f098a724145f92abed8b722df2cb95a6))
- Choose where the client address comes from: `request.remote_addr` by default, `xff_ip_selector`, `header_ip_selector` for a header your edge writes, or a callable of your own ([`c4884fd`](https://github.com/internetdata/sdk-python-flask/commit/c4884fd4f098a724145f92abed8b722df2cb95a6))
- Fail open on any lookup failure unless `fail_closed` is set, with a 2.5 s bound, no retry and a cache by default ([`c4884fd`](https://github.com/internetdata/sdk-python-flask/commit/c4884fd4f098a724145f92abed8b722df2cb95a6))
