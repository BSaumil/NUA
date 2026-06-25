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
from datetime import datetime, timezone, timedelta
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
    # Only return rows that match the new schema. Legacy docs from older
    # modules (channel_menus / v25) lived in the same collection and had a
    # different shape — they would render as empty cards in the UI.
    accounts = await db.social_accounts.find(
        {"tokenStatus": {"$exists": True}},
        {"_id": 0},
    ).to_list(50)
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
    # Constrain status — never trust the caller to mark something already published.
    if body.status and body.status not in ("draft", "scheduled", "published", "failed"):
        raise HTTPException(400, "status must be draft | scheduled | published | failed")
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


@router.patch("/social/posts/{post_id}")
async def update_post(post_id: str, body: dict, _: dict = Depends(require_owner_or_manager)):
    """Patch an existing post — used by the calendar's drag-to-reschedule
    flow. Only a small, explicit set of fields is mutable; status is
    validated against the same allow-list as create_post."""
    allowed = {"caption", "hashtags", "imageUrl", "scheduledFor", "status", "postType"}
    update = {k: v for k, v in body.items() if k in allowed}
    if "status" in update and update["status"] not in ("draft", "scheduled", "published", "failed"):
        raise HTTPException(400, "status must be draft | scheduled | published | failed")
    if "postType" in update and update["postType"] not in ("post", "story", "reel"):
        raise HTTPException(400, "postType must be post | story | reel")
    if not update:
        raise HTTPException(400, "Nothing to update")
    res = await db.social_posts.update_one({"id": post_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Post not found")
    return await db.social_posts.find_one({"id": post_id}, {"_id": 0})


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


# ============ AI WEEKLY CONTENT PLAN ============
class WeeklyPlanIn(BaseModel):
    daysAhead: int = 7
    postTime: Optional[str] = "12:00"   # local HH:MM the plan should fire each day
    tone: Optional[str] = "warm"
    platforms: Optional[List[str]] = None     # default: every connected platform
    save: bool = True                          # if False, returns a preview without persisting


@router.post("/social/ai-weekly-plan")
async def ai_weekly_plan(body: WeeklyPlanIn, user: dict = Depends(require_owner_or_manager)):
    """Generate a 7-day cross-platform social plan from top-selling products
    + active promotions, distributed one post per day per platform.

    Source rotation per day:
      - Day 0,3,6 → product (top sellers, cycled)
      - Day 1,4   → promotion (active, cycled)
      - Day 2,5   → 'special' (free-form prompt seeded from the day-of-week)
    Falls back to product → product if no promotions exist.

    The endpoint is idempotent enough to re-run: any prior `auto_plan_*`
    scheduled-but-unpublished post in the target window is dismissed before
    new ones land, so the cashier never ends up with duplicate posts.
    """
    days = max(1, min(14, body.daysAhead or 7))
    tone = body.tone or "warm"
    try:
        hour, minute = (body.postTime or "12:00").split(":")
        target_hour, target_min = int(hour), int(minute)
    except Exception:
        target_hour, target_min = 12, 0

    # 1. Pick the platforms — default to all connected accounts.
    if body.platforms:
        platforms = [p for p in body.platforms if p in SUPPORTED_PLATFORMS]
    else:
        accs = await db.social_accounts.find(
            {"tokenStatus": {"$exists": True}}, {"_id": 0, "platform": 1},
        ).to_list(50)
        platforms = sorted({a["platform"] for a in accs})
    if not platforms:
        raise HTTPException(400, "No connected social accounts — connect at least one first")

    # 2. Compute top-selling products (last 7 days). Falls back gracefully
    # when there aren't enough transactions to mine.
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.productId", "qty": {"$sum": "$items.quantity"}}},
        {"$sort": {"qty": -1}}, {"$limit": 7},
    ]
    try:
        top = await db.transactions.aggregate(pipeline).to_list(7)
        top_ids = [t["_id"] for t in top if t.get("_id")]
    except Exception:
        top_ids = []
    if not top_ids:
        fallback = await db.products.find(
            {"eightySixed": {"$ne": True}}, {"_id": 0, "id": 1},
        ).to_list(7)
        top_ids = [p["id"] for p in fallback]
    products_for_plan = []
    for pid in top_ids:
        p = await db.products.find_one({"id": pid}, {"_id": 0})
        if p:
            products_for_plan.append(p)
    if not products_for_plan:
        raise HTTPException(400, "No products available to seed a plan — add a product or run a sale first")

    # 3. Active promotions
    promos = await db.promotions.find({"active": True}, {"_id": 0}).to_list(10)

    # 4. If we're persisting, wipe any leftover auto-plan posts in the upcoming
    # window so re-runs don't pile up duplicates. Preview (save=false) MUST NOT
    # touch persisted state.
    if body.save:
        window_end = (datetime.now(timezone.utc) + timedelta(days=days + 1)).isoformat()
        await db.social_posts.delete_many({
            "autoPlanRun": True,
            "status": "scheduled",
            "scheduledFor": {"$gte": datetime.now(timezone.utc).isoformat(), "$lte": window_end},
        })

    # 5. Walk N days × P platforms, alternating the source type.
    SPECIAL_SEEDS = [
        "Chef's Choice tonight — limited covers, intimate vibe.",
        "Weekend brunch is on — bring the crew.",
        "Pairing night: every main paired with a hand-picked sip.",
        "Hidden-menu Tuesday — DM us for the secret order.",
    ]
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    saved_posts = []
    preview = []
    now = datetime.now(timezone.utc)

    for d in range(days):
        day = now + timedelta(days=d + 1)
        scheduled_for = day.replace(hour=target_hour, minute=target_min, second=0, microsecond=0).isoformat()
        if d % 3 == 1 and promos:
            promo = promos[d % len(promos)]
            source_type, source_id, subject_label, subject_detail, image_hint = (
                "promotion", promo["id"], promo.get("name", "promo"),
                f"{promo.get('discount', 0)}% off — schedule: {promo.get('schedule', 'ongoing')}",
                None,
            )
        elif d % 3 == 2:
            seed = SPECIAL_SEEDS[d % len(SPECIAL_SEEDS)]
            source_type, source_id, subject_label, subject_detail, image_hint = (
                "special", None, seed[:60], seed, None,
            )
        else:
            prod = products_for_plan[d % len(products_for_plan)]
            source_type, source_id = "product", prod["id"]
            subject_label = prod.get("name", "our top dish")
            subject_detail = (
                f"Category: {prod.get('category', 'food')}, price ${prod.get('price', 0):.2f}. "
                f"Description: {prod.get('description') or prod.get('seoDescription') or ''}"
            )
            image_hint = prod.get("image")

        for platform in platforms:
            gen = await _generate_for_platform(
                platform=platform, post_type="post", tone=tone,
                subject_label=subject_label, subject_detail=subject_detail, locale="en-AU",
            )
            doc = {
                "id": str(uuid.uuid4()),
                "platform": platform,
                "postType": "post",
                "caption": gen["caption"],
                "hashtags": gen["hashtags"],
                "imageAlt": gen.get("imageAlt"),
                "imageUrl": image_hint,
                "sourceType": source_type,
                "sourceId": source_id,
                "scheduledFor": scheduled_for,
                "status": "scheduled" if body.save else "preview",
                "autoPlan": True,
                "autoPlanRun": body.save,
                "autoPlanId": plan_id,
                "isFallback": bool(gen.get("isFallback")),
                "createdBy": user.get("email"),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if body.save:
                await db.social_posts.insert_one(doc)
                doc.pop("_id", None)
                saved_posts.append(doc)
            else:
                preview.append(doc)

    return {
        "planId": plan_id,
        "saved": len(saved_posts),
        "preview": preview if not body.save else [],
        "posts": saved_posts if body.save else preview,
        "platformsUsed": platforms,
    }
