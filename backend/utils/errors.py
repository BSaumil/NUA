"""log_and_continue() — for the "this is best-effort, never block the main
flow" pattern used all over this codebase (audit-log writes after the real
mutation already succeeded, notification sends, rules-engine emits). The
established idiom was `except Exception: pass`, which is fine for genuinely
inconsequential fallbacks (a date failed to parse, use a placeholder) but
silent for things worth knowing about if they start failing — an audit
trail that stops recording with zero signal is a real gap, just not one
that should ever turn into a 500 for the caller.

Not a blanket replacement for every bare except in the codebase — most of
the ~100 existing ones are deliberate, low-stakes fallbacks that don't
need a log line. Use this where the thing inside the try is itself worth
knowing if it silently stops happening.
"""
import logging


def log_and_continue(logger: logging.Logger, context: str, exc: Exception) -> None:
    logger.warning(f"{context}: {exc}")
