"""QueueSift HTTP surface (Slice 0: health only; digest UI arrives in Slice 3)."""

from fastapi import FastAPI

app = FastAPI(title="QueueSift", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "queuesift"}
