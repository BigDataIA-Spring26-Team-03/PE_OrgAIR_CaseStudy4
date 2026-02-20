from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from sec_edgar_downloader import Downloader

from app.services.snowflake import SnowflakeService

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOCUMENTS_TABLE = "documents_sec"
CHUNKS_TABLE = "document_chunks_sec"

AFTER_DATE = os.getenv("SEC_AFTER_DATE", "2021-01-01")
SEC_SLEEP = float(os.getenv("SEC_SLEEP_SECONDS", "0.75"))

# Filing counts per the plan spec
FILING_COUNTS: Dict[str, int] = {
    "10-K": 2,
    "8-K": 2,
    "10-Q": 4,
}

# Canonical section names → exactly matches integration_service.py SEC_SECTION_MAP
CANONICAL = {
    "10-K": {
        "business":     "Item 1 (Business)",
        "risk_factors": "Item 1A (Risk)",
        "mda":          "Item 7 (MD&A)",
    },
    "8-K": {
        "8.01":  "Item 8.01",
        "5.02":  "Item 5.02",
        "2.01":  "Item 2.01",
        "1.01":  "Item 1.01",
    },
    "10-Q": {
        "part1item1": "Item 1",
        "part1item2": "Item 7 (MD&A)",   # Part I Item 2 = MD&A → same dimension as 10-K Item 7
        "part2item1": "Item 1A (Risk)",
    },
}

# Mistral OCR header → canonical name (used when OCR fallback runs for 10-K)
MISTRAL_HEADER_MAP: List[Tuple[str, str]] = [
    ("ITEM 1A",         "Item 1A (Risk)"),
    ("RISK FACTORS",    "Item 1A (Risk)"),
    ("ITEM 7",          "Item 7 (MD&A)"),
    ("MD&A",            "Item 7 (MD&A)"),
    ("MANAGEMENT",      "Item 7 (MD&A)"),
    ("ITEM 1",          "Item 1 (Business)"),   # must be after ITEM 1A
    ("BUSINESS",        "Item 1 (Business)"),
]

# Chunking parameters
MIN_WORDS = 500
MAX_WORDS = 1000
OVERLAP_WORDS = 75
MIN_BLOCK_WORDS = 10
MAX_NUMERIC_RATIO = 0.65


# ---------------------------------------------------------------------------
# SECPipeline
# ---------------------------------------------------------------------------

