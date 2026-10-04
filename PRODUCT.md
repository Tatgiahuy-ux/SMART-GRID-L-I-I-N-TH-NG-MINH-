# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python + Streamlit, developed and run from Visual Studio Code.
Machine learning: scikit-learn (RandomForestRegressor) with joblib for model persistence.
Blockchain demo: hashlib/SHA-256 hash chain plus a local Proof-of-Work chain with a
heaviest-chain consensus rule (no external node or network dependency).

## Users

Primary users are the five-person student project team, who need to integrate, test, and demonstrate the Smart Grid model. The lecturer is the evaluator and demo audience.

## Product Purpose

Provide an educational Smart Grid demonstration that predicts electricity consumption with machine learning and verifies the integrity of electricity data using blockchain-style hashing. Success means the team can run one reliable Streamlit demo showing the data, prediction, hash, mining, and verification result clearly.

## Positioning

The project combines electricity-consumption forecasting and tamper-evident data verification in one small, explainable classroom demo rather than presenting either technique in isolation. Each mined block stores the actual consumption next to the model prediction, so the ML and Blockchain parts are wired together instead of being shown side by side.

## Operating Context

- The application is assembled and operated locally from Visual Studio Code during a classroom presentation.
- The integration owner connects the ML and Blockchain modules, prepares the demo flow, and handles runtime issues during presentation.
- Contributors must document each module's purpose, inputs, outputs, run instructions, and known limitations for the presentation and report.

## Capabilities and Constraints

- The ML module loads `data/power_consumption.csv` (720 hourly rows), trains and serves a RandomForest model from `ml/model.pkl`, and produces an hourly forecast in Python. Test metrics live in `ml/metrics.json`.
- If scikit-learn or `ml/model.pkl` is unavailable, the ML module falls back to an explainable linear-trend baseline and reports the reason, so the demo always runs.
- The Blockchain module creates a SHA-256 hash chain, mines Proof-of-Work blocks with a configurable difficulty, verifies nonce/difficulty/linkage, and resolves conflicts with the heaviest-chain rule.
- The Streamlit interface exposes five tabs: overview and ML metrics, hash integrity, Proof-of-Work consensus, data, and the presentation script.
- `tools/smoke_test.py` and `tools/ui_test.py` verify the integrated flow headlessly (8 + 8 checks).
- The dataset is simulated by script, not measured from a real grid, and Smart Mobility data is not covered yet.
- The PoW/consensus demo runs inside a single process with two simulated branches; it is not a peer-to-peer network and has no digital signatures or smart contracts.
- This is an educational demonstration. Hash verification and PoW must not be presented as absolute protection against all forms of data tampering; a majority-hash-power attacker is demonstrated explicitly.

## Evidence on Hand

- The project brief identifies Smart Grid as the topic and electricity-consumption data as the primary data source.
- The ML teammate delivered `ml_model.py`, `generate_data.py`, `model.pkl`, and `data/power_consumption.csv`; originals are kept in `team-deliverables/`.
- The Blockchain teammate delivered `blockchain_module.py` (kept in `team-deliverables/`); its `calculate_hash` was missing a `return`, which is fixed in `blockchain/consensus.py`.
- Everything still unproven: real grid or mobility data, P2P consensus, smart contracts, and any claim of production security.
