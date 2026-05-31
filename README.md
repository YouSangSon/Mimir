# Mimir

Free, legal investment-insight pipeline. Mimir collects public Korean and US
market data, stores it as version-controlled JSONL in this repo (git-as-DB),
and runs for free on GitHub Actions. It is the foundation for later layers:
scored insights (⭐), scheduled Telegram digests, daily HTML reports, historical
"what happened last time" analysis, and — eventually — automated trading.

> **Not financial advice.** Everything Mimir produces is for information only.

Named after Mímir, the keeper of the well of wisdom in Norse myth.

---

## Status

| Layer | Spec | State |
|---|---|---|
| **S1 Collector** — data collection & storage | [spec](docs/superpowers/specs/2026-05-31-collector-design.md) · [plan](docs/superpowers/plans/2026-05-31-s1-collector.md) | **Increment 1 implemented** |
| S2 Analysis & Scoring (⭐) | — | planned |
| S3 Delivery & Reporting (Telegram + HTML) | — | planned |
| S4 Historical / Event-Analog | — | planned |
| S5 Automated Trading | — | future |

See the full [program roadmap](docs/architecture/roadmap.md).

### What Increment 1 collects

| Source | Market | Data | Auth | Legal |
|---|---|---|---|---|
| **SEC EDGAR** | 🇺🇸 US | filings (10-K/Q, 8-K) | User-Agent only (no signup) | ✅ official |
| **Stooq** | 🇺🇸 US | EOD prices (OHLCV) | free `apikey` (captcha-issued) | ✅ free |
| **DART** | 🇰🇷 KR | disclosures | free API key | ✅ official |

Out of the box (no keys) only **SEC EDGAR** runs. Add the free keys to enable
Stooq and DART. KR prices (pykrx), macro (FRED/ECOS), and news arrive in
Increment 2.

---

## Setup

Requires Python **3.14** (pinned via `.tool-versions` for asdf).

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env   # then fill in any free keys you want
```

Configure what to track in `config/watchlist.yaml`, and source toggles /
gray-source policy in `config/sources.yaml`.

## Run

```bash
# Collect for a cadence (writes data/ + reports/status.html)
.venv/bin/python -m mimir.collect --cadence daily

# Backfill history for a source (e.g. years of prices for the event-analog layer)
.venv/bin/python -m mimir.backfill --source stooq --since 2018-01-01
```

Secrets come from the environment (`.env` locally, GitHub Actions Secrets in CI).
Open `reports/status.html` to see the last run's per-source result.

## How data is stored (git-as-DB)

```
data/<dataset>/YYYY/MM/DD.jsonl     # append-only, line-diffable, idempotent
data/_manifest/YYYY/MM/DD.jsonl     # one line per run: what/when/how many/ok?
```

Datasets: `prices`, `filings`, `macro`, `news`. Each line is a normalized
envelope validated by pydantic at the boundary. Date partitioning keeps git
diffs tiny and avoids repo bloat.

## Scheduling (free)

`.github/workflows/collect-daily.yml` runs on a cron (off-peak minute, since
GitHub cron is best-effort), then commits new data back to the repo. Use a
**public** repo for unlimited free Actions minutes. CI (`ci.yml`) runs ruff,
mypy `--strict`, and pytest with an 80% coverage gate.

## Development

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
.venv/bin/coverage run -m pytest && .venv/bin/coverage report
```

TDD throughout; adapters are unit-tested against recorded fixtures (no live
network). Architecture and contracts live in the
[S1 spec](docs/superpowers/specs/2026-05-31-collector-design.md).

## Legal & ethics

- Prefer official APIs; collect only public data.
- Each source carries a `legal_status` and `rate_limit` enforced in code.
- `pykrx` (KR prices, Increment 2) is a scraping gray area: throttled,
  internal-analysis only, and switchable off via `gray_enabled: false`.
- API keys and tokens are never committed.
