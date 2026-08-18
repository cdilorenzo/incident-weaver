from fastapi import FastAPI

app = FastAPI(title="IncidentWeaver AI Runtime")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}