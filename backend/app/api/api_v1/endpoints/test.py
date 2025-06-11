from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def test_endpoint():
    return {"message": "API is working"}
