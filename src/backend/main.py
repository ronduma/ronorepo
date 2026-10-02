from fastapi import APIRouter, FastAPI

from routers import ollama

app = FastAPI()
router = APIRouter(prefix="/api")


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/health")
async def health():
    return {"status": "ok"}


router.include_router(ollama.router)
app.include_router(router)
