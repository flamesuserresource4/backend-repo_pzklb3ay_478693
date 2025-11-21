import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Farm, Practice, Recommendation

app = FastAPI(title="Climate Resilient Agriculture API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Climate Resilient Agriculture API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Seed default practices if collection is empty
@app.post("/seed/practices")
def seed_practices():
    default_practices = [
        {
            "title": "Mulching",
            "description": "Apply organic mulch to conserve soil moisture, regulate temperature, and suppress weeds.",
            "crops": ["maize", "vegetables", "fruit"],
            "risks": ["drought", "heat"],
            "cost_level": "low",
            "benefits": ["moisture conservation", "soil health", "reduced irrigation needs"],
            "prerequisites": "Access to crop residues or organic mulch materials",
        },
        {
            "title": "Zai Pits / Planting Basins",
            "description": "Small basins that capture runoff to improve infiltration and water availability in arid zones.",
            "crops": ["maize", "sorghum", "millet"],
            "risks": ["drought"],
            "cost_level": "low",
            "benefits": ["water harvesting", "yield stability"],
            "prerequisites": "Labor investment for digging basins",
        },
        {
            "title": "Drought-tolerant Varieties",
            "description": "Use improved varieties bred for drought/heat tolerance.",
            "crops": ["maize", "wheat", "rice", "beans"],
            "risks": ["drought", "heat"],
            "cost_level": "medium",
            "benefits": ["yield stability", "reduced crop failure risk"],
            "prerequisites": "Access to certified seed suppliers",
        },
        {
            "title": "Raised Beds",
            "description": "Improve drainage to reduce waterlogging and root disease risk in heavy rains.",
            "crops": ["vegetables"],
            "risks": ["flood"],
            "cost_level": "low",
            "benefits": ["better drainage", "root health"],
            "prerequisites": None,
        },
        {
            "title": "Drip Irrigation",
            "description": "Efficient irrigation delivering water to the root zone, minimizing losses.",
            "crops": ["vegetables", "fruit"],
            "risks": ["drought", "heat"],
            "cost_level": "high",
            "benefits": ["water savings", "higher water productivity"],
            "prerequisites": "Capital for system and simple filtration",
        },
        {
            "title": "Agroforestry (Windbreaks/Shade)",
            "description": "Integrate trees to reduce heat stress, wind damage, and improve microclimate.",
            "crops": ["coffee", "cocoa", "vegetables", "maize"],
            "risks": ["heat", "wind", "drought"],
            "cost_level": "medium",
            "benefits": ["microclimate regulation", "soil health", "biodiversity"],
            "prerequisites": "Space and species selection guidance",
        },
    ]

    inserted = 0
    existing = list(db["practice"].find({})) if db else []
    if existing:
        return {"status": "ok", "message": "Practices already seeded", "count": len(existing)}

    for p in default_practices:
        create_document("practice", p)
        inserted += 1

    return {"status": "ok", "inserted": inserted}


# Create a farm profile
@app.post("/farms")
def create_farm(farm: Farm):
    farm_id = create_document("farm", farm)
    return {"id": farm_id}


# List/search practices
class PracticeQuery(BaseModel):
    crop: Optional[str] = None
    risk: Optional[str] = None
    cost: Optional[str] = None
    q: Optional[str] = None


@app.get("/practices")
def list_practices(
    crop: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    cost: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    filter_dict = {}
    if crop:
        filter_dict["crops"] = {"$in": [crop.lower()]}
    if risk:
        filter_dict["risks"] = {"$in": [risk.lower()]}
    if cost:
        filter_dict["cost_level"] = cost.lower()

    results = get_documents("practice", filter_dict)

    # Basic text search client-side filter
    if q:
        ql = q.lower()
        results = [
            r
            for r in results
            if ql in r.get("title", "").lower()
            or ql in r.get("description", "").lower()
        ]

    # Convert ObjectId to str
    for r in results:
        if "_id" in r:
            r["id"] = str(r.pop("_id"))
    return {"items": results}


# Get tailored recommendations for a farm profile (not stored)
class FarmInput(BaseModel):
    crops: List[str] = []
    risks: List[str] = []
    budget: Optional[str] = None


@app.post("/recommendations")
def get_recommendations(payload: FarmInput):
    # Load all practices
    practices = get_documents("practice", {})

    recs: List[Recommendation] = []
    crops = {c.lower() for c in payload.crops}
    risks = {r.lower() for r in payload.risks}
    budget = payload.budget.lower() if payload.budget else None

    for p in practices:
        p_crops = set([c.lower() for c in p.get("crops", [])])
        p_risks = set([r.lower() for r in p.get("risks", [])])
        p_cost = p.get("cost_level", "").lower()

        crop_overlap = len(crops & p_crops)
        risk_overlap = len(risks & p_risks)
        cost_match = 1 if (not budget or p_cost == budget) else 0

        score = 0.5 * (crop_overlap > 0) + 0.4 * (risk_overlap > 0) + 0.1 * cost_match
        if crop_overlap or risk_overlap:
            reasons = []
            if crop_overlap:
                reasons.append("Matches your crops")
            if risk_overlap:
                reasons.append("Addresses stated risks")
            if cost_match:
                reasons.append("Fits your budget")

            recs.append(
                Recommendation(
                    practice_title=p.get("title", ""),
                    match_score=round(float(score), 2),
                    reasons=reasons,
                    cost_level=p_cost,
                    risks=list(p_risks),
                    crops=list(p_crops),
                )
            )

    # Sort by score desc
    recs.sort(key=lambda x: x.match_score, reverse=True)

    return {"items": [r.model_dump() for r in recs[:20]]}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
