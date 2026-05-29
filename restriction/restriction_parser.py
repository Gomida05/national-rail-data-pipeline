"""Ticket restriction parsing and download workflow for National Rail feeds.

This module contains the streaming parser orchestration and disk writing handlers
used to download the live XML payload, convert nested tags into structured models,
and save the unified, clean JSON output.
"""

import json
from dataclasses import asdict
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from main import TOKEN
from typing import List

from restriction_models import (
    RestrictionDetail,
    RestrictionDirections,
    TicketRestrictionData,
    parse_html_to_plain,
    resolve_restriction_type,
)


class TicketRestrictionParser:
    """Parse, transform, and persist structural National Rail restriction payloads."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize parser operational paths.

        Args:
            base_dir: Optional project root. Defaults to the parent folder of this execution path.
        """
        project_root = Path(__file__).resolve().parents[1] if base_dir is None else Path(base_dir)
        self.data_dir = project_root / "data"
        self.xml_path = self.data_dir / "ticket_restrictions.xml"
        self.json_path = self.data_dir / "ticket_restrictions.json"

    def build_restriction(self, current, current_details):
        """Assemble structured data components into a validated model layout."""
        return TicketRestrictionData(
            id=current.get("id", "").strip(),
            code=current.get("code", "").strip(),
            name=parse_html_to_plain(current.get("name")),
            link=current.get("link", "").strip(),
            type=resolve_restriction_type(current.get("type")),
            applicableDays=parse_html_to_plain(current.get("applicableDays")),
            notes=parse_html_to_plain(current.get("notes")),
            easement=parse_html_to_plain(current.get("easement")),
            seasonalVariations=parse_html_to_plain(current.get("seasonalVariations")),
            directions=RestrictionDirections(
                outward=parse_html_to_plain(current.get("outwardDirection")),
                returnDir=parse_html_to_plain(current.get("returnDirection"))
            ),
            details=current_details
        )

    def parse_restrictions(self, xml_file_path: str | Path) -> List[TicketRestrictionData]:
        """Parse the nested XML feed iteratively into domain-mapped models."""
        restrictions = []
        
        # State tracking references
        current = {}
        current_details = []
        
        # Temporary nested buffers
        detail_outward = None
        detail_return = None

        # Stream parse to stay efficient
        for event, elem in ET.iterparse(str(xml_file_path), events=("start", "end")):
            # Clean namespace headers out from the tag selector string
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if event == "end":
                text = (elem.text or "").strip()

                if tag == "TicketRestrictionIdentifier":
                    # If we encounter a new restriction block while another is active, commit it
                    if current.get("id"):
                        restrictions.append(self.build_restriction(current, current_details))
                        current, current_details = {}, []
                    current["id"] = text

                elif tag == "RestrictionCode":
                    current["code"] = text
                elif tag == "Name":
                    current["name"] = text
                elif tag == "LinkToDetailPage":
                    current["link"] = text
                elif tag == "ApplicableDays":
                    current["applicableDays"] = text
                elif tag == "Notes":
                    current["notes"] = text
                elif tag == "Easement":
                    current["easement"] = text
                elif tag == "SeasonalVariations":
                    current["seasonalVariations"] = text
                elif tag == "OutwardDirection":
                    current["outwardDirection"] = text
                elif tag == "ReturnDirection":
                    current["returnDirection"] = text
                elif tag == "RestrictionsType":
                    current["type"] = text
                
                # Capture child collection structures
                elif tag == "DetailsOutward":
                    detail_outward = text
                elif tag == "DetailsReturn":
                    detail_return = text
                elif tag == "Restriction":
                    # Build and add the sub-rule element onto the restriction data details array
                    current_details.append(
                        RestrictionDetail(
                            outwardRules=parse_html_to_plain(detail_outward),
                            returnRules=parse_html_to_plain(detail_return)
                        )
                    )
                    # Clear nested rule buffer states
                    detail_outward, detail_return = None, None

                elif tag == "TicketRestriction":
                    # End of the parent block: append the finalized model
                    if current.get("id"):
                        restrictions.append(self.build_restriction(current, current_details))
                        current, current_details = {}, []

                elem.clear()  # Free memory allocation chunks references instantly

        return restrictions

    def save_to_json(self, restrictions, path: str | Path | None = None):
        """Serialize data object graphs out into a structured JSON file."""
        target_path = Path(path) if path is not None else self.json_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(r) for r in restrictions], handle, indent=2, ensure_ascii=False)

    def download_and_parse(self, url: str, token: str, xml_path: str | Path | None = None, json_path: str | Path | None = None):
        """Execute stream ingestion, cleanup execution and write properties."""
        download_path = Path(xml_path) if xml_path is not None else self.xml_path
        output_path = Path(json_path) if json_path is not None else self.json_path

        download_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = {"X-Auth-Token": token, "Accept": "application/xml"}
        with requests.get(url, headers=headers, stream=True) as response:
            response.raise_for_status()
            with download_path.open("wb") as handle:
                for chunk in response.iter_content(8192):
                    handle.write(chunk)

        parsed_data = self.parse_restrictions(download_path)
        print(f"Successfully processed and cleaned {len(parsed_data)} restriction records.")
        self.save_to_json(parsed_data, output_path)
        return parsed_data


def main():
    """Execute the restriction transformation workflow loop sequence."""
    parser = TicketRestrictionParser()
    parser.download_and_parse(
        url="https://opendata.nationalrail.co.uk/api/staticfeeds/4.0/ticket-restrictions",
        token=TOKEN,
        xml_path=parser.xml_path,
        json_path=parser.json_path,
    )


if __name__ == "__main__":
    main()