"""Ticket parsing and download workflow for National Rail ticket types.

This module contains the parser orchestration and file handling used to
fetch the XML feed, turn it into structured ticket objects, and write the
resulting JSON file.
"""

import json
from dataclasses import asdict
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from type.ticket_models import (
    RestrictionInfo,
    TicketRules,
    TicketValidity,
    TicketsData,
    TOCCodeResolver,
    parse_html_to_plain,
)


class TicketParser:
    """Parse, transform, and persist National Rail ticket type feeds."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize parser paths.

        Args:
            base_dir: Optional project root. Defaults to the parent of this file.
        """

        project_root = Path(__file__).resolve().parents[1] if base_dir is None else Path(base_dir)
        self.data_dir = project_root / "data"
        self.xml_path = self.data_dir / "tickets.xml"
        self.json_path = self.data_dir / "tickets.json"
        self.toc_resolver = TOCCodeResolver()

    def map_validity(self, data):
        """Convert validity XML fields into the structured payload shape."""

        return {
            "dayOutward": parse_html_to_plain(data.get("DayOutward")),
            "dayReturn": parse_html_to_plain(data.get("DayReturn")),
            "timeOutward": parse_html_to_plain(data.get("TimeOutward")),
            "timeReturn": parse_html_to_plain(data.get("TimeReturn")),
            "outwardNote": parse_html_to_plain(data.get("OutwardNote")),
            "returnNote": parse_html_to_plain(data.get("ReturnNote")),
        }

    def map_rules(self, data):
        """Convert rule XML fields into the structured payload shape."""

        return {
            "conditions": parse_html_to_plain(data.get("conditions")),
            "availability": parse_html_to_plain(data.get("availability")),
            "retailing": parse_html_to_plain(data.get("retailing")),
            "bookingDeadlines": parse_html_to_plain(data.get("bookingdeadlines")),
            "refunds": parse_html_to_plain(data.get("refunds")),
            "discounts": parse_html_to_plain(data.get("discount")),
            "specialConditions": parse_html_to_plain(data.get("specialconditions")),
            "breakOfJourney": parse_html_to_plain(data.get("breakofjourney")),
            "compulsoryReservations": parse_html_to_plain(data.get("compulsoryreservations")),
            "changesToTravelPlans": parse_html_to_plain(data.get("changestotravelplans")),
        }

    def build_ticket(self, current, validity, railcard, group, rules, tocs):
        """Create a structured ticket record from parsed XML fragments."""

        return TicketsData(
            id=current.get("id", ""),
            code=current.get("code", ""),
            name=current.get("name", ""),
            description=parse_html_to_plain(current.get("description")),
            classType=parse_html_to_plain(current.get("class_type")),
            returnType=parse_html_to_plain(current.get("return_type")),
            fareCategory=parse_html_to_plain(current.get("fare_category")),
            validity=TicketValidity(**self.map_validity(validity)) if validity else None,
            railcard=RestrictionInfo(
                permitted=railcard.get("permitted"),
                note=parse_html_to_plain(railcard.get("note")),
            ) if railcard else None,
            groupTravel=RestrictionInfo(
                permitted=group.get("permitted"),
                note=parse_html_to_plain(group.get("note")),
            ) if group else None,
            rules=TicketRules(**self.map_rules(rules)) if rules else None,
            includedTocs=self.toc_resolver.resolve_all(tocs),
        )

    def parse_tickets(self, xml_file_path: str | Path):
        """Parse the XML feed into a list of ticket objects."""

        tickets = []
        current = {}
        current_tocs = []
        validity = {}
        railcard = {}
        group = {}
        rules = {}
        current_section = "NONE"

        for event, elem in ET.iterparse(str(xml_file_path), events=("start", "end")):
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if event == "start":
                if tag == "Validity":
                    current_section = "VALIDITY"
                elif tag == "RailCard":
                    current_section = "RAILCARD"
                elif tag == "Group":
                    current_section = "GROUP"

            elif event == "end":
                text = (elem.text or "").strip()

                if tag == "TicketTypeIdentifier":
                    if current.get("id"):
                        tickets.append(self.build_ticket(current, validity, railcard, group, rules, current_tocs))
                        current, current_tocs, validity, railcard, group, rules = {}, [], {}, {}, {}, {}
                    current["id"] = text

                elif tag == "TicketTypeCode":
                    current["code"] = text
                elif tag == "TicketTypeName":
                    current["name"] = text
                elif tag == "Description":
                    current["description"] = text
                elif tag == "Class":
                    current["class_type"] = text
                elif tag == "SingleReturn":
                    current["return_type"] = text
                elif tag == "FareCategory":
                    current["fare_category"] = text
                elif tag == "TocRef":
                    current_tocs.append(text)
                elif current_section == "VALIDITY":
                    validity[tag] = text
                elif tag == "Permitted":
                    if current_section == "RAILCARD":
                        railcard["permitted"] = text.lower() == "true"
                    elif current_section == "GROUP":
                        group["permitted"] = text.lower() == "true"
                elif tag == "Note":
                    if current_section == "RAILCARD":
                        railcard["note"] = text
                    elif current_section == "GROUP":
                        group["note"] = text
                elif tag in {
                    "Conditions",
                    "Availability",
                    "Retailing",
                    "BookingDeadlines",
                    "Refunds",
                    "Discount",
                    "SpecialConditions",
                    "BreakOfJourney",
                    "CompulsoryReservations",
                    "ChangesToTravelPlans",
                }:
                    rules[tag.lower()] = text

                if tag in {"Validity", "RailCard", "Group"}:
                    current_section = "NONE"

                elem.clear()

        if current.get("id"):
            tickets.append(self.build_ticket(current, validity, railcard, group, rules, current_tocs))

        return tickets

    def save_to_json(self, tickets, path: str | Path | None = None):
        """Serialize ticket objects to a JSON file."""

        target_path = Path(path) if path is not None else self.json_path
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(ticket) for ticket in tickets], handle, indent=2, ensure_ascii=False)

    def download_and_parse(self, url: str, token: str, xml_path: str | Path | None = None, json_path: str | Path | None = None):
        """Download the XML feed, parse it, and save the result as JSON."""

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

        tickets = self.parse_tickets(download_path)
        print(f"parsed: {len(tickets)}")
        self.save_to_json(tickets, output_path)
        return tickets


def main():
    """Run the parser against the National Rail ticket feed."""

    parser = TicketParser()
    parser.download_and_parse(
        url="https://opendata.nationalrail.co.uk/api/staticfeeds/4.0/ticket-types",
        token=YOU_TOKEN_HERE,
        xml_path=parser.xml_path,
        json_path=parser.json_path,
    )


if __name__ == "__main__":
    main()
