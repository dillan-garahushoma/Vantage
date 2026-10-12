"""The optional estate health brief (BATCH AI-4).

A brief *explains* the latest stored Living Score snapshot in plain English. It
never calculates a score, never recommends from its own knowledge, and is never
shown anything except the numbers in :mod:`app.analytics.ai.brief_facts`.

The layer is optional by construction:

* the facts are a pure projection of a stored snapshot - no aggregate query is
  re-run and no number is recomputed, so a brief cannot disagree with the score;
* the provider sees numbers, enums and dates only, never resident text, a name, a
  unit number or an estate name;
* every failure - AI off, provider down, budget spent, malformed or ungrounded
  output - falls back to the deterministic template built from the same stored
  snapshot, so the product is complete with AI off.

This package imports the engine's *vocabulary* (component keys and weights) and
never its calculation.
"""
