from fastapi import FastAPI
from schemas import CheckBase
import uvicorn
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/check")
def check(check: CheckBase):
    return {
        "message": f"{check.name} was checked",
        "status": "ok"}

if __name__ == "__main__":
    uvicorn.run("Back.main.main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                reload_dirs=["Back/"])