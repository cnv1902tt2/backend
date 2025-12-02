from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RequestResetRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class VerifyResetRequest(BaseModel):
    email: EmailStr
    otp_code: str
