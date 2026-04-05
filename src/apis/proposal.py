import os
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File  
from pydantic import BaseModel
from src.main import run_proposal_pipeline
from src.vectorStore import ProposalVectorStore
import uuid


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

    # Discover resume path relative to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    resume_txt = os.path.join(base_dir, "data", "resumes", "user_resume.txt")
    resume_pdf = os.path.join(base_dir, "data", "resumes", "user_resume.pdf")

    if os.path.exists(resume_txt):
        logger.info("Resume found at %s", resume_txt)
        with open(resume_txt, "r", encoding="utf-8") as f:
            resume_text = f.read()
    elif os.path.exists(resume_pdf):
        logger.warning("Only PDF resume found — PDF parsing not implemented. Using empty resume.")
        resume_text = "Resume available as PDF but parsing is not yet implemented."
    else:
        logger.warning("Resume not found in data/resumes/")
        return {"error": "Resume not found, please ensure data/resumes/user_resume.txt exists"}

    try:
        # Run the full LangGraph proposal pipeline
        final_state = run_proposal_pipeline(
            job_description=job_description,
            resume_text=resume_text,
        )
        proposal = final_state.get("draft_proposal")

        if proposal is None:
            logger.error("Failed to generate proposal: draft_proposal is None")
            return {"error": "Failed to generate proposal"}

        logger.info("Proposal generated successfully. Status: %s", final_state.get("status"))
        return {
            "proposal": proposal,
            "status": final_state.get("status"),
            "grounding_score": final_state.get("grounding_score"),
        }
    except Exception as e:
        logger.exception("Error during proposal generation")
        raise HTTPException(status_code=500, detail=str(e))


#  Initialize your existing Vector Database
db = ProposalVectorStore()

# 3. Create the Upload Endpoint
@app.post("/api/proposals/upload")
async def upload_proposal(file: UploadFile = File(...)):
    """
    Accepts a .txt file containing a past proposal and saves it to the vector database.
    """
    # Guardrail: Check file extension
    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only .txt files are supported currently."
        )
    
    try:
        # Read the file asynchronously
        content = await file.read()
        
        # Decode the bytes into a standard string
        text_content = content.decode("utf-8")
        
        # Guardrail: Check if the file is empty
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="The provided .txt file is empty.")

        # Generate a unique ID for this document so it doesn't overwrite others
        doc_id = str(uuid.uuid4())
        
        # Create metadata so you know where this vector came from
        metadata = {
            "filename": file.filename,
            "source": "manual_upload",
            "type": "past_proposal"
        }
        
        # Add to Chroma DB using your existing method!
        db.add_proposals(
            texts=[text_content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return {
            "status": "success",
            "message": f"Successfully ingested {file.filename}",
            "document_id": doc_id
        }

    except Exception as e:
        # Catch any encoding or database errors
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")