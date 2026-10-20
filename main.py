from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from scraper import LeadScraper

app = FastAPI(title="Lead Scraper SaaS")

templates = Jinja2Templates(directory="templates")
scraper = LeadScraper()

class LeadRequest(BaseModel):
    niche: str
    location: str

class PaymentRequest(BaseModel):
    email: str
    amount: int
    batch_id: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
    return {
        "status": "success",
        "authorization_url": f"https://checkout.paystack.com/mock-{data.batch_id}"
    }
