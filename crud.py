from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.supabase_client import supabase
from postgrest.exceptions import APIError
from datetime import datetime, timedelta
import os
import httpx
from fastapi import Body
from backend.config import GEMINI_API_KEY
import google.generativeai as genai
import json
from datetime import datetime

router = APIRouter()

class EntryCreate(BaseModel):
    user_id: str
    date: str  # YYYY-MM-DD
    text: str

class EntryUpdate(BaseModel):
    entry_id: str
    text: str

class EntryOut(BaseModel):
    entry_id: str
    user_id: str
    date: str
    text: str

# User Settings Models
class UserSettings(BaseModel):
    user_id: str
    timezone: str
    reminder_h: int
    reminder_m: int
    pdf_on: bool

class UserSettingsUpdate(BaseModel):
    user_id: str
    timezone: Optional[str] = None
    reminder_h: Optional[int] = None
    reminder_m: Optional[int] = None
    pdf_on: Optional[bool] = None

class GeminiRequest(BaseModel):
    user_id: str
    week_start: str
    week_end: str
    entries: dict  # {"Monday": "...", ...}

class GeminiResponse(BaseModel):
    summary: str

@router.post("/", response_model=EntryOut)
def create_entry(entry: EntryCreate):
    # Prevent duplicate per day
    print(entry)
    try:
        existing = supabase.table("entries").select("*").eq("user_id", entry.user_id).eq("date", entry.date).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if existing.data:
        raise HTTPException(status_code=400, detail="Entry for this date already exists.")
    try:
        result = supabase.table("entries").insert(entry.dict()).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.data[0]

@router.get("/", response_model=List[EntryOut])
def list_entries(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    query = supabase.table("entries").select("*").eq("user_id", user_id)
    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)
    try:
        result = query.order("date").execute()
        print(result)
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.data

@router.put("/", response_model=EntryOut)
def update_entry(entry: EntryUpdate):
    try:
        result = supabase.table("entries").update({"text": entry.text}).eq("entry_id", entry.entry_id).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.data[0]

@router.get("/settings/{user_id}", response_model=UserSettings)
def get_user_settings(user_id: str):
    try:
        result = supabase.table("users").select("user_id, timezone, reminder_h, reminder_m, pdf_on").eq("user_id", user_id).single().execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data

@router.put("/settings/{user_id}", response_model=UserSettings)
def update_user_settings(user_id: str, update: UserSettingsUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None and k != "user_id"}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        result = supabase.table("users").update(update_data).eq("user_id", user_id).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    return result.data[0]

@router.get("/weekly/{user_id}")
def get_weekly_entries(user_id: str, week_start: str):
    """
    Aggregate entries for a user for the week starting on week_start (YYYY-MM-DD, must be a Monday).
    Returns a dict: {"Monday": ..., "Tuesday": ..., ..., "Friday": ...}
    """
    try:
        start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid week_start format. Use YYYY-MM-DD.")
    if start_date.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start must be a Monday.")
    end_date = start_date + timedelta(days=4)
    try:
        result = supabase.table("entries").select("date, text").eq("user_id", user_id).gte("date", str(start_date)).lte("date", str(end_date)).order("date").execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Map dates to weekdays
    day_map = {i: day for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])}
    entries_by_day = {day: None for day in day_map.values()}
    for entry in result.data:
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        weekday = entry_date.weekday()
        if weekday in day_map:
            entries_by_day[day_map[weekday]] = entry["text"]
    return {"week_start": str(start_date), "week_end": str(end_date), "entries": entries_by_day}

@router.post("/gemini/summary", response_model=GeminiResponse)
def gemini_summary(request: GeminiRequest):
    """
    Call Gemini LLM API to summarize the week's entries using the official SDK
    and your custom few-shot prompt. Also save the report in the DB.
    """
    FEW_SHOT_PROMPT = """
        You are an expert workplace communicator. Your task is to convert a user's raw daily entries into one concise, professional paragraph summarizing the week's accomplishments. Use first person, mention key collaborators by name, and maintain an upbeat, collaborative tone.

        ### Example 1  
        INPUT:
        {
        "Monday":    "Reviewed the resources James shared and began developing a new design for CAIN.",
        "Tuesday":   "Discussed initial ideas with James and was asked to create a layout inspired by Microsoft 365 Copilot.",
        "Wednesday": "Built a functional prototype of the Copilot-like interface.",
        "Thursday":  "Collaborated with James to structure the CAIN module internally.",
        "Friday":    "Refined the prototype based on James's feedback and prepared documentation for next week."
        }

        OUTPUT:
        This week, I reviewed the resources James shared and kicked off the new CAIN design, then after discussing concepts he asked me to craft a layout inspired by Microsoft 365 Copilot. I proceeded to build a working prototype of that interface and collaborated with James to define the internal module structure. By Friday, I refined the prototype based on his feedback and prepared documentation for our next steps.

        ---

        ### Example 2  
        INPUT:
        {
        "Monday":    "Conducted a kickoff meeting with Maria to align on project objectives.",
        "Tuesday":   "Drafted wireframes for the mobile app and shared them with the team.",
        "Wednesday": "Integrated the authentication API and resolved two critical bugs.",
        "Thursday":  "Held a design review session and incorporated UX improvements suggested by Maria.",
        "Friday":    "Deployed the first alpha build to the staging environment and wrote release notes."
        }

        OUTPUT:
        This week, I led a kickoff meeting with Maria to align on our goals, then drafted and circulated mobile app wireframes. Midweek, I integrated the authentication API and fixed two critical bugs, followed by a design review where I incorporated Maria's UX suggestions. Finally, I deployed the first alpha build to staging and authored the release notes.

        ---

        ### Now it's your turn  
        INPUT:
        """
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Prepare the few-shot prompt, injecting the JSON of entries
        week_entries ="\n".join(f"{day}: {text}" for day, text in request.entries.items() if text)
        print(week_entries)
        prompt = FEW_SHOT_PROMPT+week_entries + "Output:"
        # Call Gemini
        response = model.generate_content(prompt)
        summary = response.text.strip()
        print("--------------------------------")
        print(request.user_id)
        print(request.week_start)
        print(request.week_end)
        print(summary)
        # Save the weekly report in the DB
        try:
            supabase.table("weekly_reports").insert({
                "user_id": request.user_id,
                "week_start": request.week_start,
                "week_end": request.week_end,
                "sent_at": datetime.now().isoformat(),
                "summary": summary
            }).execute()
        except APIError as e:
            print("Failed to save weekly report:", e)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    return {"summary": summary}

@router.get("/weekly_reports/{user_id}")
def get_weekly_reports(user_id: str):
    """
    Fetch all weekly reports for a user, ordered by week_start descending.
    """
    try:
        result = supabase.table("weekly_reports").select("*").eq("user_id", user_id).order("week_start", desc=True).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result.data