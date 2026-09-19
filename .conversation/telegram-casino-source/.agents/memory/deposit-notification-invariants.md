---
name: Deposit notification invariants
description: Rules for keeping crypto deposit settlement, fees, notifications, and explorer links consistent.
---

The settlement layer must pass the gross provider USD value to the confirmation renderer; the renderer derives the fee-adjusted credited value from the separate fee field.

**Why:** Passing the net amount as gross causes the fee to be subtracted twice in the user-facing confirmation while accounting totals remain correct.

**How to apply:** Keep gross USD, credited USD, fee USD, coin amount, network, and txid as separate values across provider verification, balance crediting, and notification retry payloads.

The Telegram deposit UX has two distinct user-facing stages: a short button-free processing message when the address first detects a transaction, followed by a separate button-free confirmation after crediting succeeds. Processing must not include balance, Txid, or diagnostic details.

**Why:** Combining detection and settlement makes users think funds are confirmed before the blockchain/provider confirmation is complete, while verbose diagnostics obscure the status.

**How to apply:** Keep the processing and confirmation notification claims separate and preserve premium custom-emoji formatting without falling back to inline keyboards or diagnostic blocks.