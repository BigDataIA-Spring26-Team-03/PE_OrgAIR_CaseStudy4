from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import List, Dict, Optional
from uuid import uuid4

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, SSLError
from dotenv import load_dotenv
from sec_edgar_downloader import Downloader

from app.services.snowflake import SnowflakeService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# CONFIGURATION


DEFAULT_TARGET_TICKERS = ["CAT", "DE", "UNH", "HCA", "ADP", "PAYX", "WMT", "TGT", "JPM", "GS"]

# Table names (Case Study 3 uses separate tables)
DOCUMENTS_TABLE = "documents_sec"
CHUNKS_TABLE = "document_chunks_sec"

# Differential limits: 3 + 4 + 5 + 2 = 14 per company × 10 = 140 total
DEFAULT_FILING_TYPES = {
    "10-K": 3,      # Annual reports (3 years)
    "10-Q": 4,      # Quarterly reports (4 quarters)
    "8-K": 5,       # Material events (recent 5)
    "DEF 14A": 2    # Proxy statements (2 years)
}

FILING_TYPES = list(DEFAULT_FILING_TYPES.keys())

# SEC rate limiting: 10 req/sec max, using 0.75s = 1.33 req/sec (safe margin)
SEC_REQUEST_SLEEP_SECONDS = float(os.getenv("SEC_SLEEP_SECONDS", "0.75"))

# Download filings filed after this date
AFTER_DATE = os.getenv("SEC_AFTER_DATE", "2021-01-01")


# UTILITY FUNCTIONS


def require_env(name: str) -> str:
    """Get required environment variable or raise error."""
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 hash of file in 1MB chunks (memory efficient)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_all_download_folders(ticker: str, filing_type: str, limit: int) -> list[Path]:
    """
    Get multiple downloaded filing folders (up to limit).
    
    Returns folders sorted by modification time (newest first).
    sec-edgar-downloader creates folders like: data/raw/sec-edgar-filings/CAT/10-K/0000012345-24-000001/
    """
    base = Path("data/raw") / "sec-edgar-filings" / ticker / filing_type
    if not base.exists():
        return []
    
    subdirs = [p for p in base.iterdir() if p.is_dir()]
    if not subdirs:
        return []
    
    # Sort by modification time (newest first)
    subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return subdirs[:limit]


def pick_main_file(folder: Path) -> Optional[Path]:
    """
    Select the main filing file from downloaded folder.
    
    Priority:
    1. full-submission.txt (SEC standard filename)
    2. Any .txt, .html, .htm file
    3. Largest file in folder
    """
    # Priority 1: SEC standard filename
    candidates = list(folder.rglob("full-submission.txt"))
    
    # Priority 2: Text or HTML files
    if not candidates:
        candidates = (
            list(folder.rglob("*.txt")) +
            list(folder.rglob("*.html")) +
            list(folder.rglob("*.htm"))
        )
    
    # Priority 3: Any file
    if not candidates:
        candidates = [p for p in folder.rglob("*") if p.is_file()]
    
    if not candidates:
        return None
    
    # Pick largest file (likely the main document)
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def filing_type_for_paths(filing_type: str) -> str:
    """
    Normalize filing type for URLs and S3 keys.
    
    Examples:
        "10-K" -> "10K"
        "DEF 14A" -> "DEF14A"
        "def-14a" -> "DEF14A"
    """
    t = filing_type.upper().strip()
    t = t.replace(" ", "")   
    t = t.replace("-", "")   
    return t


def build_sec_source_url(download_folder: Path, main_file: Path) -> Optional[str]:
    """
    Build SEC EDGAR URL from downloaded folder structure.
    
    Folder name format: {CIK}-{YY}-{NNNNNN}
    Example: 0000320193-25-000079
    
    Output: https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION_NO_DASHES}/{FILENAME}
    Example: https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/full-submission.txt
    """
    accession = download_folder.name
    parts = accession.split("-")
    
    if len(parts) < 3:
        return None
    
    # Extract CIK and remove leading zeros
    cik = parts[0].lstrip("0") or "0"
    
    # Build accession number without dashes
    accession_nodashes = accession.replace("-", "")
    
    filename = main_file.name
    
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodashes}/{filename}"


def extract_filing_date_from_folder(folder: Path) -> Optional[date]:
    """
    Extract approximate filing date from accession number.
    
    Accession format: CIK-YY-NNNNNN
    Example: 0000012345-24-000123 -> Year 2024
    
    Note: We only extract the year, set to January 1st.
    Actual filing date would need to be parsed from document content.
    """
    accession = folder.name
    parts = accession.split("-")
    
    if len(parts) < 3:
        return None
    
    try:
        year_str = parts[1]
        year = int(year_str)
        
        # Convert 2-digit year to 4-digit (pivot at 50)
        if year < 50:
            year += 2000
        else:
            year += 1900
        
        # Return January 1st of that year
        return date(year, 1, 1)
    except (ValueError, IndexError):
        return None


