from pydantic import BaseModel, EmailStr, SecretStr, Field


class LoginRequest(BaseModel):

    email: EmailStr
    password: SecretStr


class LoginResponse(BaseModel):

    nickname: str
    email: EmailStr
    message: str = "Authenticated"
    chat_data: dict | None = None


class EmailVerificationRequest(BaseModel):

    nickname: str
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)


class EmailVerificationResponse(BaseModel):

    message: str


class EmailVerificationConfirmRequest(BaseModel):

    nickname: str
    code: str


class EmailVerificationConfirmResponse(BaseModel):

    message: str
    chat_data: dict | None = None
