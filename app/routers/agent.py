from fastapi import APIRouter

router = APIRouter()

@router.post("/agent/chat")
def chat():
    return {"response": "Hello"}
