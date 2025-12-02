from pydantic import BaseModel, EmailStr, SecretStr, Field


class LoginRequest(BaseModel):

    username: str
    password: SecretStr


class LoginResponse(BaseModel):

    username: str
    message: str = "Authenticated"
    chat_data: dict | None = None


class EmailVerificationRequest(BaseModel):

    username: str
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)


class EmailVerificationResponse(BaseModel):

    message: str


class EmailVerificationConfirmRequest(BaseModel):

    username: str
    code: str


class EmailVerificationConfirmResponse(BaseModel):

    message: str
    chat_data: dict | None = None
