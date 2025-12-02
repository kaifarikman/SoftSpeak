from pydantic import BaseModel


class AdminLoginRequest(BaseModel):

    username: str
    password: str


class AdminLoginResponse(BaseModel):

    message: str
    token: str


class QuestionCreateRequest(BaseModel):

    category_id: int
    text: str
    order: int = 0
    is_active: bool = True


class QuestionUpdateRequest(BaseModel):

    text: str | None = None
    order: int | None = None
    is_active: bool | None = None


class CategoryCreateRequest(BaseModel):

    name: str
    description: str | None = None
    order: int = 0


class RandomWordSchema(BaseModel):

    id: int
    text: str
    is_active: bool

    class Config:
        from_attributes = True


class RandomWordCreateRequest(BaseModel):

    text: str


class RandomWordUpdateRequest(BaseModel):

    text: str | None = None
    is_active: bool | None = None

