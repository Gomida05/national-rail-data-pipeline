"""Ticket data models and text cleanup helpers.

This module defines the dataclasses used to represent ticket metadata and
helper utilities for cleaning HTML and resolving transport operator names.
"""

import re
from dataclasses import dataclass
from html import unescape
from typing import List, Optional


@dataclass
class TicketValidity:
    """Structured validity information for a ticket."""

    dayOutward: Optional[str] = None
    dayReturn: Optional[str] = None
    timeOutward: Optional[str] = None
    timeReturn: Optional[str] = None
    outwardNote: Optional[str] = None
    returnNote: Optional[str] = None


@dataclass
class RestrictionInfo:
    """Ticket restriction metadata, such as railcard or group travel rules."""

    permitted: Optional[bool] = None
    note: Optional[str] = None


@dataclass
class TicketRules:
    """Structured ticket rule sections pulled from the feed."""

    conditions: Optional[str] = None
    availability: Optional[str] = None
    retailing: Optional[str] = None
    bookingDeadlines: Optional[str] = None
    refunds: Optional[str] = None
    discounts: Optional[str] = None
    specialConditions: Optional[str] = None
    breakOfJourney: Optional[str] = None
    compulsoryReservations: Optional[str] = None
    changesToTravelPlans: Optional[str] = None


@dataclass
class TicketsData:
    """Complete ticket record used for JSON export."""

    id: str
    code: str
    name: str
    description: Optional[str]
    classType: Optional[str]
    returnType: Optional[str]
    fareCategory: Optional[str]
    validity: Optional[TicketValidity]
    railcard: Optional[RestrictionInfo]
    groupTravel: Optional[RestrictionInfo]
    rules: Optional[TicketRules]
    includedTocs: List[str]


class TOCCodeResolver:
    """Resolve Transport Operator Company codes into readable names."""

    TOC_CODE_MAP = {
        "AW": "Transport for Wales (AW)",
        "CC": "City to Coast (CC)",
        "CH": "Chiltern Railways (CH)",
        "CS": "Caledonian Sleeper (CS)",
        "EM": "East Midlands Railway (EM)",
        "ES": "Eurostar (ES)",
        "GC": "Grand Central (GC)",
        "GN": "Great Northern (GN)",
        "GR": "LNER (GR)",
        "GW": "Great Western Railway (GW)",
        "GX": "Gatwick Express (GX)",
        "HC": "Heathrow Connect (HC)",
        "HT": "Hull Trains (HT)",
        "HX": "Heathrow Express (HX)",
        "IL": "Island Line (IL)",
        "LE": "Greater Anglia (LE)",
        "LM": "London Northwestern Railway (LM)",
        "LO": "London Overground (LO)",
        "LT": "TfL Rail (LT)",
        "ME": "Merseyrail (ME)",
        "NT": "Northern Trains (NT)",
        "SC": "ScotRail (SC)",
        "SE": "Southeastern (SE)",
        "SN": "Southern (SN)",
        "SR": "SWR (SR)",
        "SX": "Stansted Express (SX)",
        "TP": "TransPennine Express (TP)",
        "TL": "Thameslink (TL)",
        "VT": "Avanti West Coast (VT)",
        "XC": "CrossCountry (XC)",
    }

    def resolve(self, code: str) -> str:
        """Return a readable operator name for a TOC code."""

        return self.TOC_CODE_MAP.get(code, code)

    def resolve_all(self, codes: List[str]) -> List[str]:
        """Resolve a list of TOC codes into readable names."""

        return [self.resolve(code) for code in codes if code.strip()]


def parse_html_to_plain(text: Optional[str]) -> Optional[str]:
    """Clean HTML fragments into plain text and normalise empty values."""

    if not text:
        return None

    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned == "" or cleaned == "-":
        return None

    return cleaned


def parse_toc_names(codes: List[str], resolver: TOCCodeResolver | None = None) -> List[str]:
    """Resolve TOC codes into display names for a ticket."""

    resolver = resolver or TOCCodeResolver()
    return resolver.resolve_all(codes)