def upload_file_with_retry(
    s3_client,
    file_path: str,
    bucket: str,
    s3_key: str,
    transfer_config: TransferConfig,
    max_retries: int = 5
) -> bool:
    """
    Upload file to S3 with retry logic for SSL/connection errors.
    
    Uses put_object instead of upload_file to avoid multipart SSL issues.
    
    Args:
        s3_client: Boto3 S3 client
        file_path: Local file path to upload
        bucket: S3 bucket name
        s3_key: S3 object key
        transfer_config: Transfer configuration (not used with put_object, kept for signature compatibility)
        max_retries: Maximum number of retry attempts
    
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Read file in memory (SEC files are typically 1-50 MB, acceptable)
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload with put_object (single-part, no multipart SSL issues)
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_content,
                ContentType='text/plain'
            )
            
            logger.debug(f"    ✓ Upload successful on attempt {attempt}")
            return True
            
        except (SSLError, BotoCoreError, ClientError) as e:
            error_msg = str(e)
            
            # Check if it's a retryable error
            is_retryable = (
                "SSL" in error_msg or
                "EOF occurred" in error_msg or
                "Connection was closed" in error_msg or
                "timeout" in error_msg.lower() or
                "timed out" in error_msg.lower()
            )
            
            if not is_retryable or attempt == max_retries:
                # Not retryable or final attempt - give up
                logger.error(f"    ⚠️ S3 upload failed after {attempt} attempts: {error_msg[:150]}")
                return False
            
            # Exponential backoff: 2s, 4s, 8s, 16s, 30s
            wait_time = min(2 ** attempt, 30)
            logger.warning(
                f"    ⚠️ Upload attempt {attempt}/{max_retries} failed, "
                f"retrying in {wait_time}s... (Error: {error_msg[:80]})"
            )
            time.sleep(wait_time)
        
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"    ⚠️ Unexpected error on attempt {attempt}: {str(e)[:150]}")
            if attempt == max_retries:
                return False
            time.sleep(2 ** attempt)
    
    return False


# MAIN DOWNLOAD FUNCTION
def collect_for_tickers(
    tickers: List[str],
    filing_types: List[str],
    limit_per_type: int = 1,
    after: Optional[str] = None,
) -> None:
    """
    FastAPI-friendly entrypoint.
    Router passes:
      tickers: ["CAT"]
      filing_types: ["10-K","10-Q","8-K","DEF 14A"]
      limit_per_type: 1..5
    """
    global DEFAULT_TARGET_TICKERS, DEFAULT_FILING_TYPES, FILING_TYPES, AFTER_DATE

    DEFAULT_TARGET_TICKERS = [t.upper().strip() for t in tickers if t and t.strip()]
    DEFAULT_FILING_TYPES = {ft: int(limit_per_type) for ft in filing_types}
    FILING_TYPES = list(DEFAULT_FILING_TYPES.keys())

    if after:
        AFTER_DATE = after

    main()

def main() -> None:
    """
    Download SEC filings for all target companies.
    
    Process:
    1. Load companies from Snowflake
    2. For each company:
       - Download filings from SEC EDGAR (with rate limiting)
       - Upload to S3 (with retry logic for large files)
       - Store metadata in Snowflake
    3. Track statistics and handle errors gracefully
    
    Expected output: ~140 documents (14 per company × 10 companies)
    """
    logger.info("=" * 60)
    logger.info("SEC EDGAR DOWNLOADER")
    logger.info("=" * 60)
    
    # -------------------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------------------
    
    email = require_env("SEC_EDGAR_USER_AGENT_EMAIL")
    bucket = require_env("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    logger.info(f"Email: {email}")
    logger.info(f"S3 Bucket: {bucket}")
    logger.info(f"AWS Region: {region}")
    logger.info(f"After Date: {AFTER_DATE}")
    logger.info(f"Rate Limit: {SEC_REQUEST_SLEEP_SECONDS}s between requests")
    
    # Create download directory
    download_root = Path("data/raw")
    download_root.mkdir(parents=True, exist_ok=True)
    
    # Initialize SEC downloader (handles rate limiting internally)
    dl = Downloader("OrgAIR", email, str(download_root))
    
    # Configure S3 transfer for large files (10-50 MB SEC filings)
    transfer_config = TransferConfig(
        multipart_threshold=1024 * 25,      # 25 MB (start multipart for files > 25MB)
        max_concurrency=10,                 # 10 parallel uploads
        multipart_chunksize=1024 * 25,     # 25 MB chunks
        use_threads=True,                   # Use threading
        max_io_queue=1000                   # Queue size
    )
    
    # Initialize S3 with enhanced retry configuration
    s3 = boto3.client(
        "s3",
        region_name=region,
        config=Config(
            # Retry configuration (adaptive exponential backoff)
            retries={"max_attempts": 15, "mode": "adaptive"},
            
            # Timeout configuration (large SEC files need longer timeouts)
            connect_timeout=60,              # 60 seconds to establish connection
            read_timeout=300,                # 5 minutes to read response
            
            # Connection optimization
            tcp_keepalive=True,              # Prevent connection drops
            signature_version='s3v4',        # Use signature v4
            max_pool_connections=50          # Connection pool size
        ),
    )
    
    # Initialize Snowflake service
    sf = SnowflakeService()
    
    
    # LOAD COMPANIES FROM DATABASE
   
    
    logger.info("\nFetching companies from database...")
    
    # Build dynamic IN clause with parameter substitution (SQL injection safe)
    placeholders = ",".join([f"%(t{i})s" for i in range(len(DEFAULT_TARGET_TICKERS))])
    
    company_rows = sf.execute_query(
        f"""
        SELECT id, ticker
        FROM companies
        WHERE is_deleted = FALSE
          AND UPPER(ticker) IN ({placeholders})
        """,
        {f"t{i}": DEFAULT_TARGET_TICKERS[i] for i in range(len(DEFAULT_TARGET_TICKERS))},
    )
    
    # Build ticker → company_id mapping
    ticker_to_company: dict[str, str] = {}
    for r in company_rows:
        # Handle both uppercase and lowercase column names from Snowflake
        tid = r.get("TICKER") if "TICKER" in r else r.get("ticker")
        cid = r.get("ID") if "ID" in r else r.get("id")
        ticker_to_company[str(tid).upper()] = str(cid)
    
    # Fail fast if companies are missing from database
    missing = [t for t in DEFAULT_TARGET_TICKERS if t not in ticker_to_company]
    if missing:
        raise RuntimeError(
            f"Missing companies in database: {missing}\n"
            f"Please insert these companies first using scripts/insert_companies.py"
        )
    
    logger.info(f"Found {len(ticker_to_company)} companies in database")
    

    # INITIALIZE STATISTICS TRACKING
 
    
    stats = {
        "inserted": 0,
        "skipped_dedup": 0,
        "skipped_missing_file": 0,
        "skipped_sec_download_error": 0,
        "skipped_s3_upload_error": 0,
        "skipped_invalid_folder": 0
    }
    
    run_date = date.today().isoformat()
    

    # DOWNLOAD AND PROCESS FILINGS

    
    logger.info("\nStarting downloads...")
    logger.info(f"Expected total: {sum(DEFAULT_FILING_TYPES.values()) * len(DEFAULT_TARGET_TICKERS)} documents")
    
    for ticker_idx, ticker in enumerate(DEFAULT_TARGET_TICKERS, 1):
        logger.info(f"\n[{ticker_idx}/{len(DEFAULT_TARGET_TICKERS)}] Processing {ticker}...")
        
        company_stats = {ft: 0 for ft in FILING_TYPES}
        
        for filing_type in FILING_TYPES:
            limit = DEFAULT_FILING_TYPES[filing_type]
            
            logger.info(f"  {filing_type}: Downloading up to {limit} filings...")
            
           
            # STEP 1: DOWNLOAD FROM SEC EDGAR
            
            try:
                dl.get(
                    filing_type,
                    ticker,
                    limit=limit,
                    after=AFTER_DATE
                )
                logger.info(f"  {filing_type}: Download request completed")
            except Exception as e:
                logger.error(f"   SEC download failed for {ticker} {filing_type}: {e}")
                stats["skipped_sec_download_error"] += 1
                time.sleep(SEC_REQUEST_SLEEP_SECONDS)  # Respect rate limit even on error
                continue
            
            # SEC rate limiting: wait between requests
            time.sleep(SEC_REQUEST_SLEEP_SECONDS)
            
          
            # STEP 2: FIND DOWNLOADED FILES
           
            folders = get_all_download_folders(ticker, filing_type, limit)
            
            if not folders:
                logger.warning(f"  No download folders found for {ticker} {filing_type}")
                stats["skipped_missing_file"] += 1
                continue
            
            logger.info(f"  {filing_type}: Found {len(folders)} downloaded filings")
            
                
            # STEP 3: PROCESS EACH DOWNLOADED FILING
                
            for folder_idx, folder in enumerate(folders, 1):
                try:
                    # Find main file in download folder
                    main_file = pick_main_file(folder)
                    if not main_file:
                        logger.warning(f"  No main file in {folder.name}")
                        stats["skipped_missing_file"] += 1
                        continue
                    
                    # Calculate content hash for deduplication
                    content_hash = sha256_file(main_file)
                    
                 
                    # STEP 4: CHECK FOR DUPLICATES (deduplication via content hash)
                    
                    existing = sf.execute_query(
                        f"""
                        SELECT id
                        FROM {DOCUMENTS_TABLE}
                        WHERE ticker = %(ticker)s
                          AND filing_type = %(filing_type)s
                          AND content_hash = %(content_hash)s
                        LIMIT 1
                        """,
                        {
                            "ticker": ticker,
                            "filing_type": filing_type,
                            "content_hash": content_hash
                        },
                    )
                    
                    if existing:
                        logger.debug(f"    ⏭️  Skipping duplicate: {folder.name}")
                        stats["skipped_dedup"] += 1
                        continue
                    
                    
                    # STEP 5: UPLOAD TO S3 (with retry logic for large files)
                   
                    doc_id = str(uuid4())
                    ext = main_file.suffix or ".txt"
                    ft_path = filing_type_for_paths(filing_type)
                    
                    # Build S3 key: sec/{TICKER}/{FILING_TYPE}/{DATE}/{UUID}.txt
                    s3_key = f"sec/{ticker}/{ft_path}/{run_date}/{doc_id}{ext}"
                    
                    # Upload with retry logic
                    upload_success = upload_file_with_retry(
                        s3,
                        main_file,
                        bucket,
                        s3_key,
                        transfer_config,
                        max_retries=5
                    )
                    
                    if not upload_success:
                        stats["skipped_s3_upload_error"] += 1
                        continue
                    
                   
                    # STEP 6: INSERT METADATA TO SNOWFLAKE
                  
                    source_url = build_sec_source_url(folder, main_file)
                    filing_date = extract_filing_date_from_folder(folder) or date.today()
                    
                    sf.execute_update(
                        f"""
                        INSERT INTO {DOCUMENTS_TABLE}
                          (id, company_id, ticker, filing_type, filing_date,
                           source_url, local_path, s3_key, content_hash,
                           status, created_at)
                        VALUES
                          (%(id)s, %(company_id)s, %(ticker)s, %(filing_type)s, %(filing_date)s,
                           %(source_url)s, %(local_path)s, %(s3_key)s, %(content_hash)s,
                           'downloaded', CURRENT_TIMESTAMP())
                        """,
                        {
                            "id": doc_id,
                            "company_id": ticker_to_company[ticker],
                            "ticker": ticker,
                            "filing_type": filing_type,
                            "filing_date": filing_date,
                            "source_url": source_url,
                            "local_path": str(main_file),
                            "s3_key": s3_key,
                            "content_hash": content_hash,
                        },
                    )
                    
                    stats["inserted"] += 1
                    company_stats[filing_type] += 1
                    
                    logger.info(f"   [{folder_idx}/{len(folders)}] Processed: {doc_id[:8]}...")
                    
                except Exception as e:
                    logger.error(f"   Error processing {folder.name}: {e}")
                    stats["skipped_invalid_folder"] += 1
                    continue
        
        # Print per-company summary
        total_for_company = sum(company_stats.values())
        logger.info(f"  {ticker} Summary: {total_for_company} documents")
        for ft, count in company_stats.items():
            logger.info(f"    - {ft}: {count}")
    
    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Inserted documents:        {stats['inserted']}")
    logger.info(f"⏭ Skipped (duplicate):       {stats['skipped_dedup']}")
    logger.info(f"Skipped (missing file):    {stats['skipped_missing_file']}")
    logger.info(f" Skipped (SEC error):       {stats['skipped_sec_download_error']}")
    logger.info(f"Skipped (S3 error):        {stats['skipped_s3_upload_error']}")
    logger.info(f"Skipped (invalid folder):  {stats['skipped_invalid_folder']}")
    logger.info("=" * 60)
    
    expected = sum(DEFAULT_FILING_TYPES.values()) * len(DEFAULT_TARGET_TICKERS)
    logger.info(f"\nExpected: ~{expected} documents")
    logger.info(f"Actual:    {stats['inserted']} documents")
    
    if stats['inserted'] >= 90:
        logger.info("SUCCESS: Downloaded 90+ documents!")
    else:
        logger.warning(f"  WARNING: Only {stats['inserted']} documents (target: 90+)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n Interrupted by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}", exc_info=True)
        raise