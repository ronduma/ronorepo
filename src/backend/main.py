from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/api")


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(router)        