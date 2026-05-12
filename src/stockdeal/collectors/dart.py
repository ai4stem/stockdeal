"""Open DART API client.

Docs: https://opendart.fss.or.kr/

Endpoints used:
- corpCode.xml         : full corp_code mapping (bootstrap once; cache locally)
- list.json            : disclosure list by corp_code / date range
- fnlttSinglAcntAll    : single-company financial statements (annual / quarterly)

Rate limit: 10,000 calls/day per key. Bootstrap is 1 call; daily polling is
~10 calls per watchlist ticker so well within budget.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from stockdeal.config import get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)

BASE = "https://opendart.fss.or.kr/api"
CORP_CODE_CACHE = Path(".dart_corp_code.json")

REPORT_CODES = {
    "Q1": "11013",
    "HALF": "11012",
    "Q3": "11014",
    "ANNUAL": "11011",
}
PERIOD_END_BY_REPORT = {
    "11013": (3, 31),
    "11012": (6, 30),
    "11014": (9, 30),
    "11011": (12, 31),
}
REPORT_NAME_BY_CODE = {v: k for k, v in REPORT_CODES.items()}


class DartError(RuntimeError):
    pass


class DartClient:
    def __init__(self) -> None:
        self._key = get_settings().dart_api_key.get_secret_value()
        self._http = httpx.AsyncClient(base_url=BASE, timeout=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # corp_code bootstrap
    # ------------------------------------------------------------------
    async def fetch_corp_code_zip(self) -> bytes:
        r = await self._http.get("/corpCode.xml", params={"crtfc_key": self._key})
        if r.status_code != 200:
            raise DartError(f"corpCode http {r.status_code}: {r.text[:200]}")
        # Some errors come back as a JSON error body with status=200; sniff zip magic.
        if not r.content.startswith(b"PK"):
            raise DartError(f"corpCode unexpected payload: {r.text[:200]}")
        return r.content

    @staticmethod
    def parse_corp_code_xml(zip_bytes: bytes) -> list[dict[str, str]]:
        """Return [{'corp_code', 'corp_name', 'stock_code'}, ...] for listed firms."""
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            inner = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
            data = zf.read(inner)
        root = ET.fromstring(data)
        out: list[dict[str, str]] = []
        for el in root.findall("list"):
            stock_code = (el.findtext("stock_code") or "").strip()
            if not stock_code:
                continue  # skip non-listed companies
            out.append(
                {
                    "corp_code": (el.findtext("corp_code") or "").strip(),
                    "corp_name": (el.findtext("corp_name") or "").strip(),
                    "stock_code": stock_code,
                }
            )
        return out

    # ------------------------------------------------------------------
    # Disclosures
    # ------------------------------------------------------------------
    async def list_disclosures(
        self,
        corp_code: str,
        bgn_de: date | None = None,
        end_de: date | None = None,
        page_no: int = 1,
        page_count: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "crtfc_key": self._key,
            "corp_code": corp_code,
            "page_no": page_no,
            "page_count": page_count,
        }
        if bgn_de:
            params["bgn_de"] = bgn_de.strftime("%Y%m%d")
        if end_de:
            params["end_de"] = end_de.strftime("%Y%m%d")
        body = await self._get_json("/list.json", params)
        if body.get("status") not in ("000", "013"):  # 013 = no data
            raise DartError(f"list.json status={body.get('status')} msg={body.get('message')}")
        return body.get("list", []) or []

    # ------------------------------------------------------------------
    # Financial statements
    # ------------------------------------------------------------------
    async def fetch_financial_statements(
        self,
        corp_code: str,
        bsns_year: int,
        reprt_code: str,            # see REPORT_CODES
        fs_div: str = "OFS",        # OFS=별도, CFS=연결
    ) -> list[dict[str, Any]]:
        params = {
            "crtfc_key": self._key,
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }
        body = await self._get_json("/fnlttSinglAcntAll.json", params)
        if body.get("status") not in ("000", "013"):
            raise DartError(
                f"fnlttSinglAcntAll status={body.get('status')} msg={body.get('message')}"
            )
        return body.get("list", []) or []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        r = await self._http.get(path, params=params)
        if r.status_code != 200:
            raise DartError(f"http {r.status_code}: {r.text[:200]}")
        return r.json()


# ----------------------------------------------------------------------
# Helpers (no network)
# ----------------------------------------------------------------------
def disclosure_url(rcept_no: str) -> str:
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"


def parse_rcept_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")


def period_end_for(reprt_code: str, bsns_year: int) -> date:
    m, d = PERIOD_END_BY_REPORT[reprt_code]
    return date(bsns_year, m, d)


def period_type_for(reprt_code: str) -> str:
    return REPORT_NAME_BY_CODE.get(reprt_code, "UNKNOWN")
