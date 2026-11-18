"""Pydantic validators and structural parsers for IFSC, CIN, and GSTIN."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field, field_validator

IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
CIN_RE = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")
GSTIN_RE = re.compile(
    r"^([0-3][0-9])([A-Z]{5}[0-9]{4}[A-Z])([1-9A-Z])(Z)([0-9A-Z])$"
)

GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def compute_gstin_checksum(gstin_14: str) -> str:
    """Compute the 15th check digit for a 14-character GSTIN prefix using mod-36 Luhn-like weights."""
    if len(gstin_14) != 14:
        raise ValueError(f"Expected 14 chars for GSTIN prefix, got {len(gstin_14)}")
    factor = 2
    total = 0
    mod = len(GSTIN_CHARSET)
    for ch in reversed(gstin_14.upper()):
        code_point = GSTIN_CHARSET.index(ch)
        addend = factor * code_point
        factor = 1 if factor == 2 else 2
        addend = (addend // mod) + (addend % mod)
        total += addend
    check_code_point = (mod - (total % mod)) % mod
    return GSTIN_CHARSET[check_code_point]


def validate_gstin_checksum(gstin: str) -> bool:
    """Verify both regex structure and mod-36 check digit of a 15-char GSTIN."""
    g = gstin.strip().upper()
    if not GSTIN_RE.match(g):
        return False
    return compute_gstin_checksum(g[:14]) == g[14]


@dataclass(frozen=True)
class ParsedGSTIN:
    gstin: str
    state_code: str
    pan_segment: str
    entity_number: str
    checksum_char: str
    checksum_valid: bool


def parse_gstin(gstin: str) -> ParsedGSTIN:
    """Parse a 15-character GSTIN into its structural components."""
    g = gstin.strip().upper()
    m = GSTIN_RE.match(g)
    if not m:
        raise ValueError(f"Invalid GSTIN structure: {gstin!r}")
    return ParsedGSTIN(
        gstin=g,
        state_code=m.group(1),
        pan_segment=m.group(2),
        entity_number=m.group(3),
        checksum_char=m.group(5),
        checksum_valid=(compute_gstin_checksum(g[:14]) == m.group(5)),
    )


@dataclass(frozen=True)
class ParsedCIN:
    cin: str
    listing_status: str
    industry_code: str
    state_code: str
    incorporation_year: int
    ownership_type: str
    registration_number: str


def parse_cin(cin: str) -> ParsedCIN:
    """Parse a 21-character MCA Corporate Identification Number (CIN)."""
    c = cin.strip().upper()
    m = CIN_RE.match(c)
    if not m:
        raise ValueError(f"Invalid CIN structure: {cin!r}")
    return ParsedCIN(
        cin=c,
        listing_status=m.group(1),
        industry_code=m.group(2),
        state_code=m.group(3),
        incorporation_year=int(m.group(4)),
        ownership_type=m.group(5),
        registration_number=m.group(6),
    )


class IfscBranchRecord(BaseModel):
    ifsc: str
    bank_code: str
    bank_name: Optional[str] = None
    branch_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state_name: Optional[str] = None
    pincode: Optional[str] = Field(default=None, pattern=r"^\d{6}$")
    micr: Optional[str] = None
    neft: bool = False
    rtgs: bool = False
    imps: bool = False
    upi: bool = False

    @field_validator("ifsc")
    @classmethod
    def check_ifsc(cls, v: str) -> str:
        val = v.strip().upper()
        if not IFSC_RE.match(val):
            raise ValueError(f"Invalid IFSC format: {v!r}")
        return val


class McaCompanyRecord(BaseModel):
    cin: str
    company_name: str
    company_status: str
    listing_status: str
    industry_code: str
    state_code: str
    incorporation_year: int
    ownership_type: str
    registration_number: str
    roc_code: Optional[str] = None
    company_category: Optional[str] = None
    company_class: Optional[str] = None
    authorized_capital: Optional[float] = None
    paidup_capital: Optional[float] = None
    registration_date: Optional[str] = None
    registered_address: Optional[str] = None
    pincode: Optional[str] = Field(default=None, pattern=r"^\d{6}$")

    @field_validator("cin")
    @classmethod
    def check_cin(cls, v: str) -> str:
        val = v.strip().upper()
        if not CIN_RE.match(val):
            raise ValueError(f"Invalid CIN format: {v!r}")
        return val
