# Hireblaze API

AI-powered job application assistant backend API.

## Authentication

### Password Requirements

- **Minimum length**: 6 characters
- **Maximum length**: 72 bytes (UTF-8 encoded)
- **Validation**: Enforced server-side for security

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

### Dependencies

- FastAPI
- SQLAlchemy
- bcrypt 4.0.1 (pinned for production stability)
- passlib 1.7.4 (pinned for bcrypt compatibility)
