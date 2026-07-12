"""Offline evaluators for AI flow outputs.

Currently houses ``itinerary_evaluators`` — pure-function evaluators for
``generate_itinerary`` output (#1053 P0.3). These mirror the LangSmith
evaluator concept (input/output → score + reasoning) but as plain Python
functions so they can:

- Run inside the existing pytest suite
- Run inside the chat-scenarios CI step
- Be ported to LangSmith ``RunEvaluator`` instances later without changing
  the underlying logic.
"""