class SECPipeline:
    """
    Unified download → parse → chunk → store pipeline for SEC filings.

    Usage:
        pipeline = SECPipeline()
        result = pipeline.run("NVDA")
        # result = {"ticker": "NVDA", "docs_processed": 8, "chunks_created": 142, "errors": []}
    """

    def __init__(self) -> None:
        self._email = self._require_env("SEC_EDGAR_USER_AGENT_EMAIL")
        self._bucket = self._require_env("S3_BUCKET_NAME")
        self._region = os.getenv("AWS_REGION", "us-east-1")
        self._mistral_key = os.getenv("MISTRAL_API_KEY")

        # Set edgartools identity (required for all SEC EDGAR API calls)
        try:
            from edgar import set_identity  # type: ignore
            set_identity(f"OrgAIR {self._email}")
        except Exception as exc:
            logger.warning("Could not set edgartools identity: %s", exc)

        self._db = SnowflakeService()
        self._s3 = boto3.client(
            "s3",
            region_name=self._region,
            config=Config(
                retries={"max_attempts": 10, "mode": "adaptive"},
                connect_timeout=60,
                read_timeout=300,
                tcp_keepalive=True,
            ),
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, ticker: str) -> Dict[str, Any]:
        """
        Full pipeline for one ticker. Downloads, parses, chunks, and stores all filings.
        Skips duplicates based on content hash.
        """
        ticker = ticker.upper().strip()
        logger.info("=" * 60)
        logger.info("SEC PIPELINE: %s", ticker)
        logger.info("=" * 60)

        company_id = self._resolve_company_id(ticker)

        docs = self._download(ticker, company_id)
        total_chunks = 0
        errors: List[str] = []

        for doc in docs:
            try:
                sections = self._parse_doc(doc)
                if not sections:
                    logger.warning("No sections extracted for %s %s", ticker, doc["filing_type"])
                    continue

                parsed_s3_key = self._save_parsed_to_s3(
                    ticker, doc["filing_type"], doc["filing_date"], sections, doc["doc_id"]
                )
                self._update_doc_status(doc["doc_id"], "parsed", {"s3_key": parsed_s3_key})

                all_chunks: List[Dict[str, Any]] = []
                for section_name, text in sections.items():
                    if not text or len(text.split()) < MIN_BLOCK_WORDS:
                        continue
                    chunks = self._chunk_section(text, section_name, doc["doc_id"])
                    all_chunks.extend(chunks)

                if all_chunks:
                    self._save_chunks(all_chunks)
                    total_chunks += len(all_chunks)
                    total_word_count = sum(c["word_count"] for c in all_chunks)
                    self._update_doc_status(
                        doc["doc_id"], "chunked",
                        {
                            "chunk_count": len(all_chunks),
                            "word_count": total_word_count,
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    logger.info(
                        "  %s %s → %d chunks across %d sections",
                        ticker, doc["filing_type"], len(all_chunks), len(sections)
                    )

            except Exception as exc:
                msg = f"{ticker} {doc.get('filing_type')} {doc.get('doc_id')}: {exc}"
                logger.error("Error processing doc: %s", msg)
                errors.append(msg)
                self._update_doc_status(doc["doc_id"], "failed", {"error_message": str(exc)[:500]})

        result = {
            "ticker": ticker,
            "docs_processed": len(docs),
            "chunks_created": total_chunks,
            "errors": errors,
        }
        logger.info("Done: %s", result)
        return result

    # ------------------------------------------------------------------
    # Step 2: Download from SEC EDGAR
    # ------------------------------------------------------------------

    def _download(self, ticker: str, company_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Download filings for each type, upload raw files to S3,
        insert records into documents_sec. Returns list of doc metadata dicts.
        """
        download_root = Path("data/raw")
        download_root.mkdir(parents=True, exist_ok=True)

        dl = Downloader("OrgAIR", self._email, str(download_root))
        docs: List[Dict[str, Any]] = []
        run_date = date.today().isoformat()

        for filing_type, limit in FILING_COUNTS.items():
            logger.info("Downloading %s x%d for %s", filing_type, limit, ticker)
            try:
                dl.get(filing_type, ticker, limit=limit, after=AFTER_DATE)
            except Exception as exc:
                logger.error("SEC download failed for %s %s: %s", ticker, filing_type, exc)
                time.sleep(SEC_SLEEP)
                continue
            time.sleep(SEC_SLEEP)

            folders = self._get_download_folders(ticker, filing_type, limit)
            for folder in folders:
                main_file = self._pick_main_file(folder)
                if not main_file:
                    continue

                content_hash = self._sha256(main_file)
                existing = self._db.execute_query(
                    f"SELECT id, status, local_path, s3_key FROM {DOCUMENTS_TABLE} WHERE content_hash = %(h)s AND UPPER(ticker) = %(t)s LIMIT 1",
                    {"h": content_hash, "t": ticker},
                )
                if existing:
                    row = existing[0]
                    status = str(row.get("STATUS") or row.get("status", ""))
                    if status == "chunked":
                        logger.info("  Skipping (already chunked): %s", main_file.name)
                        continue
                    # Exists but not chunked — re-queue for parsing
                    existing_id = str(row.get("ID") or row.get("id"))
                    existing_path = str(row.get("LOCAL_PATH") or row.get("local_path") or str(main_file))
                    logger.info("  Re-queuing for parse (status=%s): %s doc_id=%s", status, main_file.name, existing_id)
                    docs.append({
                        "doc_id": existing_id,
                        "ticker": ticker,
                        "filing_type": filing_type,
                        "filing_date": run_date,
                        "local_path": existing_path,
                        "s3_key": str(row.get("S3_KEY") or row.get("s3_key", "")),
                        "is_pdf": main_file.suffix.lower() == ".pdf",
                    })
                    continue

                filing_date = self._extract_date(folder)
                ft_norm = filing_type.upper().replace(" ", "").replace("-", "")
                s3_key = f"sec/{ticker}/{ft_norm}/{run_date}/{uuid4()}{main_file.suffix}"

                uploaded = self._s3_upload(main_file, s3_key)
                if not uploaded:
                    continue

                source_url = self._build_source_url(folder, main_file)
                doc_id = str(uuid4())

                self._db.execute_update(
                    f"""
                    INSERT INTO {DOCUMENTS_TABLE}
                        (id, company_id, ticker, filing_type, filing_date,
                         source_url, local_path, s3_key, content_hash, status, created_at)
                    VALUES
                        (%(id)s, %(cid)s, %(ticker)s, %(ft)s, %(fdate)s,
                         %(url)s, %(lpath)s, %(s3key)s, %(hash)s, 'downloaded', %(now)s)
                    """,
                    {
                        "id": doc_id,
                        "cid": company_id,
                        "ticker": ticker,
                        "ft": filing_type,
                        "fdate": str(filing_date) if filing_date else None,
                        "url": source_url,
                        "lpath": str(main_file),
                        "s3key": s3_key,
                        "hash": content_hash,
                        "now": datetime.now(timezone.utc).isoformat(),
                    },
                )

                docs.append({
                    "doc_id": doc_id,
                    "ticker": ticker,
                    "filing_type": filing_type,
                    "filing_date": str(filing_date) if filing_date else run_date,
                    "local_path": str(main_file),
                    "s3_key": s3_key,
                    "is_pdf": main_file.suffix.lower() == ".pdf",
                })
                logger.info("  Stored %s %s doc_id=%s", filing_type, main_file.name, doc_id)

        return docs

    # ------------------------------------------------------------------
    # Step 3: Parse — edgartools primary, Mistral OCR fallback for PDFs
    # ------------------------------------------------------------------

    def _parse_doc(self, doc: Dict[str, Any]) -> Dict[str, str]:
        """
        Route to correct parser based on filing type and file format.
        Returns {canonical_section_name: clean_text}.
        """
        filing_type = doc["filing_type"]
        ticker = doc["ticker"]
        local_path = doc["local_path"]
        is_pdf = doc.get("is_pdf", False)

        if is_pdf:
            logger.info("  PDF detected — using Mistral OCR for %s", local_path)
            return self._parse_with_mistral_ocr(local_path, filing_type)

        # edgartools primary
        try:
            sections = self._parse_with_edgartools(ticker, filing_type, local_path)
            if sections:
                # For 10-K: edgartools sometimes misses Item 7 (mda returns None).
                # Supplement any missing critical sections from the local HTML file.
                if filing_type == "10-K":
                    expected = ["Item 1 (Business)", "Item 1A (Risk)", "Item 7 (MD&A)"]
                    missing = [s for s in expected if s not in sections]
                    if missing:
                        logger.info("  edgartools missing %s — supplementing from local HTML", missing)
                        bs_sections = self._parse_with_beautifulsoup(local_path, filing_type)
                        for s in missing:
                            if s in bs_sections:
                                sections[s] = bs_sections[s]
                                logger.info("  Supplemented %s from BeautifulSoup", s)
                return sections
        except Exception as exc:
            logger.warning("edgartools failed for %s %s: %s — trying HTML parser", ticker, filing_type, exc)

        # HTML fallback (BeautifulSoup) — handles full-submission.txt and .htm files
        return self._parse_with_beautifulsoup(local_path, filing_type)

    def _parse_with_edgartools(
        self, ticker: str, filing_type: str, local_path: str
    ) -> Dict[str, str]:
        """
        Use edgartools to extract clean section text from SEC filings.
        Returns canonical {section_name: text} dict.
        """
        from edgar import Company  # type: ignore

        company = Company(ticker)
        sections: Dict[str, str] = {}

        if filing_type == "10-K":
            filings = company.get_filings(form="10-K")
            if not filings:
                return {}
            tenk = filings.latest(1).obj()
            raw = {
                "business":     getattr(tenk, "business", None),
                "risk_factors": getattr(tenk, "risk_factors", None),
                "mda":          getattr(tenk, "mda", None),
            }
            for attr_key, canonical_name in CANONICAL["10-K"].items():
                text = raw.get(attr_key)
                if text:
                    text_str = str(text).strip()
                    if len(text_str.split()) >= MIN_BLOCK_WORDS:
                        sections[canonical_name] = text_str

        elif filing_type == "10-Q":
            filings = company.get_filings(form="10-Q")
            if not filings:
                return {}
            tenq = filings.latest(1).obj()
            # edgartools TenQ exposes parts/items
            for attr_key, canonical_name in CANONICAL["10-Q"].items():
                text = getattr(tenq, attr_key, None)
                if text:
                    text_str = str(text).strip()
                    if len(text_str.split()) >= MIN_BLOCK_WORDS:
                        sections[canonical_name] = text_str

        
        elif filing_type == "8-K":
            filings = company.get_filings(form="8-K")
            if not filings:
                return {}
            eightk = filings.latest(1).obj()
            items_raw = getattr(eightk, "items", None) or []

            # edgartools can return items as a list of objects OR a dict — handle both
            if isinstance(items_raw, dict):
                items_dict = items_raw
            elif isinstance(items_raw, list):
                # Each item in the list is typically an object with .item_number and .text attributes
                items_dict = {}
                for item in items_raw:
                    # Try attribute-style access first (edgartools Item objects)
                    item_num = getattr(item, "item_number", None) or getattr(item, "number", None)
                    text = getattr(item, "text", None) or getattr(item, "content", None)
                    if item_num and text:
                        items_dict[str(item_num)] = text
                    elif isinstance(item, str):
                        # Fallback: plain string — store by index
                        items_dict[str(len(items_dict))] = item
            else:
                logger.warning("Unexpected 8-K items type: %s", type(items_raw))
                items_dict = {}

            logger.info("8-K items resolved: %s", list(items_dict.keys()))

            for item_num, canonical_name in CANONICAL["8-K"].items():
                text = items_dict.get(item_num)
                if text:
                    text_str = str(text).strip()
                    if len(text_str.split()) >= MIN_BLOCK_WORDS:
                        sections[canonical_name] = text_str

                return sections

    def _parse_with_mistral_ocr(
        self, local_path: str, filing_type: str
    ) -> Dict[str, str]:
        """
        Use Mistral OCR API to extract structured markdown from a PDF filing,
        then map markdown headers to canonical section names.
        Requires MISTRAL_API_KEY env var.
        """
        if not self._mistral_key:
            logger.warning("MISTRAL_API_KEY not set — Mistral OCR fallback unavailable")
            return {}

        try:
            from mistralai import Mistral  # type: ignore

            client = Mistral(api_key=self._mistral_key)

            with open(local_path, "rb") as f:
                file_data = f.read()

            # Upload file to Mistral
            uploaded = client.files.upload(
                file={"file_name": Path(local_path).name, "content": file_data},
                purpose="ocr",
            )
            signed = client.files.get_signed_url(file_id=uploaded.id, expiry=1)

            # Run OCR
            ocr_result = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "url", "url": signed.url},
            )

            # Combine all pages into one markdown string
            full_markdown = "\n\n".join(
                page.markdown for page in ocr_result.pages if page.markdown
            )

            return self._extract_sections_from_markdown(full_markdown, filing_type)

        except Exception as exc:
            logger.error("Mistral OCR failed for %s: %s", local_path, exc)
            return {}

    def _extract_primary_document(self, raw: bytes) -> bytes:
        """
        Extract the primary HTML document from an SGML full-submission.txt.
        The SGML wrapper contains multiple <DOCUMENT> blocks (filings + exhibits +
        binary attachments). We only want the first <TEXT> block (the actual filing).
        Uses plain string search — no regex.
        """
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return raw

        # Find the first <TEXT> marker (the primary filing document)
        start_marker = "<TEXT>"
        end_marker = "</TEXT>"
        start = text.find(start_marker)
        if start == -1:
            return raw  # Not SGML — return as-is

        end = text.find(end_marker, start)
        if end == -1:
            end = len(text)

        primary = text[start + len(start_marker):end]
        return primary.encode("utf-8")

    def _parse_with_beautifulsoup(
        self, local_path: str, filing_type: str
    ) -> Dict[str, str]:
        """
        Parse HTML/SGML SEC filings using BeautifulSoup.
        Extracts only the primary document from the SGML container first,
        then locates Item headings and captures the text that follows each.
        Used as fallback when edgartools cannot connect.
        """
        from bs4 import BeautifulSoup  # type: ignore

        try:
            with open(local_path, "rb") as f:
                raw = f.read()

            # Strip the SGML wrapper — only parse the primary filing HTML
            primary_html = self._extract_primary_document(raw)
            soup = BeautifulSoup(primary_html, "lxml")

            # Remove script/style/table-of-contents noise
            for tag in soup(["script", "style", "head"]):
                tag.decompose()

            # Collect all text-bearing elements in document order
            elements = soup.find_all(["p", "div", "span", "td", "tr", "h1", "h2", "h3", "h4"])

            sections: Dict[str, str] = {}
            current_section: Optional[str] = None
            current_lines: List[str] = []

            def flush() -> None:
                if not current_section or not current_lines:
                    return
                text = "\n\n".join(current_lines).strip()
                if len(text.split()) >= MIN_BLOCK_WORDS:
                    if current_section not in sections:
                        sections[current_section] = text
                    else:
                        sections[current_section] += "\n\n" + text

            for el in elements:
                raw_text = el.get_text(separator=" ", strip=True)
                if not raw_text or len(raw_text) < 5:
                    continue

                upper = raw_text.upper()[:120]  # Only check start of text for headings

                # Detect section headings by Item keyword presence in short text blocks
                if len(raw_text) < 200:
                    detected = self._detect_section_heading(upper, filing_type)
                    if detected:
                        flush()
                        current_section = detected
                        current_lines = []
                        continue

                if current_section and len(raw_text.split()) >= 5:
                    current_lines.append(raw_text)

            flush()
            logger.info("  BeautifulSoup extracted %d sections from %s", len(sections), Path(local_path).name)
            return sections

        except Exception as exc:
            logger.error("BeautifulSoup parse failed for %s: %s", local_path, exc)
            return {}

    def _detect_section_heading(self, upper_text: str, filing_type: str) -> Optional[str]:
        """
        Identify whether a short text block is a known section heading.
        Uses plain string containment — no regex.
        """
        if filing_type == "10-K":
            # Order matters: check 1A before 1
            if "ITEM 1A" in upper_text or "RISK FACTORS" in upper_text:
                return "Item 1A (Risk)"
            if "ITEM 7A" in upper_text:
                return None  # Quantitative disclosures — skip
            if "ITEM 7" in upper_text and ("MANAGEMENT" in upper_text or "MD&A" in upper_text or upper_text.strip().startswith("ITEM 7")):
                return "Item 7 (MD&A)"
            if "ITEM 1" in upper_text and "BUSINESS" in upper_text:
                return "Item 1 (Business)"
            if upper_text.strip() in ("ITEM 1.", "ITEM 1"):
                return "Item 1 (Business)"
        elif filing_type == "10-Q":
            if "ITEM 1A" in upper_text or "RISK FACTORS" in upper_text:
                return "Item 1A (Risk)"
            if "ITEM 2" in upper_text and ("MANAGEMENT" in upper_text or "MD&A" in upper_text):
                return "Item 7 (MD&A)"   # 10-Q Part I Item 2 = MD&A
            if "ITEM 1" in upper_text and "FINANCIAL" in upper_text:
                return "Item 1"
        elif filing_type == "8-K":
            for item_num, canonical in CANONICAL["8-K"].items():
                if f"ITEM {item_num.upper()}" in upper_text:
                    return canonical
        return None

    def _extract_sections_from_markdown(
        self, markdown: str, filing_type: str
    ) -> Dict[str, str]:
        """
        Parse markdown from Mistral OCR output into canonical sections.
        Uses header-level splitting (no regex on raw HTML).
        """
        sections: Dict[str, str] = {}
        if not markdown:
            return sections

        # Split on markdown headers (# or ##)
        lines = markdown.split("\n")
        current_header: Optional[str] = None
        current_lines: List[str] = []

        def flush(header: Optional[str], body_lines: List[str]) -> None:
            if not header:
                return
            canonical = self._map_header_to_canonical(header, filing_type)
            if canonical:
                text = "\n".join(body_lines).strip()
                if len(text.split()) >= MIN_BLOCK_WORDS:
                    if canonical not in sections:
                        sections[canonical] = text
                    else:
                        sections[canonical] += "\n\n" + text

        for line in lines:
            if line.startswith("#"):
                flush(current_header, current_lines)
                current_header = line.lstrip("#").strip().upper()
                current_lines = []
            else:
                current_lines.append(line)

        flush(current_header, current_lines)
        return sections

    def _map_header_to_canonical(self, header_upper: str, filing_type: str) -> Optional[str]:
        """
        Map an uppercase markdown header string to a canonical section name.
        Works for 10-K, 10-Q, 8-K using the MISTRAL_HEADER_MAP and CANONICAL tables.
        """
        # 10-K: use MISTRAL_HEADER_MAP (ordered, ITEM 1A before ITEM 1)
        if filing_type == "10-K":
            for pattern, canonical in MISTRAL_HEADER_MAP:
                if pattern in header_upper:
                    return canonical
            return None

        # 8-K: look for ITEM X.XX patterns
        if filing_type == "8-K":
            for item_num, canonical in CANONICAL["8-K"].items():
                if item_num in header_upper:
                    return canonical
            return None

        # 10-Q: look for PART I ITEM 1/2
        if filing_type == "10-Q":
            if "ITEM 1A" in header_upper or "RISK" in header_upper:
                return "Item 1A (Risk)"
            if "ITEM 2" in header_upper or "MD&A" in header_upper or "MANAGEMENT" in header_upper:
                return "Item 7 (MD&A)"   # 10-Q Part I Item 2 = MD&A
            if "ITEM 1" in header_upper:
                return "Item 1"
            return None

        return None

    # ------------------------------------------------------------------
    # Step 4: Chunk sections
    # ------------------------------------------------------------------

    def _chunk_section(
        self, text: str, section: str, doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        Semantic chunking within a single section.
        - Splits on paragraph boundaries (\n\n)
        - Filters noise blocks
        - Builds 500–1000 word windows with 75-word overlap
        """
        # Split into paragraph blocks
        raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

        # Filter noise blocks
        clean_blocks: List[str] = []
        for block in raw_blocks:
            words = block.split()
            if len(words) < MIN_BLOCK_WORDS:
                continue
            numeric_chars = sum(1 for c in block if c.isdigit() or c in ",.$()")
            if len(block) > 0 and numeric_chars / len(block) > MAX_NUMERIC_RATIO:
                continue
            clean_blocks.append(block)

        if not clean_blocks:
            return []

        # Build chunks by accumulating blocks until hitting word target
        chunks: List[Dict[str, Any]] = []
        current_words: List[str] = []
        char_offset = 0
        chunk_start = 0

        def make_chunk(words: List[str], start: int) -> Dict[str, Any]:
            content = " ".join(words)
            return {
                "id": str(uuid4()),
                "document_id": doc_id,
                "chunk_index": len(chunks),
                "content": content,
                "section": section,
                "word_count": len(words),
                "start_char": start,
                "end_char": start + len(content),
            }

        for block in clean_blocks:
            block_words = block.split()
            if len(current_words) + len(block_words) > MAX_WORDS and current_words:
                chunks.append(make_chunk(current_words, chunk_start))
                # Overlap: carry last OVERLAP_WORDS into next chunk
                overlap = current_words[-OVERLAP_WORDS:] if len(current_words) > OVERLAP_WORDS else current_words[:]
                chunk_start = char_offset - len(" ".join(overlap))
                current_words = overlap
            current_words.extend(block_words)
            char_offset += len(block) + 2  # +2 for \n\n separator

        # Final chunk
        if len(current_words) >= MIN_BLOCK_WORDS:
            chunks.append(make_chunk(current_words, chunk_start))
        elif chunks and current_words:
            # Merge undersized tail into previous chunk
            chunks[-1]["content"] += " " + " ".join(current_words)
            chunks[-1]["word_count"] += len(current_words)
            chunks[-1]["end_char"] = chunks[-1]["start_char"] + len(chunks[-1]["content"])

        # Guard: split any chunk still over MAX_WORDS at sentence boundary
        final_chunks: List[Dict[str, Any]] = []
        for chunk in chunks:
            if chunk["word_count"] <= MAX_WORDS:
                final_chunks.append(chunk)
            else:
                split_chunks = self._split_oversized(chunk, doc_id, len(final_chunks))
                final_chunks.extend(split_chunks)

        # Re-index
        for i, c in enumerate(final_chunks):
            c["chunk_index"] = i

        return final_chunks

    def _split_oversized(
        self, chunk: Dict[str, Any], doc_id: str, index_offset: int
    ) -> List[Dict[str, Any]]:
        """Split a chunk that exceeds MAX_WORDS at sentence boundaries."""
        sentences = chunk["content"].split(". ")
        result: List[Dict[str, Any]] = []
        current: List[str] = []

        for sentence in sentences:
            current.append(sentence)
            if len(" ".join(current).split()) >= MIN_WORDS:
                content = ". ".join(current).strip()
                result.append({
                    "id": str(uuid4()),
                    "document_id": doc_id,
                    "chunk_index": index_offset + len(result),
                    "content": content,
                    "section": chunk["section"],
                    "word_count": len(content.split()),
                    "start_char": chunk["start_char"],
                    "end_char": chunk["start_char"] + len(content),
                })
                current = []

        if current:
            content = ". ".join(current).strip()
            if result:
                result[-1]["content"] += " " + content
                result[-1]["word_count"] += len(content.split())
            else:
                result.append({
                    "id": str(uuid4()),
                    "document_id": doc_id,
                    "chunk_index": index_offset,
                    "content": content,
                    "section": chunk["section"],
                    "word_count": len(content.split()),
                    "start_char": chunk["start_char"],
                    "end_char": chunk["start_char"] + len(content),
                })

        return result

    # ------------------------------------------------------------------
    # Step 5: Save to S3 + Snowflake
    # ------------------------------------------------------------------

    def _save_parsed_to_s3(
        self,
        ticker: str,
        filing_type: str,
        filing_date: str,
        sections: Dict[str, str],
        doc_id: str,
    ) -> str:
        """Save parsed sections as gzip JSON to S3. Returns S3 key."""
        ft_norm = filing_type.upper().replace(" ", "").replace("-", "")
        s3_key = f"parsed/{ticker}/{ft_norm}/{filing_date}/{doc_id}.json.gz"
        payload = {
            "doc_id": doc_id,
            "ticker": ticker,
            "filing_type": filing_type,
            "sections": {k: v for k, v in sections.items()},
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }
        body = gzip.compress(json.dumps(payload).encode("utf-8"))
        self._s3.put_object(Bucket=self._bucket, Key=s3_key, Body=body, ContentType="application/gzip")
        return s3_key

    def _save_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Batch insert chunks into document_chunks_sec."""
        for chunk in chunks:
            # Escape single quotes in content
            safe_content = chunk["content"].replace("'", "''")
            safe_section = chunk["section"].replace("'", "''")
            self._db.execute_update(
                f"""
                INSERT INTO {CHUNKS_TABLE}
                    (id, document_id, chunk_index, content, section,
                     word_count, start_char, end_char)
                VALUES
                    (%(id)s, %(doc_id)s, %(idx)s, %(content)s, %(section)s,
                     %(wc)s, %(sc)s, %(ec)s)
                """,
                {
                    "id": chunk["id"],
                    "doc_id": chunk["document_id"],
                    "idx": chunk["chunk_index"],
                    "content": chunk["content"],
                    "section": chunk["section"],
                    "wc": chunk["word_count"],
                    "sc": chunk.get("start_char", 0),
                    "ec": chunk.get("end_char", 0),
                },
            )

    def _update_doc_status(
        self, doc_id: str, status: str, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update status (and optional fields) in documents_sec."""
        set_parts = ["status = %(status)s"]
        params: Dict[str, Any] = {"status": status, "id": doc_id}

        if extra:
            for k, v in extra.items():
                set_parts.append(f"{k} = %({k})s")
                params[k] = v

        self._db.execute_update(
            f"UPDATE {DOCUMENTS_TABLE} SET {', '.join(set_parts)} WHERE id = %(id)s",
            params,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _resolve_company_id(self, ticker: str) -> Optional[str]:
        rows = self._db.execute_query(
            "SELECT id FROM companies WHERE UPPER(ticker) = %(t)s AND is_deleted = FALSE LIMIT 1",
            {"t": ticker},
        )
        if rows:
            r = rows[0]
            return str(r.get("ID") or r.get("id"))
        logger.warning("Company %s not found in companies table — proceeding without company_id", ticker)
        return None

    def _get_download_folders(self, ticker: str, filing_type: str, limit: int) -> List[Path]:
        base = Path("data/raw/sec-edgar-filings") / ticker / filing_type
        if not base.exists():
            return []
        subdirs = [p for p in base.iterdir() if p.is_dir()]
        subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return subdirs[:limit]

    def _pick_main_file(self, folder: Path) -> Optional[Path]:
        candidates = list(folder.rglob("full-submission.txt"))
        if not candidates:
            candidates = (
                list(folder.rglob("*.txt"))
                + list(folder.rglob("*.html"))
                + list(folder.rglob("*.htm"))
                + list(folder.rglob("*.pdf"))
            )
        if not candidates:
            candidates = [p for p in folder.rglob("*") if p.is_file()]
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
        return candidates[0]

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def _s3_upload(self, local_path: Path, s3_key: str) -> bool:
        for attempt in range(1, 6):
            try:
                with local_path.open("rb") as f:
                    self._s3.put_object(
                        Bucket=self._bucket,
                        Key=s3_key,
                        Body=f.read(),
                        ContentType="text/plain",
                    )
                return True
            except (BotoCoreError, ClientError) as exc:
                wait = min(2 ** attempt, 30)
                logger.warning("S3 upload attempt %d failed: %s — retrying in %ds", attempt, exc, wait)
                time.sleep(wait)
        logger.error("S3 upload failed after 5 attempts: %s", s3_key)
        return False

    def _build_source_url(self, folder: Path, main_file: Path) -> Optional[str]:
        accession = folder.name
        parts = accession.split("-")
        if len(parts) < 3:
            return None
        cik = parts[0].lstrip("0") or "0"
        accession_nodashes = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodashes}/{main_file.name}"

    def _extract_date(self, folder: Path) -> Optional[date]:
        parts = folder.name.split("-")
        if len(parts) < 3:
            return None
        try:
            yr = int(parts[1])
            yr = yr + 2000 if yr < 50 else yr + 1900
            return date(yr, 1, 1)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _require_env(name: str) -> str:
        v = os.getenv(name)
        if not v:
            raise RuntimeError(f"Missing required env var: {name}")
        return v


# ---------------------------------------------------------------------------
# CLI / Script entry point
# ---------------------------------------------------------------------------

def run_pipeline(tickers: Optional[List[str]] = None) -> None:
    """Run the SEC pipeline for specified tickers (or default 5 companies)."""
    default_tickers = ["NVDA", "JPM", "WMT", "GE", "DG"]
    targets = [t.upper() for t in (tickers or default_tickers)]

    pipeline = SECPipeline()
    for ticker in targets:
        try:
            result = pipeline.run(ticker)
            logger.info("Result for %s: %s", ticker, result)
        except Exception as exc:
            logger.error("Pipeline failed for %s: %s", ticker, exc)


if __name__ == "__main__":
    import sys
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    run_pipeline(tickers)
