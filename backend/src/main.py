from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ehr_routes import router as ehr_router

app = FastAPI(title="Blockchain EHR API", version="1.0")

# Enable CORS for frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set specific domains later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ehr_router)

@app.get("/")
def root():
    return {"message": "Blockchain EHR API running"}
