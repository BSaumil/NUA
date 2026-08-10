"""
Ash Personas — specialized agent identities.

Each persona is a focused "Chief of Staff" for a domain. They share
Ash's core cognition (multi-turn tool-calling loop) but differ in:
  • which tools they can call (module-scoped)
  • which system prompt frames the conversation
  • which grounding data is prioritized

Personas are just configuration — the underlying agent loop is unchanged.
This keeps the surface area small while letting the owner talk to a
specialist ("ask Ash Finance about Q4 margin") without leaking irrelevant
tools into the LLM's context window.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Persona:
    id: str
    label: str
    tagline: str
    modules: List[str]                     # tool modules this persona can invoke
    tone: str                              # short adjective for LLM
    focus: str                             # what this persona cares about most
    icon: str = "brain"                    # lucide-react name
    color: str = "#6366f1"                 # indigo default


# ── Registry ──────────────────────────────────────────────────────────────
PERSONAS: Dict[str, Persona] = {
    "executive": Persona(
        id="executive",
        label="Ask NUA",
        tagline="Your on-call NUA — ask anything, get grounded answers, execute across every module.",
        modules=["Ash", "Finance", "Inventory", "Customers", "Reservations", "Marketing", "Staff"],
        tone="warm, composed, terse",
        focus="Overall health, cross-module trade-offs, what needs the owner's attention TODAY.",
        icon="sparkles",
        color="#4f46e5",
    ),
    "finance": Persona(
        id="finance",
        label="NUA Finance",
        tagline="CFO — margins, cash flow, approvals over $500, tax posture.",
        modules=["Finance", "Ash"],
        tone="precise, numeric, sceptical",
        focus="Revenue vs. cost, gross margin, working capital, unapproved journal entries, tax exposure.",
        icon="calculator",
        color="#059669",
    ),
    "ops": Persona(
        id="ops",
        label="NUA Ops",
        tagline="Head of Operations — inventory, kitchen, purchasing, waste.",
        modules=["Inventory", "Ash"],
        tone="hands-on, direct, safety-first",
        focus="Stock levels vs. par, waste %, 86'd dishes, PO cadence, supplier reliability.",
        icon="package",
        color="#d97706",
    ),
    "hr": Persona(
        id="hr",
        label="NUA HR",
        tagline="Head of People — rosters, burnout, tasks, training gaps.",
        modules=["Staff", "Ash"],
        tone="empathetic, coaching",
        focus="Overtime, burnout signals, unfilled shifts, task assignment, morale.",
        icon="users",
        color="#7c3aed",
    ),
    "marketing": Persona(
        id="marketing",
        label="NUA Marketing",
        tagline="CMO — promotions, campaigns, churn recovery, birthday cadence.",
        modules=["Marketing", "Customers", "Ash"],
        tone="creative, growth-minded",
        focus="Slow inventory to promote, at-risk customers to re-engage, campaign performance, voucher ROI.",
        icon="megaphone",
        color="#db2777",
    ),
    "guest": Persona(
        id="guest",
        label="NUA Guest",
        tagline="Head of Guest Experience — reservations, VIPs, loyalty tier moves.",
        modules=["Customers", "Reservations", "Ash"],
        tone="warm, hospitality-first",
        focus="Guest satisfaction, VIP recognition, no-show recovery, tier upgrades that build lifetime value.",
        icon="heart",
        color="#dc2626",
    ),
}

DEFAULT_PERSONA = "executive"


def get_persona(persona_id: Optional[str]) -> Persona:
    if not persona_id:
        return PERSONAS[DEFAULT_PERSONA]
    return PERSONAS.get(persona_id.lower(), PERSONAS[DEFAULT_PERSONA])


def catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": p.id,
            "label": p.label,
            "tagline": p.tagline,
            "modules": p.modules,
            "tone": p.tone,
            "focus": p.focus,
            "icon": p.icon,
            "color": p.color,
        }
        for p in PERSONAS.values()
    ]


def filter_tools(all_tools: List[Dict[str, Any]], persona_id: Optional[str]) -> List[Dict[str, Any]]:
    """Return only tools whose module belongs to the persona."""
    persona = get_persona(persona_id)
    allowed = set(persona.modules)
    return [t for t in all_tools if t.get("module") in allowed]


def system_prompt(persona_id: Optional[str], base_prompt: str) -> str:
    """Wrap the shared Ash system prompt with the persona's voice + focus."""
    p = get_persona(persona_id)
    header = f"""You are **{p.label}** — a specialised NUA persona.

  Tone: {p.tone}
  Domain focus: {p.focus}
  You have tools only for modules: {', '.join(p.modules)}.

  If the owner asks something outside your remit, say so briefly and suggest
  which persona to switch to (Ask NUA / NUA Finance / NUA Ops / NUA HR / NUA Marketing / NUA Guest).
"""
    return header + "\n\n" + base_prompt
