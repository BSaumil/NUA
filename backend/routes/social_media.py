"""
Social Media Marketing — connect accounts, AI-generate post content from
products/promos/specials, and schedule/publish.

Real cross-posting to Meta/TikTok/X requires per-platform OAuth flows and
business verification. The connect flow here is intentionally MOCKED at
the OAuth boundary so the rest of the product (AI generation, scheduling,
preview, image-library binding) can ship today. Marking a post "published"
flags it locally — the platform call is logged but stubbed.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import os
import logging

from database import db
from deps import get_user, require_owner_or_manager

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ("instagram", "facebook", "tiktok", "x", "google_business")
PLATFORM_LABELS = {
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "x": "X (Twitter)",
    "google_business": "Google Business",
}


# ============ MODELS ============
class AccountConnectIn(BaseModel):
    platform: str
    handle: str        # @restaurant_handle
    displayName: Optional[str] = None


class SocialPostIn(BaseModel):
    platform: str                       # which connected account
    postType: str                       # post | story | reel
    caption: str
    hashtags: List[str] = []
    imageUrl: Optional[str] = None      # data: URL from ImageLibrary or http
    sourceType: Optional[str] = None    # product | promotion | special | manual
    sourceId: Optional[str] = None
    scheduledFor: Optional[str] = None  # ISO date string; null = publish-now
    status: Optional[str] = "draft"     # draft | scheduled | published | failed


class AIGenerateIn(BaseModel):
    sourceType: str                    # product | promotion | special
    sourceId: Optional[str] = None     # required for product/promotion
    tone: Optional[str] = "warm"       # warm | bold | playful | luxe | concise
    platforms: List[str] = ["instagram"]
    postType: Optional[str] = "post"   # post | story | reel
    customPrompt: Optional[str] = None
    locale: Optional[str] = "en-AU"


# ============ ACCOUNT CRUD ============
@router.get("/social/accounts")
async def list_accounts(_: dict = Depends(get_user)):
    accounts = await db.social_accounts.find({}, {"_id": 0}).to_list(50)
    return accounts


@router.post("/social/accounts")
async def connect_account(body: AccountConnectIn, user: dict = Depends(require_owner_or_manager)):
    if body.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Platform must be one of {SUPPORTED_PLATFORMS}")
    handle = body.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(400, "Handle is required")
    existing = await db.social_accounts.find_one({"platform": body.platform, "handle": handle})
    if existing:
        raise HTTPException(409, "This handle is already connected on that platform")
    doc = {
        "id": str(uuid.uuid4()),
        "platform": body.platform,
        "platformLabel": PLATFORM_LABELS[body.platform],
        "handle": handle,
        "displayName": body.displayName or handle,
        # MOCKED — real OAuth tokens go here once the integration ships.
        "tokenStatus": "mock_active",
        "connectedAt": datetime.now(timezone.utc).isoformat(),
        "connectedBy": user.get("email"),
    }
    await db.social_accounts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/social/accounts/{account_id}")
async def disconnect_account(account_id: str, _: dict = Depends(require_owner_or_manager)):
    res = await db.social_accounts.delete_one({"id": account_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Account not found")
    return {"deleted": True}


# ============ POSTS ============
@router.get("/social/posts")
async def list_posts(status: Optional[str] = None, platform: Optional[str] = None, _: dict = Depends(get_user)):
    q: dict = {}
    if status:
        q["status"] = status
    if platform:
        q["platform"] = platform
    posts = await db.social_posts.find(q, {"_id": 0}).sort("createdAt", -1).to_list(200)
    return posts


@router.post("/social/posts")
async def create_post(body: SocialPostIn, user: dict = Depends(require_owner_or_manager)):
    if body.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Platform must be one of {SUPPORTED_PLATFORMS}")
    if body.postType not in ("post", "story", "reel"):
        raise HTTPException(400, "postType must be post | story | reel")
    # Must have a connected account for that platform
    if not await db.social_accounts.find_one({"platform": body.platform}):
        raise HTTPException(400, f"No connected {body.platform} account — connect one first")
    doc = {
        "id": str(uuid.uuid4()),
        **body.dict(),
        "status": body.status or "draft",
        "createdBy": user.get("email"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.social_posts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/social/posts/{post_id}")
async def delete_post(post_id: str, _: dict = Depends(require_owner_or_manager)):
    res = await db.social_posts.delete_one({"id": post_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Post not found")
    return {"deleted": True}


@router.post("/social/posts/{post_id}/publish")
async def publish_post(post_id: str, _: dict = Depends(require_owner_or_manager)):
    """Marks a post as published. Real cross-posting to Meta/TikTok/X is
    deferred until per-platform OAuth is wired — this endpoint flips the
    status flag and stamps publishedAt so the UI flow works end-to-end."""
    post = await db.social_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Post not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.social_posts.update_one(
        {"id": post_id},
        {"$set": {"status": "published", "publishedAt": now, "publishProvider": "stub"}},
    )
    logger.info("Social publish (stub) → post=%s platform=%s", post_id, post.get("platform"))
    return {"id": post_id, "status": "published", "publishedAt": now}


# ============ AI CONTENT GENERATION ============
@router.post("/social/ai-generate")
async def ai_generate(body: AIGenerateIn, _: dict = Depends(require_owner_or_manager)):
    """Generates caption + hashtags + a one-line image alt for a product,
    promotion or general special. Returns ONE generation per platform
    requested. Falls back to a templated copy when the LLM key is missing
    or upstream errors, so the UX never hits a dead end."""
    # 1. Resolve the source content
    subject_label = ""
    subject_detail = ""
    image_hint = None
    if body.sourceType == "product":
        if not body.sourceId:
            raise HTTPException(400, "sourceId is required for product generation")
        p = await db.products.find_one({"id": body.sourceId}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Product not found")
        subject_label = p.get("name", "our latest dish")
        subject_detail = (
            f"Category: {p.get('category', 'food')}, price ${p.get('price', 0):.2f}. "
            f"Description: {p.get('description') or p.get('seoDescription') or ''}"
        )
        image_hint = p.get("image")
    elif body.sourceType == "promotion":
        if not body.sourceId:
            raise HTTPException(400, "sourceId is required for promotion generation")
        promo = await db.promotions.find_one({"id": body.sourceId}, {"_id": 0})
        if not promo:
            raise HTTPException(404, "Promotion not found")
        subject_label = promo.get("name", "our latest deal")
        subject_detail = (
            f"{promo.get('discount', 0)}% off — schedule: {promo.get('schedule', 'ongoing')}, "
            f"type: {promo.get('type', 'category')}"
        )
    elif body.sourceType == "special":
        subject_label = (body.customPrompt or "Tonight's special")[:80]
        subject_detail = body.customPrompt or "A short, irresistible food highlight."
    else:
        raise HTTPException(400, "sourceType must be product | promotion | special")

    platforms = [p for p in body.platforms if p in SUPPORTED_PLATFORMS] or ["instagram"]
    results = []
    for platform in platforms:
        gen = await _generate_for_platform(
            platform=platform,
            post_type=body.postType or "post",
            tone=body.tone or "warm",
            subject_label=subject_label,
            subject_detail=subject_detail,
            locale=body.locale or "en-AU",
        )
        gen["platform"] = platform
        gen["sourceType"] = body.sourceType
        gen["sourceId"] = body.sourceId
        if image_hint and not gen.get("imageHint"):
            gen["imageHint"] = image_hint
        results.append(gen)
    return {"generations": results}


def _fallback_generation(platform: str, post_type: str, subject_label: str) -> dict:
    """Template used when the LLM key is unavailable or upstream errors."""
    base_tags = ["#nuva", "#restaurant", "#foodie", "#chefspecial"]
    platform_tag = {
        "instagram": "#instafood",
        "facebook": "#facebook",
        "tiktok": "#tiktokfood",
        "x": "#foodtwitter",
        "google_business": "#localfavourite",
    }.get(platform, "#food")
    caption = f"{subject_label} — fresh from our kitchen tonight. Come taste it."
    if post_type == "story":
        caption = f"Tonight only: {subject_label}. Swipe up before it's gone."
    elif post_type == "reel":
        caption = f"30s of {subject_label} pure magic 🎬 (recipe whispered in the comments)."
    return {
        "caption": caption,
        "hashtags": base_tags + [platform_tag],
        "imageAlt": f"A close-up shot of {subject_label}.",
        "isFallback": True,
    }


async def _generate_for_platform(*, platform: str, post_type: str, tone: str,
                                 subject_label: str, subject_detail: str, locale: str) -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return _fallback_generation(platform, post_type, subject_label)
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        # NOTE: do NOT stream here — we need a single JSON envelope back.
        system = (
            f"You are a senior restaurant social media editor writing in {locale}. "
            "Output ONLY a single JSON object with keys caption (string), "
            "hashtags (string array, leading # included, no spaces), and imageAlt (string). "
            "No commentary. No markdown fences. "
            "Captions must respect platform norms: Instagram ≤ 220 chars, "
            "TikTok hooky + emoji-friendly, X ≤ 240 chars total incl hashtags, "
            "Facebook conversational, Google Business factual."
        )
        chat = LlmChat(
            api_key=key,
            session_id=f"social-{uuid.uuid4()}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-6")
        prompt = (
            f"Platform: {platform}. Post type: {post_type}. Tone: {tone}.\n"
            f"Subject: {subject_label}\nDetails: {subject_detail}\n"
            "Return JSON now."
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
        import json
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1] if "```" in cleaned[3:] else cleaned[3:]
            cleaned = cleaned.lstrip("json").strip()
        data = json.loads(cleaned)
        if "caption" not in data or "hashtags" not in data:
            raise ValueError("missing keys")
        data["isFallback"] = False
        return data
    except Exception as exc:
        logger.warning("AI social generation failed (%s) — using fallback", exc)
        out = _fallback_generation(platform, post_type, subject_label)
        out["aiError"] = type(exc).__name__
        return out


@router.get("/social/platforms")
async def list_platforms(_: dict = Depends(get_user)):
    return [
        {"key": k, "label": PLATFORM_LABELS[k]} for k in SUPPORTED_PLATFORMS
    ]
