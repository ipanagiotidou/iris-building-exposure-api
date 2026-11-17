from fastapi import FastAPI

app = FastAPI(
    title="Building Exposure API", 
    description="Building data collection and enrichment for the Netherlands",
    version="0.1.0")


@app.get("/")
def root():
    return {"message": "Building Exposure API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}
