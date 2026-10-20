# Spike: TypeSafe Jev key and Python SDK contract

Date: 2026-10-19. Throwaway probe (not kept in the application).

## Result

- `TYPESAFE_API_KEY` is present and authenticates.
- `models.list()` succeeded in about 0.21s and returned `jev-latest` and `jev-preview`.
- One real inference call returned `model='jev-1.13.0'`, usage 316 input / 24 output
  tokens, `noul=0.8`, in about 0.30s.

## Contract correction (matters for Slice 2)

The installed `typesafe-sdk` 0.7.5 Python surface is not an ergonomic
`Jev.ask(...)` wrapper. Verified working shape:

- Import `TypeSafeClient` and question types from `typesafe_sdk`.
- Call `client.system_one(state, {"question_name": Noul(...)})`.
- `Noul` takes `instructions` plus `criteria={"true": ..., "false": ...}`.
- The response carries the concrete model (`jev-1.13.0`) and total usage even
  though the model list exposes channel names.

Slice 2 must code against the installed schemas (inspected via the models'
JSON schemas), pin the SDK version, and record `response.model` and usage on
every proposal. Provider training/retention settings still require the design
ADR before real issue text is sent at scale; this spike sent only a two-sentence
synthetic summary.
