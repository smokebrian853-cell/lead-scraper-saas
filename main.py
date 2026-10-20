import os
import httpx
# ... (keep your other imports)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_fallback")

@app.post("/api/v1/initialize-payment")
async def initialize_payment(data: PaymentRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            json={
                "email": data.email,
                "amount": data.amount * 100, # Paystack expects amount in minor units (cents)
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
