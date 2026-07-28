# schemas.py - Legal document schemas
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

from pydantic import BaseModel, Field
from typing import Optional, List

class CreditAgreement(BaseModel):
    lender: str = Field(description="Name of the lender")
    borrower: str = Field(description="Name of the borrower")
    loan_amount: float = Field(description="Principal amount")
    interest_rate: float = Field(description="Annual interest rate in percentage")
    term_months: int = Field(description="Loan term in months")
    collateral: Optional[str] = Field(description="Collateral description")
    default_penalty: Optional[float] = Field(description="Penalty rate after default")
    governing_law: str = Field(description="Governing jurisdiction")

class ContractClause(BaseModel):
    clause_title: str = Field(description="Title of the clause")
    clause_text: str = Field(description="Full text of the clause")
    parties_involved: List[str] = Field(description="Parties affected by this clause")
    obligations: List[str] = Field(description="Obligations imposed")
    penalties: List[str] = Field(description="Penalties for breach")