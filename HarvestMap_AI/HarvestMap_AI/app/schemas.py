from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

BusinessCategory = Literal["farm", "shop", "market", "service"]
ProductCategory = Literal["vegetables", "fruit", "dairy", "grain", "honey", "meat"]


class Register(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)
    role: Literal["user", "owner"] = "user"


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class AccountUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class LocationIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class BusinessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=150)
    category: BusinessCategory
    description: str = Field(min_length=10, max_length=6000)
    location_id: int = Field(gt=0)
    address: str = Field(min_length=3, max_length=250)
    phone: str = Field(default="", max_length=40)
    website: str = Field(default="", max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("website")
    @classmethod
    def safe_url(cls, v):
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("Сілтеме http:// немесе https:// арқылы басталуы керек")
        return v


class ProductIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=150)
    category: ProductCategory
    description: str = Field(min_length=10, max_length=6000)
    price: float = Field(gt=0, le=1_000_000_000, allow_inf_nan=False, multiple_of=0.01)
    unit: Literal["кг", "л", "дана", "қап"] = "кг"
    stock: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False, multiple_of=0.01)
    season_start: int = Field(ge=1, le=12)
    season_end: int = Field(ge=1, le=12)


class Moderation(BaseModel):
    status: Literal["approved", "rejected", "pending"]


class RoleChange(BaseModel):
    role: Literal["user", "owner", "admin"]
    is_active: bool = True


class AssistantIn(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
