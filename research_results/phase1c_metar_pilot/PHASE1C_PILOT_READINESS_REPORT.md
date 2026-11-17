# Phase 1C Pilot Readiness Report

**Prepared:** 2026-11-17  
**Status:** `PILOT_WORKFLOW_BLOCKED_PROVIDER_INTERFACE_UNVERIFIED`  
**Branch:** `codex/phase1c-controlled-metar-pilot`  
**Base:** Phase 1B `49c3edfe031ff5d670d424ff50f9d087354add32`

## 1. Executive summary

The approval-gated workflow and offline quality checks are prepared for VILD0 and conditional neighbour candidate 42105. The exact proposed dates are not supported by the inspected Meteostat 2.2.3 METAR adapter: its runtime registry starts on 2026-11-16 and its Aviation Weather Center adapter queries only the latest 24 hours. The local provider filter excludes September 2025 before the request function is called. No observation rows were requested or retrieved. The workflow is therefore blocked for this requested historical interval, and this is not a completed data pilot.

## 2. Starting Phase 1B status

Phase 1B is `PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED`. It inventoried provider/parameter metadata but did not fetch observation rows. VILD0/42099 identity remains unresolved; 42105 is a conditional neighbour. Inventory periods do not prove actual observations, timestamp overlap, source flags, or representativeness. Phase 0 is complete locally; Phase 1A and 1B remain partial.

## 3. Provider-interface verification

The isolated Meteostat 2.2.3 package exposes `meteostat.hourly(station, start, end, timezone=None, parameters=None, providers=None)`, returning a TimeSeries. The implementation selects `Provider.METAR` and the five `Parameter` enums explicitly. `TimeSeries.fetch(fill=False, sources=True, clean=False)` supports no-fill output and per-parameter source columns; `config.include_model_data=False` is additionally set as a guard. Provider selection is constrained to METAR, and the workflow rejects non-METAR source values when source columns are present.

The runtime provider registry reports METAR start `2026-11-16`; installed adapter source targets Aviation Weather Center with `hours=24`. The requested dates fail both checks. This workflow does not call `meteostat.hourly()` unless the local runtime preflight passes. The adapter parses METAR text and does not preserve original HTTP response bytes. A future saved export is labeled as a Meteostat DataFrame export, not the original response.

Meteostat 2.2.3 computes RHUM from temperature and dew point. It is not an independent encoded METAR observation. Source labels cannot establish instrument-level provenance or station independence. The optional `metar` parser was absent from the isolated package environment.

## 4. Retrieval configuration

- Stations: `VILD0` (primary candidate) and `42105` (conditional neighbour candidate).
- Provider: Meteostat `METAR` only.
- Parameters: `temp`, `rhum`, `wspd`, `wdir`, `pres`.
- Period: 2025-09-01 inclusive through 2025-09-30 inclusive; internal end boundary 2025-10-01 exclusive.
- Frequency: hourly; source index preserved and a separate UTC-aware index used for comparisons.
- Model fill: disabled; no interpolation or imputation.
- Future output: unique `research_results/phase1c_metar_pilot/runs/<unique_run_id>/` directory with immutable CSV exports and hashes.

## 5. Authentication requirements

The inspected Meteostat Python dataset interface is distinct from its authenticated JSON API; the latter requires a RapidAPI key/subscription. The installed METAR adapter requires `MS_AVIATIONWEATHER_USER_AGENT` and the optional `metar` parser. No secret was read, printed, or stored. No RapidAPI key is required by the inspected Python route.

## 6. Dry-run result and approval

The CLI default printed the exact configuration and provider blocker with `network_request_performed: false` and `observation_rows_downloaded: false`. It did not invoke a provider call. Execution requires both `--execute` and `--confirm-pilot-retrieval`; the current period is still refused by provider preflight. No actual retrieval was executed. Approval remains `PENDING_USER_APPROVAL`.

## 7. Expected future data outputs

If a provider/date window is later explicitly approved and supported, each station would have a unique run directory with a Meteostat-returned DataFrame CSV, UTC retrieval metadata, quality summaries, common-timestamp outputs, and a SHA-256 manifest. The DataFrame is not represented as raw HTTP bytes. No successful run manifest or fabricated observation data exists in this preparation.

## 8. Source attribution limitations

Per-variable source columns can identify the package's source attribution when returned, while absent values are marked `UNKNOWN`. A METAR label is not proof of independent sensor provenance. RHUM is derived within Meteostat. Physical identity and independence of VILD0/42105, actual overlap, and spatial suitability remain unverified. This pilot cannot establish E3 effectiveness.

## 9. Outstanding risks

- The requested September 2025 period is outside the inspected 24-hour adapter window and predates the package's current METAR provider start.
- Availability through another historical METAR source has not been established.
- The optional METAR parser was not installed.
- Candidate station identity, source provenance, and actual common observations are unknown.
- Phase 2 independently adjudicated event/fault/normal references remain outstanding.

## 10. Exact next user decision

Choose whether to identify and verify a different traceable historical METAR provider or change the pilot dates to a window that the current adapter can serve. Any changed specification must be reviewed before execution. Explicit authorization will still be required for any actual bounded request. No observations should be assumed available from the current workflow for September 2025.

## Verification references

See [PILOT_DRY_RUN_REPORT.md](PILOT_DRY_RUN_REPORT.md) for detailed package and official documentation links. Phase 1A and Phase 1B manifests and their historical artifacts are verified separately during final validation.
