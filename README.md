# Automatic Weekly Update Generator – Backend

This is the backend for the **Automatic Weekly Update Generator**: a professional, full-stack application that enables users to log daily work, receive reminders, and generate weekly summaries using Google Gemini LLM. The backend is built with FastAPI, uses Supabase for authentication and as a Postgres database, and integrates with Google Gemini for LLM-powered summaries.

## Features

- **User Authentication** (Supabase magic link)
- **User Management** (custom `users` table)
- **Daily Entry CRUD** (create, read, update, delete)
- **Weekly Report Generation** (Google Gemini LLM)
- **Weekly Report Storage** (`weekly_reports` table)
- **User Settings** (timezone, reminders, PDF/email options)
- **PDF/Email Delivery** (optional)
- **CORS Support** (for frontend integration)
- **Robust Error Handling**
- **Timezone-aware Timestamps (UTC)**

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- Supabase project (for auth and database)
- Google Gemini API key (for LLM integration)
- (Optional) Email service credentials (for report delivery)

### Installation

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd automatic_weekly_update/backend
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the backend root with the following (example):

   ```
   SUPABASE_URL=your-supabase-url
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   SUPABASE_ANON_KEY=your-supabase-anon-key
   GEMINI_API_KEY=your-gemini-api-key
   EMAIL_HOST=smtp.example.com
   EMAIL_PORT=587
   EMAIL_USER=your-email@example.com
   EMAIL_PASSWORD=your-email-password
   FRONTEND_ORIGIN=http://localhost:5173
   ```

5. **Run database migrations (if any):**

   - Ensure your Supabase tables (`users`, `daily_entries`, `weekly_reports`, etc.) are set up as per the schema.

6. **Start the FastAPI server:**

   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000).

## API Endpoints

- `POST /auth/signup` – Request magic link (Supabase)
- `GET /auth/me` – Get current user info (and insert into `users` table if new)
- `POST /entries` – Create daily entry
- `GET /entries` – List all daily entries for user
- `PUT /entries/{id}` – Update daily entry
- `DELETE /entries/{id}` – Delete daily entry
- `GET /weekly-report` – Generate weekly summary (Google Gemini LLM)
- `POST /weekly-report` – Save weekly report
- `GET /weekly-reports` – List all weekly reports for user
- `GET /settings` – Get user settings
- `PUT /settings` – Update user settings

> See the OpenAPI docs at `/docs` for full details and request/response schemas.

## Usage

1. **Authenticate:**  
   Use the `/auth/signup` endpoint to request a magic link. After login, use the access token for authenticated requests.

2. **Daily Logging:**  
   Use `/entries` endpoints to create, view, edit, and delete daily logs.

3. **Weekly Reports:**  
   Use `/weekly-report` to generate summaries (via Gemini LLM) and `/weekly-reports` to view all reports.

4. **Settings:**  
   Use `/settings` endpoints to manage user preferences.

## Integration

- **Frontend:**  
  The backend is designed to work seamlessly with the React frontend. Ensure CORS is configured to allow requests from your frontend origin.

- **Supabase:**  
  Used for both authentication and as the main Postgres database.

- **Google Gemini LLM:**  
  Used for generating professional weekly summaries.

## Deployment

- Use a production-ready ASGI server (e.g., Gunicorn with Uvicorn workers) for deployment.
- Set all environment variables securely in your deployment environment.
- Configure HTTPS and proper CORS settings for security.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

## License

[MIT](../LICENSE) (or your chosen license)

---

**Questions?**  
Open an issue or contact the maintainer.
