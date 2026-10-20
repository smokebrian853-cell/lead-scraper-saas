import os
import httpx
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from scraper import LeadScraper

# 1. Define app FIRST before any routes use it
app = FastAPI(title="Lead Scraper SaaS")

templates = Jinja2Templates(directory=".")
scraper = LeadScraper()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_fallback")

class LeadRequest(BaseModel):
    niche: str
    location: str

class PaymentRequest(BaseModel):
    email: str
    amount: int
    batch_id: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.post("/api/v1/preview")
async def get_preview(data: LeadRequest):
    leads = await scraper.extract_leads(data.niche, data.location)
    return {
        "batch_id": f"batch_{data.niche.lower()}_{data.location.lower()}",
        "total_extracted": len(leads),
        "preview_leads": leads
    }

@app.post("/api/v1/initialize-payment")
async def initialize_payment(data: PaymentRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            json={
                "email": data.email,
                "amount": data.amount * 100,  # Paystack expects kobo/cents
                "callback_url": f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost:8000')}/success"
            },
            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
        )
        res_data = response.json()
        
        if res_data.get("status"):
            return {
                "status": "success",
                "authorization_url": res_data["data"]["authorization_url"]
            }
        else:
            return {"status": "error", "message": "Could not initialize payment"}
