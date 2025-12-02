# Revit Key Backend

FastAPI backend for managing license keys and admin authentication with OTP password reset.

## Setup

1. Create and activate a Python 3.11+ environment.
2. Install dependencies:

```cmd
pip install -r backend/requirements.txt
```

3. Configure environment (optional):

```cmd
copy backend\.env.example backend\.env
```

Edit `.env` to set SMTP credentials for email OTP. Leave empty for dev mode (OTP printed to console).

4. Run the server (Windows cmd):

```cmd
cd backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Default DB: SQLite file `backend/revit_keys.db`. Override via `DATABASE_URL` env.
- Default admin: `username=admin`, `password=@Abc12324`, `email=admin@example.com`.

## API Endpoints

### Authentication
- **POST** `/auth/login` → JWT token
  - Body: `{"username": "admin", "password": "@Abc12324"}`
  - Response: `{"access_token": "...", "token_type": "bearer"}`
  
- **POST** `/auth/request-reset` → Request password reset (sends OTP to email)
  - Body: `{"email": "admin@example.com", "new_password": "NewPass123", "confirm_password": "NewPass123"}`
  - Response: `{"message": "OTP sent to email", "expires_in_minutes": 10}`
  - Note: In dev mode (no SMTP), OTP is printed to server console
  
- **POST** `/auth/verify-reset` → Verify OTP and apply new password
  - Body: `{"email": "admin@example.com", "otp_code": "123456"}`
  - Response: `{"message": "Password reset successful"}`

### Key Management (Admin only)
- **POST** `/keys/create` → create key
  - Headers: `Authorization: Bearer <token>`
  - Body: `{"type": "trial|month|year|lifetime", "note": "optional"}`
  
- **GET** `/keys/list` → list all keys
- **GET** `/keys/{key_value}` → get key details
- **PUT** `/keys/{key_value}` → update key (lock/unlock, edit note)
  - Body: `{"is_active": true, "note": "updated note"}`
  
- **DELETE** `/keys/{key_value}` → delete key

### Revit Validation
- **POST** `/keys/validate` → validate key from Revit (no auth required)
  - Body: `{"key_value": "...", "machine_name": "...", "os_version": "...", "revit_version": "...", "cpu_info": "...", "ip_address": "...", "machine_hash": "..."}`

## Password Reset Flow

1. User calls **POST** `/auth/request-reset` with email and new password (twice for confirmation)
2. System validates email exists, password strength, generates 6-digit OTP, sends to email (or prints to console in dev mode)
3. User receives OTP via email
4. User calls **POST** `/auth/verify-reset` with email and OTP code
5. System verifies OTP (not used, not expired), applies new password, marks OTP as used

## Testing

Validate implementation:
```cmd
python validate_implementation.py
```

Test password reset (interactive):
```cmd
python test_reset_password.py
```

Test all endpoints:
```cmd
python tests_smoke.py
```

## Notes

- Key types: `trial` (7 days), `month` (30 days), `year` (365 days), `lifetime` (no expiry).
- Admin-only routes require `Authorization: Bearer <token>` from `/auth/login`.
- OTP expires in 10 minutes (configurable via `OTP_EXPIRE_MINUTES` env).
- In dev mode (no SMTP credentials), OTP is printed to server console.
- Password requirements: minimum 8 characters (configurable in code).
