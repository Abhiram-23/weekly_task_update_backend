from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.auth import router as auth_router
from backend.crud import router as crud_router

app = FastAPI()

# Allow requests from your frontend (adjust the origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or ["*"] for all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(crud_router, prefix="/entries", tags=["entries"])

@app.get("/")
def read_root():
    return {"msg": "Automatic Weekly Update Generator backend is running."} 