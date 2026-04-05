import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.main import run_proposal_pipeline

# Create a logger
logger = logging.getLogger("proposal_generation_api")
logger.setLevel(logging.DEBUG)


# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()



class ProposalRequest(BaseModel):
    job_description: str


@router.post("/generate_proposal")
def generate_proposal(request: ProposalRequest):
    job_description = request.job_description
    logger.info("Generating proposal for job description: %s...", job_description[:50])

    # Discover resume path
    # We look relative to the project root (where the app is likely run from)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    resume_txt = os.path.join(base_dir, "data", "resumes", "user_resume.txt")
    resume_pdf = os.path.join(base_dir, "data", "resumes", "user_resume.pdf")

    if os.path.exists(resume_txt):
        logger.info("Resume found at %s", resume_txt)
    elif os.path.exists(resume_pdf):
        logger.info("PDF resume found at %s", resume_pdf)
        # return {"error": "PDF resume parsing not implemented yet"}
        # For now, we proceed as the graph might handle it or use the txt if both exist
        # logic in main.py/graph seems to rely on what's in the vector store/context
    else:
        logger.warning("Resume not found in data/resumes/")
        return {"error": "Resume not found, please ensure data/resumes/user_resume.txt exists"}

    try:
        # call the main logic function
        final_state = run_proposal_pipeline(job_description)
        proposal = final_state.get("draft_proposal")

        if proposal is None:
            logger.error("Failed to generate proposal: draft_proposal is None")
            return {"error": "Failed to generate proposal"}

        logger.info("Proposal generated successfully. Status: %s", final_state.get("status"))
        return {
            "proposal": proposal,
            "status": final_state.get("status"),
            "grounding_score": final_state.get("grounding_score")
        }
    except Exception as e:
        logger.exception("Error during proposal generation")
        raise HTTPException(status_code=500, detail=str(e))