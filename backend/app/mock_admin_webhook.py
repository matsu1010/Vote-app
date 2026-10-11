from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Admin Mock Webhook")


@app.post("/webhook")
async def receive_summary(request: Request):
    payload = await request.json()
    print("Received summary payload:", payload)
    return JSONResponse({
        "status": "received",
        "payload": payload
    })
