"""Admin-managed site content: header, footer, home page and legal pages."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime, timezone
import re, uuid

StatSource = Literal["students", "questions", "tests", "attempts", "live", "manual"]


class LinkItem(BaseModel):
    label: str
    url: str


class HeaderIn(BaseModel):
    brand_name: str = "ExamForge"
    nav_links: List[LinkItem] = []
    cta_label: str = "Get Started"
    cta_url: str = "/register"


class HeroIn(BaseModel):
    badge_text: str = ""
    title: str = ""
    highlight: str = ""
    subtitle: str = ""
    primary_cta_label: str = ""
    primary_cta_url: str = ""
    secondary_cta_label: str = ""
    secondary_cta_url: str = ""


class StatIn(BaseModel):
    label: str
    source: StatSource = "manual"
    override: str = ""


class FeatureIn(BaseModel):
    icon: str = "Target"
    title: str
    desc: str = ""


class FooterIn(BaseModel):
    tagline: str = ""
    copyright: str = ""
    links: List[LinkItem] = []


class HomeIn(BaseModel):
    hero: HeroIn
    stats: List[StatIn] = Field(default_factory=list, max_length=6)
    features: List[FeatureIn] = []


class LayoutIn(BaseModel):
    header: HeaderIn
    footer: FooterIn


class PageIn(BaseModel):
    title: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    content: str = ""
    published: bool = True


DEFAULTS = {
    "header": {
        "brand_name": "ExamForge",
        "nav_links": [{"label": "Test Series", "url": "/test-series"}, {"label": "Courses", "url": "/courses"},
                      {"label": "Study Materials", "url": "/study-materials"}, {"label": "Leaderboard", "url": "/leaderboard"}],
        "cta_label": "Get Started", "cta_url": "/register",
    },
    "hero": {
        "badge_text": "LIVE · {live} ASPIRANTS NOW ATTEMPTING",
        "title": "Crack competitive exams with a",
        "highlight": "precision test engine",
        "subtitle": "Full-length mocks for SSC, UPSC, Banking, Railways, NEET & JEE — real exam timers, detailed answer analytics, and courses by top faculty.",
        "primary_cta_label": "Explore Test Series", "primary_cta_url": "/test-series",
        "secondary_cta_label": "Create Free Account", "secondary_cta_url": "/register",
    },
    "stats": [{"label": "Students", "source": "students", "override": ""},
              {"label": "Questions", "source": "questions", "override": ""},
              {"label": "Mock Tests", "source": "tests", "override": ""}],
    "features": [
        {"icon": "Target", "title": "Real Exam Simulation", "desc": "Server-authoritative timer, question palette, mark-for-review — a replica of actual exam portals."},
        {"icon": "TrendingUp", "title": "Deep Analytics", "desc": "Topic-wise accuracy, time per question, strengths & weaknesses — know where to focus."},
        {"icon": "Award", "title": "Verified Content", "desc": "Questions crafted and reviewed by top faculty for SSC, UPSC, Banking, Railways and NEET/JEE."},
    ],
    "footer": {
        "tagline": "Precision test series and courses for India's competitive exams.",
        "copyright": "© 2026 ExamForge · All rights reserved.",
        "links": [{"label": "Privacy", "url": "/page/privacy"}, {"label": "Terms", "url": "/page/terms"},
                  {"label": "Refund Policy", "url": "/page/refund-policy"}, {"label": "Contact", "url": "/page/contact"}],
    },
}

SEED_PAGES = [
    ("Privacy Policy", "privacy", "## Information we collect\nWe collect your name, email and exam activity to run your account and show your results.\n\n## How we use it\nYour data is used only to provide tests, rankings and course access. We never sell it.\n\n## Contact\nWrite to us from the Contact page for any privacy request."),
    ("Terms of Service", "terms", "## Using ExamForge\nBy creating an account you agree to use the platform for personal exam preparation only.\n\n## Content\nAll questions, tests and course material are the property of ExamForge and may not be copied or redistributed.\n\n## Accounts\nWe may suspend accounts that share logins or attempt to tamper with exams."),
    ("Refund Policy", "refund-policy", "## Eligibility\nRefunds can be requested within 7 days of purchase if you have not attempted more than one test of the purchased series.\n\n## Process\nContact support with your order ID. Approved refunds are returned to the original payment method within 5–7 working days."),
    ("Contact Us", "contact", "## Get in touch\n**Email:** support@examforge.in\n\n**Hours:** Monday to Saturday, 10 AM – 6 PM IST"),
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M+"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "K+"
    return str(n)


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


async def seed_pages(db):
    for title, slug, content in SEED_PAGES:
        if not await db.pages.find_one({"slug": slug}):
            await db.pages.insert_one({"id": str(uuid.uuid4()), "title": title, "slug": slug, "content": content,
                                       "published": True, "created_at": _now(), "updated_at": _now()})


def build_site_router(db, require_roles):
    r = APIRouter(prefix="/api")
    admin = Depends(require_roles("admin"))

    async def content():
        doc = await db.settings.find_one({"key": "site"}, {"_id": 0}) or {}
        return {k: doc.get(k, v) for k, v in DEFAULTS.items()}

    async def metrics():
        return {
            "students": await db.users.count_documents({"role": "student"}),
            "questions": await db.questions.count_documents({}),
            "tests": await db.tests.count_documents({}),
            "attempts": await db.test_attempts.count_documents({}),
            "live": await db.test_attempts.count_documents({"status": "in_progress"}),
        }

    async def save(fields: dict, user):
        await db.settings.update_one({"key": "site"}, {"$set": {**fields, "updated_at": _now(), "updated_by": user["id"]}}, upsert=True)
        return await content()

    @r.get("/site")
    async def public_site():
        c, m = await content(), await metrics()
        for s in c["stats"]:
            s["display"] = s["override"] or (_compact(m.get(s["source"], 0)) if s["source"] != "manual" else "")
        c["hero"] = {**c["hero"], "badge_text": c["hero"]["badge_text"].replace("{live}", f"{m['live']:,}")}
        return {**c, "metrics": m}

    @r.get("/admin/site")
    async def admin_site(_=admin):
        return {**(await content()), "metrics": await metrics()}

    @r.put("/admin/site/layout")
    async def save_layout(data: LayoutIn, user=admin):
        return await save(data.model_dump(), user)

    @r.put("/admin/site/home")
    async def save_home(data: HomeIn, user=admin):
        return await save(data.model_dump(), user)

    @r.get("/pages/{slug}")
    async def public_page(slug: str):
        p = await db.pages.find_one({"slug": slug, "published": True}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Page not found")
        return p

    @r.get("/admin/pages")
    async def list_pages(_=admin):
        return await db.pages.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)

    async def _clean(data: PageIn, exclude_id: Optional[str] = None) -> dict:
        slug = _slugify(data.slug)
        if not slug:
            raise HTTPException(400, "Invalid slug")
        q = {"slug": slug, **({"id": {"$ne": exclude_id}} if exclude_id else {})}
        if await db.pages.find_one(q):
            raise HTTPException(400, "A page with this slug already exists")
        return {**data.model_dump(), "slug": slug, "updated_at": _now()}

    @r.post("/admin/pages")
    async def create_page(data: PageIn, _=admin):
        doc = {"id": str(uuid.uuid4()), **(await _clean(data)), "created_at": _now()}
        await db.pages.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.put("/admin/pages/{page_id}")
    async def update_page(page_id: str, data: PageIn, _=admin):
        res = await db.pages.update_one({"id": page_id}, {"$set": await _clean(data, page_id)})
        if not res.matched_count:
            raise HTTPException(404, "Page not found")
        return await db.pages.find_one({"id": page_id}, {"_id": 0})

    @r.delete("/admin/pages/{page_id}")
    async def delete_page(page_id: str, _=admin):
        await db.pages.delete_one({"id": page_id})
        return {"ok": True}

    return r
