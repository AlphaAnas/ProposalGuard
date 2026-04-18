# Proposal Guard
An agentic AI system that writes personalized proposals and cover letters for freelancers on freelance platforms based on their past proposals and relevance to job description a/w human-in-the-loop review, and responsible AI guardrails.
###  The Problem
We are building an agentic AI system that drafts highly personalized proposals and cover letters by grounding them in a freelancer’s actual past work and portfolio data. This matters because current AI tools often hallucinate credentials or produce generic, "robot-sounding" text that hurts conversion rates. Furthermore, standard LLMs can exhibit demographic bais that disadvantages certain groups; our solution integrates human-in-the-loop review and safety guardrails to ensure every proposal is factual, professional, and free from harmful bias before it gets sent.

--- 
## Setting up 

### Create a virtual environment
- Linux 
```bash
python -m venv venv
```
### Activate the virtual environment
-  On macOS/Linux:
```bash
source venv/bin/activate
```
-  On Windows:
```bash
 venv\Scripts\activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```
### Setting up environment variables
- Create a .env file in the root directory
- Add the following variables to the .env file
```bash
GOOGLE_API_KEY=your_google_api_key
CHROMA_DB_PATH=./chroma_db  
GOOGLE_API_KEY=<your key>
CHROMA_DB_PATH=./chroma_db  
LANGSMITH_API_KEY=<your key>
LANGSMITH_TRACING=true
LANGSMITH_PROJECT="ProposalGuard"
``` 
### Run the pipeline 
Run the following command from root directory   
```bash
uvicorn src.app:app --reload    
```

### Test the API
- Open the following URL in your browser: http://127.0.0.1:8000/docs
- Click on "POST /generate" and then "Try it out"
- Enter a job description and click "Execute"  

### Example job description
```bash
"Looking for a senior full-stack developer to build an AI-powered customer support dashboard. Must be proficient in Next.js, TypeScript, Supabase, and Tailwind CSS. Experience with AI integrations and data visualization is a plus. The dashboard will help businesses automate responses and analyze customer interactions."
``` 

## Setting up Vector DB
Run the `/proposals/upload` endpoint to upload past proposals to the vector database. 


