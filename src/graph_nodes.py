from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from src.vector_store import ProposalVectorStore
from src.config import Config

# 1. Define the LangGraph State
class AgentState(TypedDict):
    job_description: str
    retrieved_proposals: list[str]
    drafted_proposal: str

# 2. Initialize Vector Store
db = ProposalVectorStore()
retriever = db.get_retriever(num_results=2)

# 3. Initialize Gemini
# We use gemini-1.5-flash because it is extremely fast, highly capable, and free via AI Studio
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.7, 
    api_key=Config.GOOGLE_API_KEY
)

# 4. Node 1: Retrieval
def retrieve_past_proposals_node(state: AgentState):
    """Retrieves relevant past work from Chroma DB."""
    print("--- NODE: RETRIEVING PAST PROPOSALS ---")
    query = state["job_description"]
    
    docs = retriever.invoke(query)
    proposals_text = [doc.page_content for doc in docs]
    
    return {"retrieved_proposals": proposals_text}

# 5. Node 2: Generation (Now Powered by Gemini!)
def generate_proposal_node(state: AgentState):
    """Drafts the new proposal using Gemini and retrieved context."""
    print("--- NODE: GENERATING PROPOSAL WITH GEMINI ---")
    
    job = state["job_description"]
    past_work = "\n- ".join(state["retrieved_proposals"])
    
    # Define the system instructions for the AI
    prompt = PromptTemplate.from_template(
        "You are an expert freelance proposal writer. Your goal is to write a highly converting, "
        "concise cover letter for the job described below.\n\n"
        "CRITICAL RULES:\n"
        "1. Do NOT hallucinate skills. ONLY use the experience listed in the 'Past Relevant Work' section.\n"
        "2. Keep it professional, conversational, and under 3 paragraphs.\n"
        "3. Do not use generic, robot-sounding buzzwords.\n\n"
        "Job Description:\n{job_description}\n\n"
        "Past Relevant Work:\n{past_work}\n\n"
        "Drafted Proposal:"
    )
    
    # LangChain Expression Language (LCEL) to pipe the prompt into Gemini
    chain = prompt | llm
    
    # Execute the call
    response = chain.invoke({
        "job_description": job,
        "past_work": past_work
    })
    
    # Update the state with the actual generated text
    return {"drafted_proposal": response.content}


def finalize_proposal_node(state: AgentState):
    """The final step that only runs AFTER human approval."""
    print("--- NODE: FINALIZING PROPOSAL ---")
    print("✅ Proposal Approved and Ready to Send!")
    
    # In a real app, this is where you would trigger an API to send the email/proposal.
    # For now, we just pass the state through.
    return {"drafted_proposal": state["drafted_proposal"]}