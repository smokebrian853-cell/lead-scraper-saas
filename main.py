import os
import csv
import io
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import httpx
from scraper import LeadScraper

app = FastAPI(title="Self-Serve Lead Scraper Engine")
templates = Jinja2Templates(directory="templates")
scraper = LeadScraper()

# Paste your sk_test_... key here for local testing
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_YOUR_PAYSTACK_SECRET_KEY")

SCRAPED_BATCH_CACHE = {}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/v1/preview")
async def generate_preview(payload: dict):
    niche = payload.get("niche", "").strip()
    location = payload.get("location", "").strip()

    if not niche or not location:
        raise HTTPException(status_code=400, detail="Niche and location are required.")

    leads = await scraper.extract_leads(niche, location, limit=10)
    batch_id = f"{niche}_{location}".lower().replace(" ", "_")
    SCRAPED_BATCH_CACHE[batch_id] = leads

    preview_leads = []
    for idx, lead in enumerate(leads):
        if idx < 2:
            preview_leads.append(lead)
        else:
            preview_leads.append({
                "id": lead["id"],
                "business_name": lead["business_name"],
                "phone": lead["phone"][:6] + "######",
                "email": lead["email"][:3] + "######@####.com",
                "location": lead["location"],
                "verification_status": lead["verification_status"]
            })

    return {
        "batch_id": batch_id,
        "total_extracted": len(leads),
        "preview_leads": preview_leads
    }

@app.post("/api/v1/initialize-payment")
async def initialize_payment(payload: dict):
    email = payload.get("email")
    amount = payload.get("amount", 1500)
    batch_id = payload.get("batch_id")

    if not email or not batch_id:
        raise HTTPException(status_code=400, detail="Email and Batch ID required.")

    paystack_url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "email": email,
        "amount": int(amount) * 100,
        "currency": "KES",
        "metadata": {"batch_id": batch_id},
        "callback_url": f"http://localhost:8000/api/v1/download-csv/{batch_id}"
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(paystack_url, json=data, headers=headers)
            res_data = res.json()

        if res.status_code == 200 and res_data.get("status"):
            return {"authorization_url": res_data["data"]["authorization_url"], "reference": res_data["data"]["reference"]}
        else:
            return {"authorization_url": f"/api/v1/download-csv/{batch_id}", "test_mode": True}
    except Exception:
        return {"authorization_url": f"/api/v1/download-csv/{batch_id}", "test_mode": True}

@app.get("/api/v1/download-csv/{batch_id}")
async def download_csv(batch_id: str):
    leads = SCRAPED_BATCH_CACHE.get(batch_id)
    if not leads:
        raise HTTPException(status_code=404, detail="Batch expired or not found. Please re-run search.")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "business_name", "phone", "email", "location", "verification_status"])
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=verified_leads_{batch_id}.csv"}
    )