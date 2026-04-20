from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.apis.proposal import router as proposal_router

app = FastAPI(title="ProposalGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proposal_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to ProposalGuard API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}