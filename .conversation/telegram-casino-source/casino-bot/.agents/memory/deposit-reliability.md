---
name: Deposit reliability
description: Durable rules for confirmed NOWPayments credits and notification retries.
---

Once a confirmed deposit balance write begins, its provider payment ID must remain in durable deduplication state even if saving or Telegram notification delivery fails.

**Why:** Clearing the ID after a post-credit failure lets the next webhook or poll replay the same on-chain payment and double-credit the player.

**How to apply:** Keep balance credit, payment-ID persistence, and notification retry state separate; retries may resend messages, but must never repeat the balance mutation.