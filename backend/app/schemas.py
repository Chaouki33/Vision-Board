from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .kpi.references import DOMAINS, SECTORS, SIZES

Role = Literal["owner", "editor", "viewer"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- Auth
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    is_admin: bool = False
    must_change_password: bool = False


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserOut(UserOut):
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    companies: list[dict] = []


class AdminUserIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    is_admin: bool = False
    # Accès aux sociétés : [{"company_id": 1, "role": "editor"}]
    companies: list[dict] = []
    # Mot de passe provisoire choisi par l'admin ; généré automatiquement si absent.
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_admin: bool | None = None
    is_active: bool | None = None


class AdminUserCreated(BaseModel):
    user: AdminUserOut
    temporary_password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------- Sociétés
class CompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sector: str
    size: str | None = None  # déduite de l'effectif ou du CA si absente
    employees: int | None = Field(default=None, ge=0)
    annual_revenue: float | None = Field(default=None, ge=0)
    city: str | None = Field(default=None, max_length=120)
    # À la création : tableaux de bord à préparer d'emblée (ex. ["commercial", "rh"]).
    domains: list[str] = []

    @field_validator("domains")
    @classmethod
    def check_domains(cls, v: list[str]) -> list[str]:
        unknown = [d for d in v if d not in DOMAINS]
        if unknown:
            raise ValueError(f"Type de tableau de bord inconnu : {', '.join(unknown)}")
        return v

    @field_validator("sector")
    @classmethod
    def check_sector(cls, v: str) -> str:
        if v not in SECTORS:
            raise ValueError("Secteur inconnu")
        return v

    @field_validator("size")
    @classmethod
    def check_size(cls, v: str | None) -> str | None:
        if v is not None and v not in SIZES:
            raise ValueError("Taille inconnue")
        return v


class CompanyOut(ORM):
    id: int
    name: str
    sector: str
    size: str
    employees: int | None
    annual_revenue: float | None
    city: str | None
    created_at: datetime
    role: Role | None = None


class MemberIn(BaseModel):
    email: EmailStr
    role: Role = "viewer"


class MemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: Role


# ---------------------------------------------------------------- Données importées
class DatasetOut(ORM):
    id: int
    domain: str
    name: str
    source_filename: str
    file_type: str
    row_count: int
    columns: list[str]
    mapping: dict[str, str]
    created_at: datetime


class DatasetDetail(DatasetOut):
    preview: list[dict]
    sheets: list[str] = []


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    mapping: dict[str, str] | None = None


# ---------------------------------------------------------------- KPI et tableaux de bord
class KpiOut(BaseModel):
    code: str
    domain: str
    name: str
    description: str
    formula: str
    unit: str
    required: list[str]
    priority: int
    higher_is_better: bool | None
    warning: float | None
    critical: float | None


class RecommendationOut(KpiOut):
    available: bool
    missing_fields: list[str]
    dataset_id: int | None
    selected: bool
    reasons: list[str]


class RecommendationsOut(BaseModel):
    domain: str
    sector: str
    size: str
    suggested_domains: list[str]
    datasets: int
    kpis: list[RecommendationOut]


class DashboardIn(BaseModel):
    domain: str
    title: str = Field(min_length=1, max_length=255)
    kpi_codes: list[str] = Field(min_length=1)

    @field_validator("domain")
    @classmethod
    def check_domain(cls, v: str) -> str:
        if v not in DOMAINS:
            raise ValueError("Domaine inconnu")
        return v


class ChartOut(BaseModel):
    type: str
    title: str
    labels: list[str]
    values: list[float]
    unit: str


class KpiValueOut(BaseModel):
    code: str
    name: str
    description: str
    formula: str
    unit: str
    higher_is_better: bool | None
    value: float | None
    status: str | None
    detail: str | None
    delta: float | None
    chart: ChartOut | None
    error: str | None
    rows: int


class DashboardDataOut(BaseModel):
    id: int
    title: str
    domain: str
    start: date | None
    end: date | None
    data_start: date | None
    data_end: date | None
    kpis: list[KpiValueOut]


class DashboardBulkIn(BaseModel):
    domains: list[str] = Field(min_length=1)

    @field_validator("domains")
    @classmethod
    def check_domains(cls, v: list[str]) -> list[str]:
        unknown = [d for d in v if d not in DOMAINS]
        if unknown:
            raise ValueError(f"Type de tableau de bord inconnu : {', '.join(unknown)}")
        return v


class DashboardOut(ORM):
    id: int
    domain: str
    title: str
    kpi_codes: list[str]
    created_at: datetime
    updated_at: datetime
