import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.langgraph import router as langgraph_router

app = FastAPI(title="LangGraph Agent Server")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/ok")
def health_check():
    return {"status": "ok"}

# Include LangGraph router
app.include_router(langgraph_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=2024, reload=True)
