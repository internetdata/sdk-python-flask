# Changelog

What each release changed for you, newest first. Each line is a commit's summary, linked to its full description and diff.

## 1.0.7 - 2026-11-23

### Fixes

- Require internetdata 2.18.1: whose operator an unverified bot names ([`e3eceb1`](https://github.com/internetdata/sdk-python-flask/commit/e3eceb16c7d0f571621ec1ac1e63ad6324d0f257))

## 1.0.6 - 2026-11-22

### Features

- Require internetdata 2.18.0: whether a bot uses an address, and whose ([`4d0324d`](https://github.com/internetdata/sdk-python-flask/commit/4d0324d1c682b2f903a865867d32bc344fc06bc8))

## 1.0.5 - 2026-11-20

### Features

- Require internetdata 2.17.0: a paid domain answer's hosting, co-hosted domains, home page, redirects and backlinks ([`aed52f5`](https://github.com/internetdata/sdk-python-flask/commit/aed52f5d22873f38429fb14ecc0b0fc12d0a2836))

## 1.0.4 - 2026-11-20

### Features

- Require internetdata 2.16.0: a tier, standing, license type, format or outcome the API adds reads as served ([`32dda09`](https://github.com/internetdata/sdk-python-flask/commit/32dda091ae1ab690b860ff93d06aeb2bc35d7f51))

## 1.0.3 - 2026-11-19

### Fixes

- Require internetdata 2.15.2: a reduced answer is cached a minute at most ([`f786263`](https://github.com/internetdata/sdk-python-flask/commit/f786263e3953a28c33419d962a3999a026ffa3a3))

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
