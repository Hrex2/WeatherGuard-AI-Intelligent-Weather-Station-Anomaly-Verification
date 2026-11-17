# Phase 1C METAR pilot dry-run report

**Prepared:** 2026-11-17  
**Approval:** `PENDING_USER_APPROVAL`  
**Dry-run retrieval executed:** No network request; no observation rows retrieved.

## Exact proposed request

| Setting | Value |
|---|---|
| Stations | VILD0 (primary candidate), 42105 (conditional neighbour candidate) |
| Provider | Meteostat `METAR` (`Provider.METAR`) |
| Parameters | `temp`, `rhum`, `wspd`, `wdir`, `pres` |
| Start | 2025-09-01 inclusive |
| End | 2025-09-30 inclusive; internal exclusive boundary 2025-10-01 |
| Frequency | Hourly |
| Source timestamps | UTC, timezone-naive in Meteostat when `timezone=None`; normalize a separate comparison index to UTC-aware |
| Model fill | Disabled (`providers=[Provider.METAR]`, `config.include_model_data=False`, `fetch(fill=False)`) |
| Output | `research_results/phase1c_metar_pilot/runs/<unique_run_id>/` |

No other stations, providers, variables or dates are permitted by the fixed specification. 42099 remains identity-unresolved and is not treated as an independent neighbor.

## Interface verification

The Phase 1B isolated environment contains Meteostat Python 2.2.3. Inspection of that installed version found:

- The current call is `meteostat.hourly(station, start, end, timezone=None, parameters=None, providers=None)`. This is a function returning a `TimeSeries`; the older `Hourly` class is not exposed.
- Provider selection is an explicit list of `Provider` enums; `Provider.METAR` has value `metar`. Parameter selection is a list of `Parameter` enums. The provider registry lists METAR support for `temp`, `rhum`, `wdir`, `wspd`, and `pres`.
- The returned series is retrieved inside `ms.hourly(...)`; `.fetch()` formats its in-memory DataFrame. Use `fetch(squash=True, sources=True, fill=False, clean=False, humanize=False, units=UnitSystem.METRIC)` for per-variable source columns, with no missing-row fill. Only the METAR provider is requested; combined `Provider.HOURLY` is not used. The additional `include_model_data=False` setting is a fail-safe against Meteostat's own model provider.
- Passing an end `date` makes version 2.2.3 parse it to 23:59:59.999999. Therefore the API call must pass `date(2025, 9, 30)`, not `date(2025, 10, 1)`, to honor the inclusive final day. The next-day date is retained as the internal exclusive comparison boundary.
- With `timezone=None`, the package documents UTC as the default and returns UTC-naive time indexes. The workflow retains those original index values and creates a separate UTC-aware comparison index.
- `TimeSeries.fetch(sources=True)` provides per-variable source columns. The selected provider/source identifier is retained, but it cannot prove the actual instrument or station-site independence. The METAR adapter parses text and discards the original HTTP response body; a saved DataFrame export must be labeled as a Meteostat-returned DataFrame, not as original response bytes.

## Provider-period blocker

The pinned package's runtime provider registry reports METAR start date `2026-11-16`. For the exact 2025 request, the installed provider filter returned an empty provider list before any data request. Package source also sets the METAR endpoint to Aviation Weather Center with `hours=24`. The requested September 2025 dates are outside that adapter's time window. The official Aviation Weather Center states its database offers up to the previous 30 days, still far short of this 2025 request. The workflow therefore refuses before calling `ms.hourly()`; it does not use another provider or modify dates.

There is a second scope limitation: the package's METAR provider builds `rhum` from parsed temperature and dew point using an internal calculation. RHUM is supported by the interface, but it is derived within Meteostat rather than an independent encoded METAR field. Source-column values are not retrieved or interpreted in this dry run.

The package module imports an optional `metar` parser that is not among the installed distribution's declared runtime requirements and was absent in the isolated environment. The adapter also requires a configured user-agent string (`MS_AVIATIONWEATHER_USER_AGENT`) or it skips the provider. Neither condition changes the date-window blocker.

## Authentication and access

The Meteostat Python dataset route is separate from the RapidAPI JSON API. The Python documentation describes open Meteostat datasets without a RapidAPI key; the authenticated JSON API does require a RapidAPI key/subscription. The inspected Aviation Weather Center adapter requires a user-agent, not a RapidAPI key. The user-agent value must be provided through `MS_AVIATIONWEATHER_USER_AGENT`; the workflow does not print or persist it. No environment credential was read or displayed during this preparation.

## Dry-run result

The CLI's default invocation prints the specification, dependency and authentication notes, output directory, provider-window blocker, and `network_request_performed: false`. It does not import or call the observation retrieval function. The execution command is gated by both `--execute` and `--confirm-pilot-retrieval`, then runs provider-window checks before it can call the data interface. For the current fixed 2025 period, that check refuses execution even when the flags are supplied.

No `raw/`, `processed/`, `quality/`, `metadata/`, or `reports/` run subdirectory and no successful run manifest were created during preparation. Those directories are created only under a unique future run ID after both approval flags and provider checks pass.

## Sources inspected

- [Meteostat Python hourly interface](https://dev.meteostat.net/python/api/meteostat.hourly)
- [Meteostat TimeSeries and fetch options](https://dev.meteostat.net/python/api/meteostat.TimeSeries.fetch)
- [Meteostat Provider and Parameter enums](https://dev.meteostat.net/python/api/meteostat.Provider), [parameter enum](https://dev.meteostat.net/python/api/meteostat.Parameter)
- [Meteostat data providers](https://dev.meteostat.net/providers)
- [Meteostat time format and units](https://dev.meteostat.net/formats.html)
- [Meteostat Python library](https://dev.meteostat.net/python) and [JSON API authentication](https://dev.meteostat.net/api.html)
- [Aviation Weather Center Data API](https://www.connect.aviationweather.gov/data/api/) (documented database horizon: up to previous 30 days)
- Installed Meteostat 2.2.3 source inspected locally: `meteostat/api/hourly.py`, `meteostat/api/timeseries.py`, `meteostat/core/data.py`, `meteostat/providers/noaa/metar.py`. No request was sent to the configured endpoint.
