"""Outbound voice calls via Twilio — lets NUA actually pick up the phone
to confirm a booking or follow up with a guest, instead of only
texting/emailing. Same env-gated honesty as utils/notifications.py's SMS:
real when TWILIO_* is configured, a clear error (never a silent fake "call
placed") when it isn't.

ENV (optional, shared with the existing Twilio SMS integration):
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_PHONE
"""
from __future__ import annotations
import os
from typing import Dict, Optional


class VoiceCallError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN")
                and os.environ.get("TWILIO_FROM_PHONE"))


def place_call(*, to: str, twiml_url: str, status_callback_url: str) -> str:
    """Places the real outbound call via the Twilio REST API and returns
    the Twilio Call SID. Twilio drives the rest of the conversation itself
    by POSTing back to twiml_url (for what to say) and status_callback_url
    (when the call ends) — this only starts the phone ringing."""
    if not is_configured():
        raise VoiceCallError("Voice calling isn't set up yet — ask the owner to add Twilio credentials.")
    from twilio.rest import Client
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    call = client.calls.create(
        to=to, from_=os.environ["TWILIO_FROM_PHONE"], url=twiml_url,
        status_callback=status_callback_url, status_callback_event=["completed"],
    )
    return call.sid


def validate_signature(url: str, params: Dict[str, str], signature: Optional[str]) -> bool:
    """Confirms a webhook POST actually came from Twilio. These endpoints
    have to sit in PUBLIC_API_PREFIXES since Twilio can't carry our JWT, so
    this is the only thing standing between a spoofed SpeechResult and the
    AI acting on it as if a real guest said it."""
    if not signature or not os.environ.get("TWILIO_AUTH_TOKEN"):
        return False
    from twilio.request_validator import RequestValidator
    return RequestValidator(os.environ["TWILIO_AUTH_TOKEN"]).validate(url, params, signature)


def say_and_gather_twiml(*, say: str, gather_action_url: str, end_call: bool = False) -> str:
    """TwiML NUA speaks back at Twilio. `say` is read aloud with Twilio's
    TTS; unless `end_call`, a speech <Gather> opens so the guest's spoken
    reply comes back to `gather_action_url` as SpeechResult."""
    from twilio.twiml.voice_response import VoiceResponse, Gather
    vr = VoiceResponse()
    if end_call:
        vr.say(say)
        vr.hangup()
        return str(vr)
    gather = Gather(input="speech", action=gather_action_url, method="POST",
                     speech_timeout="auto", language="en-AU")
    gather.say(say)
    vr.append(gather)
    # Guest said nothing inside the gather window — don't leave the line
    # hanging silently.
    vr.say("Sorry, I didn't catch that. We'll follow up by text instead. Goodbye.")
    vr.hangup()
    return str(vr)
