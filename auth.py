from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from supabase_client import supabase
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        user_resp = supabase.auth.get_user(token)
        user = user_resp.user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    except APIError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format.")

    try:
        user_id = user.id
        email = user.email
        
        # Check if user exists in the custom 'users' table
        result = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        
        if not result.data:
            # If not, insert the user with default settings
            supabase.table("users").insert({
                "user_id": user_id,
                "email": email,
                "timezone": "UTC",
                "reminder_h": 9,
                "reminder_m": 0,
                "pdf_on": False,
            }).execute()
            
    except APIError as e:
        # This will catch errors related to the 'users' table, like RLS policy violations
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error with user profile: {str(e)}")
        
    return user 