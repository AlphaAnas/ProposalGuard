from fastapi import FastAPI
from src.apis.proposal import router as proposal_router
app = FastAPI() 

app.include_router(proposal_router) 

@app.get("/")
def read_root():
    return {"message": "Welcome to ProposalGuard API"}

@app.get("/health")
def health_check():
    return {"status": "ok"} 
