"""NUA Connect — the framework that lets NUA absorb data from any POS,
payment, accounting, rostering, delivery, or banking provider a venue
already uses.

Strategically (per the NUA Capability Dependency Graph), Connect is what
turns a competitor's POS into a data source feeding NUA's intelligence
layer instead of a wall NUA stops at. This package is the real
implementation of that idea: a provider registry with honest status,
encrypted per-venue credential storage, a sync-run ledger with raw payload
samples for audit/debugging, and a connector interface every provider
implements against.
"""
