from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ehr_routes import router as ehr_router
from db_init import init_db

app = FastAPI(title="Blockchain EHR API", version="1.0")

@app.on_event("startup")
def startup():
    init_db()
    print("Database initialized")

# Enable CORS for frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ehr_router)

@app.get("/")
def root():
    return {"message": "Blockchain EHR API running"}
