# Hireblaze API

AI-powered job application assistant backend API.

## Authentication

### Password Requirements

- **Minimum length**: 8 characters
- **Maximum length**: 72 bytes (UTF-8 encoded)
- **Validation**: Enforced server-side for security
- **Rate limiting**: 10 requests per minute per IP for login and signup

#### Bcrypt 72-Byte Limit

The API uses bcrypt for password hashing, which has a hard limit of 72 bytes for the input password. This limit applies to the UTF-8 encoded byte length, not the character count.

**Examples:**
- ASCII characters: 72 characters = 72 bytes (limit reached)
- Unicode characters (emojis, etc.): May be 2-4 bytes per character
- Example: 18 emoji characters = 72 bytes (limit reached)

Password validation is enforced server-side to ensure passwords never exceed this limit before hashing. If a password exceeds 72 bytes, the API returns HTTP 400 with a clear error message: "Password is too long or invalid".

## Development

### Setup

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
uvicorn app.main:app --reload
```

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host/dbname  # or sqlite:///./app.db for local dev
SECRET_KEY=your-secret-key-here

# Optional (for AI features)
OPENAI_API_KEY=sk-...  # Required for AI endpoints (/ai/*)

# Stripe (for billing)
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLIC_KEY=pk_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Database Migrations

The API uses Alembic for database migrations. Migrations run automatically on startup (idempotent).

To manually run migrations:
```bash
alembic upgrade head
```

To create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

### Dependencies

- FastAPI
- SQLAlchemy
- Alembic (database migrations)
- bcrypt 4.0.1 (pinned for production stability)
- passlib 1.7.4 (pinned for bcrypt compatibility)
- openai (for AI features)

## API Endpoints

### AI Endpoints (require OPENAI_API_KEY)

#### POST /ai/job-match
Analyze match between resume and job description.

**Request:**
```json
{
  "resume_id": 1,
  "job_id": 2
}
// OR
{
  "resume_text": "...",
  "jd_text": "..."
}
```

**Response:** Match score (0-100), overlap, missing skills, risks, improvement plan, recruiter lens.
Automatically persists to `MatchAnalysis` table.

#### POST /ai/recruiter-lens
Generate recruiter perspective analysis.

**Response:** First impression, red flags, strengths, shortlist decision, fixes.
Optionally save to Drive with `save_to_drive: true`.

#### POST /ai/interview-pack
Generate interview preparation pack.

**Response:** 10 questions, STAR outlines, 30/60/90 day plan.
Automatically persists to `InterviewPack` table and optionally saves to Drive.

#### POST /ai/outreach
Generate outreach messages.

**Request:**
```json
{
  "message_type": "recruiter_followup",  // or "linkedin_dm", "thank_you", "referral_ask"
  "resume_id": 1,
  "job_id": 2,
  "save_to_drive": false
}
```

**Response:** Generated message, subject line, tone.
Automatically persists to `OutreachMessage` table.

### Job Auto-Tracking Endpoints

#### POST /jobs/import-url
Import a job posting by URL.

**Request:**
```json
{
  "source_url": "https://jobs.example.com/123",
  "company": "Example Corp",  // optional, auto-detected
  "title": "Software Engineer",  // optional
  "location": "San Francisco"  // optional
}
```

Creates a `JobPosting` entry with placeholder JD text.

#### POST /jobs/{id}/parse-jd
Parse job description from the job posting's source URL.

Updates the `jd_text` field using existing JD parsing logic or AI.

#### GET /jobs/{id}/insights
Get comprehensive insights for a job posting.

**Response:** Match analysis, recruiter lens, outreach suggestions, interview pack availability.

## Error Handling

### AI Endpoints

- **501 Not Implemented**: Returned if `OPENAI_API_KEY` is not configured
- **502 Bad Gateway**: Returned if AI service is temporarily unavailable or returns errors
- **400 Bad Request**: Invalid request parameters

All AI endpoints return validated JSON responses (Pydantic models) and never log user content.

### Rate Limiting

- Login and signup endpoints: **10 requests per minute per IP**
- Returns **429 Too Many Requests** if exceeded
