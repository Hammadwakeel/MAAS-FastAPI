from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    Body for sending a user message to an existing chat session.
    """
    question: str = Field(..., description="The user's question or message.")

class ChatResponse(BaseModel):
    """
    Response from the RAG chatbot endpoint.
    """
    success: bool
    answer: Optional[str] = None
    error: Optional[str] = None
    chat_id: str
    onboarding_id: str

class SetupRequest(BaseModel):
    documents: List[str]
    
class SetupResponse(BaseModel):
    success: bool
    message: str
    onboarding_id: str
    chat_id: str
    vectorstore_path: str