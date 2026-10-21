import os
import httpx
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from scraper import LeadScraper

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

# 1. ADD THIS SUCCESS ROUTE FOR PAYSTACK REDIRECTS
@app.get("/success", response_class=HTMLResponse)
async def payment_success(request: Request):
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html class="bg-slate-950 text-white flex items-center justify-center h-screen">
    <head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="text-center p-6">
        <div class="bg-slate-900 border border-slate-800 p-8 rounded-3xl max-w-md mx-auto shadow-2xl">
            <div class="h-12 w-12 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">✓</div>
            <h1 class="text-2xl font-black mb-2">Payment Confirmed</h1>
            <p class="text-slate-400 text-sm mb-6">Your data export has been unlocked. Check your email or click below to return to terminal.</p>
            <a href="/" class="inline-block bg-emerald-500 text-slate-950 font-bold px-6 py-3 rounded-xl hover:bg-emerald-400 transition">Return to Terminal</a>
        </div>
    </body>
    </html>
    """)

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
    # Dynamically determine host URL so callback never defaults to localhost on Render
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    callback_target = f"https://{render_url}/success" if render_url else "http://localhost:8000/success"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json={
                    "email": data.email,
                    "amount": data.amount * 100,  # Paystack expects minor units
                    "callback_url": callback_target
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
                return {"status": "error", "message": res_data.get("message", "Payment error")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
