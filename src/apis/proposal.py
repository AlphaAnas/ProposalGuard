import os
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command
from src.graph import graph
from src.vectorStore import ProposalVectorStore

logger = logging.getLogger("proposal_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter()


class ProposalRequest(BaseModel):
    job_description: str


class ResumeRequest(BaseModel):
    action: str       # "approve" or "reject"
    feedback: str = None


def _load_resume() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    resume_txt = os.path.join(base_dir, "data", "resumes", "user_resume.txt")
    if os.path.exists(resume_txt):
        with open(resume_txt, "r", encoding="utf-8") as f:
            return f.read()
    return "No resume found."


def _safe_json(obj):
    """Make an object JSON-serializable by converting non-serializable values to strings."""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_safe_json(item) for item in obj]
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


# -----------------------------------------------------------------------
# SSE Streaming endpoint — streams per-node events to the frontend
# -----------------------------------------------------------------------
@router.post("/proposals/generate")
async def generate_proposal_stream(request: ProposalRequest):
    thread_id = str(uuid.uuid4())
    resume_text = _load_resume()

    initial_state = {
        "rfp_text": request.job_description,
        "job_description": request.job_description,
        "resume_text": resume_text,
        "retrieved_context": [],
        "retrieval_results": [],
        "draft_proposal": None,
        "generation_metadata": {},
        "grounding_score": 0.0,
        "extracted_claims": [],
        "supported_claims": [],
        "unsupported_claims": [],
        "bias_flags": [],
        "bias_evaluation": {},
        "baseline_profile": {},
        "human_feedback": None,
        "retry_count": 0,
        "status": "new",
    }

    config = {"configurable": {"thread_id": thread_id}}

    def event_stream():
        try:
            # Send thread_id so frontend can use it for resume
            yield f"event: thread_id\ndata: {json.dumps({'thread_id': thread_id})}\n\n"

            # Stream per-node events
            for event in graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    payload = {
                        "node": node_name,
                        "data": _safe_json(state_update),
                    }
                    yield f"event: node_complete\ndata: {json.dumps(payload)}\n\n"

            # Check if pipeline is paused at interrupt
            state = graph.get_state(config)
            if state.next:
                # Paused — send interrupt event with full state for review
                vals = state.values
                interrupt_data = {
                    "thread_id": thread_id,
                    "proposal": vals.get("draft_proposal", ""),
                    "grounding_score": vals.get("grounding_score", 0.0),
                    "extracted_claims": vals.get("extracted_claims", []),
                    "supported_claims": vals.get("supported_claims", []),
                    "unsupported_claims": vals.get("unsupported_claims", []),
                    "bias_flags": vals.get("bias_flags", []),
                    "bias_evaluation": _safe_json(vals.get("bias_evaluation", {})),
                    "retrieval_results": _safe_json(vals.get("retrieval_results", [])),
                    "generation_metadata": _safe_json(vals.get("generation_metadata", {})),
                    "retry_count": vals.get("retry_count", 0),
                    "status": "awaiting_review",
                }
                yield f"event: interrupt\ndata: {json.dumps(interrupt_data)}\n\n"
            else:
                # Pipeline completed (no interrupt hit — shouldn't happen normally)
                vals = state.values
                done_data = _safe_json({
                    "proposal": vals.get("draft_proposal", ""),
                    "grounding_score": vals.get("grounding_score", 0.0),
                    "bias_flags": vals.get("bias_flags", []),
                    "status": vals.get("status", "complete"),
                    "retry_count": vals.get("retry_count", 0),
                })
                yield f"event: complete\ndata: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.exception("Error during pipeline streaming")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -----------------------------------------------------------------------
# Resume endpoint — continues pipeline after human review
# -----------------------------------------------------------------------
@router.post("/proposals/{thread_id}/resume")
async def resume_proposal(thread_id: str, request: ResumeRequest):
    config = {"configurable": {"thread_id": thread_id}}

    # Verify this thread exists and is interrupted
    state = graph.get_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="This pipeline is not awaiting review.")

    user_decision = {
        "action": request.action,
        "feedback": request.feedback,
    }

    try:
        result = graph.invoke(Command(resume=user_decision), config=config)
        return _safe_json({
            "proposal": result.get("draft_proposal", ""),
            "status": result.get("status", ""),
            "grounding_score": result.get("grounding_score", 0.0),
            "bias_flags": result.get("bias_flags", []),
            "bias_evaluation": result.get("bias_evaluation", {}),
            "retry_count": result.get("retry_count", 0),
        })
    except Exception as e:
        logger.exception("Error resuming pipeline")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------
# Legacy synchronous endpoint (backward compat)
# -----------------------------------------------------------------------
@router.post("/proposals/generate_proposal")
def generate_proposal_sync(request: ProposalRequest):
    from src.main import run_proposal_pipeline
    resume_text = _load_resume()
    try:
        final_state = run_proposal_pipeline(
            job_description=request.job_description,
            resume_text=resume_text,
        )
        return {
            "proposal": final_state.get("draft_proposal"),
            "status": final_state.get("status"),
            "grounding_score": final_state.get("grounding_score"),
        }
    except Exception as e:
        logger.exception("Error during proposal generation")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------
# Upload endpoint
# -----------------------------------------------------------------------
db = ProposalVectorStore()

@router.post("/proposals/upload")
async def upload_proposal(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files supported.")
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="File is empty.")
        doc_id = str(uuid.uuid4())
        metadata = {"filename": file.filename, "source": "manual_upload", "type": "past_proposal"}
        db.add_proposals(texts=[text_content], metadatas=[metadata], ids=[doc_id])
        return {"status": "success", "message": f"Ingested {file.filename}", "document_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposals/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files supported.")
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="File is empty.")
        
        # Save to the data/resumes directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        resume_path = os.path.join(base_dir, "data", "resumes", "user_resume.txt")
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        with open(resume_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        return {"status": "success", "message": f"Resume saved: {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))