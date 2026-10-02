from fastapi import FastAPI

app = FastAPI(title="Vote App Local Backend")

@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "local-first"}
