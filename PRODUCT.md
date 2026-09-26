# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python + Streamlit, developed and run from Visual Studio Code.

## Users

Primary users are the five-person student project team, who need to integrate, test, and demonstrate the Smart Grid model. The lecturer is the evaluator and demo audience.

## Product Purpose

Provide an educational Smart Grid demonstration that predicts electricity consumption with machine learning and verifies the integrity of electricity data using blockchain-style hashing. Success means the team can run one reliable Streamlit demo showing the data, prediction, hash, and verification result clearly.

## Positioning

The project combines electricity-consumption forecasting and tamper-evident data verification in one small, explainable classroom demo rather than presenting either technique in isolation.

## Operating Context

- The application is assembled and operated locally from Visual Studio Code during a classroom presentation.
- The integration owner connects the ML and Blockchain modules, prepares the demo flow, and handles runtime issues during presentation.
- Contributors must document each module's purpose, inputs, outputs, run instructions, and known limitations for the presentation and report.

## Capabilities and Constraints

- The ML module will locate electricity-consumption data and produce a consumption prediction in Python.
- The Blockchain module will create a chain/hash record and verify whether stored data was changed.
- The Streamlit interface must expose the integrated workflow and be easy to demonstrate live.
- The project currently has no product implementation or application scaffold; integration contracts must be agreed before wiring the real modules together.
- This is an educational demonstration. Hash verification must not be presented as absolute protection against all forms of data tampering.

## Evidence on Hand

- The project brief identifies Smart Grid as the topic and electricity-consumption data as the primary data source.
- The specific dataset, trained model, hash schema, and final demo claims have not yet been selected.
