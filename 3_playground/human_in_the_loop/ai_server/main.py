from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_server.api.langgraph import router as langgraph_router

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
    uvicorn.run("ai_server.main:app", host="0.0.0.0", port=2024, reload=True)
