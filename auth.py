from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from backend.supabase_client import supabase
from postgrest.exceptions import APIError

router = APIRouter()

class SignupRequest(BaseModel):
    email: EmailStr

@router.post("/signup")
def signup(request: SignupRequest):
    # Initiate magic link signup via Supabase Auth
    try:
        result = supabase.auth.sign_in_with_otp({"email": request.email})
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"msg": "Magic link sent to email if it exists."}

@router.get("/me")
def get_me(request: Request):
    # Validate token and return user info
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = auth_header.split(" ")[1]
    try:
        user_resp = supabase.auth.get_user(token)
        user = user_resp.user
        user_id = user.id
        email = user.email
        # Check if user exists in custom users table
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if not result.data:
            # Insert user with default settings
            supabase.table("users").insert({
                "user_id": user_id,
                "email": email
            }).execute()
    except APIError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user 