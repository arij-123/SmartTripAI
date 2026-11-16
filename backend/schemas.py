from typing import Literal

from pydantic import BaseModel, ConfigDict, Field , EmailStr, SecretStr, field_validator
from datetime import datetime

Interest = Literal[
    "culture",
    "nature",
    "adventure",
    "gastronomy",
    "nightlife",
]


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget_total: float = Field(
        gt=0,
        le=9999999999.99,
        allow_inf_nan=False,
    )
    jours: int = Field(gt=0, le=365)
    mois: int = Field(ge=1, le=12)
    climat: Literal["chaud", "doux", "froid"]
    interets: list[Interest] = Field(min_length=1, max_length=5)


class UserSignup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: SecretStr = Field(min_length=5, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Ce champ ne doit pas être vide.")

        return value


class UserPublic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    created_at: datetime


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int