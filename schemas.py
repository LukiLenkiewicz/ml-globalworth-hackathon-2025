from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import List, Optional

class OfficeInquiry(BaseModel):
    # Część I – Informacje o najmie i lokalizacji
    preferred_district_or_area: str = Field(..., description="Preferowana dzielnica, okolica lub konkretna ulica")
    preferred_floor: str = Field(..., description="Preferowane piętro (np. parter, wysokie piętro, dowolne)")
    office_area_m2: int = Field(..., gt=0, description="Wymagana powierzchnia biura w m²")
    number_of_employees: int = Field(..., gt=0, description="Liczba pracowników/stanowisk pracy")
    office_type: str = Field(..., description="Rodzaj przestrzeni (np. Biuro prywatne, Open space, Coworking, Inne)")
    rental_period_start: date = Field(..., description="Data rozpoczęcia najmu (format RRRR-MM-DD)")
    rental_period_end: Optional[date] = Field(None, description="Data zakończenia najmu, jeśli dotyczy")
    rental_period_unlimited: bool = Field(..., description="Czy najem ma być na czas nieokreślony (true/false)")
    access_hours: str = Field(..., description="Godziny dostępu (np. 24/7, w godzinach pracy, inne)")
    monthly_budget_net_PLN: float = Field(..., gt=0, description="Miesięczny budżet netto w PLN")