"""Ticket restriction data models and text cleanup helpers.

This module defines the dataclasses used to represent ticket restriction metadata
and helper utilities for cleaning HTML text blocks and normalizing empty states.
"""

import re
from dataclasses import dataclass
from html import unescape
from typing import List, Optional


@dataclass
class RestrictionDetail:
    """Detailed validity windows for outward and return journeys."""

    outwardRules: Optional[str] = None
    returnRules: Optional[str] = None


@dataclass
class RestrictionDirections:
    """Descriptive text indicating general travel validity directions."""

    outward: Optional[str] = None
    returnDir: Optional[str] = None


@dataclass
class TicketRestrictionData:
    """Complete ticket restriction record used for backend JSON export."""

    id: str
    code: str
    name: str
    link: str
    type: str  # Maps descriptive textual labels matching the restriction type integer code
    applicableDays: Optional[str] = None
    notes: Optional[str] = None
    easement: Optional[str] = None
    seasonalVariations: Optional[str] = None
    directions: Optional[RestrictionDirections] = None
    details: List[RestrictionDetail] = None


def parse_html_to_plain(text: Optional[str]) -> Optional[str]:
    """Clean HTML fragments into plain text and normalise empty values to None."""
    if not text:
        return None

    # Decode HTML entity characters (e.g. &nbsp;, &amp;)
    cleaned = unescape(text)
    
    # Strip away HTML tag strings safely
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    
    # Flatten trailing whitespace breaks down into single spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Convert structural fallback dashes or empty variants to a proper Null state
    if cleaned in ("", "-", "None", "Null"):
        return None

    return cleaned


def resolve_restriction_type(type_code: Optional[str]) -> str:
    """Convert a raw National Rail type number into a clear domain classification."""
    clean_code = (type_code or "").strip()
    if clean_code == "1":
        return "ARRIVALS"
    elif clean_code == "2":
        return "DEPARTURES"
    elif clean_code == "3":
        return "GENERAL"
    return "UNKNOWN"