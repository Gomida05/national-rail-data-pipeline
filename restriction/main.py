import requests
from pathlib import Path

TOKEN = "efootballmobile2023player@gmail.com:1780084332000:NT-Oy7ITuK_RUP05JyBxgro_CZlFDG98j_IvFclKbQU="
URL = "https://opendata.nationalrail.co.uk/api/staticfeeds/4.0/ticket-restrictions"

def download_and_parse(url: str, token: str, xml_path: str | Path | None = None, json_path: str | Path | None = None):
    """Download the XML feed, parse it, and save the result as JSON."""
    download_path = Path(xml_path)
    output_path = Path(json_path)
    download_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"X-Auth-Token": token, "Accept": "application/xml"}
    with requests.get(url, headers=headers, stream=True) as response:
        response.raise_for_status()
        with download_path.open("wb") as handle:
            for chunk in response.iter_content(8192):
                handle.write(chunk)

download_and_parse(
    url=URL,
    token=TOKEN,
    xml_path="restriction.xml",
    json_path="restriction.json"
)