from fastapi import APIRouter

router = APIRouter()

@router.get("/cds")
def get_cds():
    return []
