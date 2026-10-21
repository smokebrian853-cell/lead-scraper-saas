@app.post("/api/v1/initialize-payment")
async def initialize_payment(data: PaymentRequest, request: Request):
    # Dynamically grab host header directly from incoming browser request
    host_url = str(request.base_url).rstrip('/')
    callback_target = f"{host_url}/success"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json={
                    "email": data.email,
                    "amount": data.amount * 100,  # Minor units
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
