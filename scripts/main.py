"""
ETL Pipeline CLI - Main entry point for end-to-end ETL workflow

Usage:
    python scripts/main.py import data/albums.xlsx
    python scripts/main.py import data/albums.xlsx --enrich --db
    python scripts/main.py import data/albums.xlsx --validate-only
    python scripts/main.py search --artist "Pink Floyd"
    python scripts/main.py search --title "The Wall"
    python scripts/main.py stats
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.importer import import_excel, import_csv
from etl.normalizer import normalize_record, validate_records
from etl.api_fetcher import fetch_discogs_batch
from etl.merge import merge_records
from etl.queries import search_cds_by_artist, search_cds_by_title, get_all_cds, count_cds
from app.db.database import SessionLocal
from app.db.manager import insert_cds_batch
from app.db.init_db import reset_db, clear_all_records

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_import(args):
    """Import Excel/CSV file into DB"""
    file_path = args.file
    
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        return 1
    
    try:
        logger.info(f"Starting import from: {file_path}")
        
        # Step 1: Import
        if file_path.endswith('.csv'):
            raw_records = import_csv(file_path)
        elif file_path.endswith('.xlsx'):
            raw_records = import_excel(file_path)
        else:
            raise ValueError(f"{file_path} contains unsupported file format. Use .csv or .xlsx")
        
        logger.info(f"✅ Imported {len(raw_records)} records")
        
        # Step 2: Normalize
        normalized_records = [normalize_record(r) for r in raw_records]
        logger.info(f"✅ Normalized {len(normalized_records)} records")
        
        # Step 3: Validate
        if args.validate_only:
            valid, invalid = validate_records(normalized_records)
            logger.info(f"Validation results: {len(valid)} valid, {len(invalid)} invalid")
            if invalid:
                logger.warning("Invalid records:")
                for item in invalid:
                    logger.warning(f"  {item['record']}: {item['errors']}")
            return 0
        
        valid_records, invalid_records = validate_records(normalized_records)
        
        if not valid_records:
            logger.error("No valid records to import")
            return 1
        
        logger.info(f"✅ Validated {len(valid_records)} records")
        
        # Step 4: Enrich (optional)
        if args.enrich:
            logger.info("Enriching records via Discogs API...")
            enriched_records = fetch_discogs_batch(valid_records, delay=1.0)
            merged_records = merge_records(valid_records, enriched_records, source_priority="enriched")
            logger.info(f"✅ Enriched {len(merged_records)} records")
        else:
            merged_records = valid_records
        
        # Step 5: Insert to DB (optional)
        if args.db:
            logger.info("Inserting records to database...")
            db = SessionLocal()
            inserted = insert_cds_batch(db, merged_records)
            db.close()
            logger.info(f"✅ Inserted {inserted} records to database")
        else:
            logger.info("Skipping DB insert (use --db to insert)")
            logger.info(f"Would insert {len(merged_records)} records")
        
        logger.info("✅ Import completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error during import: {e}", exc_info=True)
        return 1


def cmd_search(args):
    """Search database for CDs"""
    db = SessionLocal()
    
    try:
        if args.artist:
            logger.info(f"Searching by artist: {args.artist}")
            results = search_cds_by_artist(db, args.artist)
        elif args.title:
            logger.info(f"Searching by title: {args.title}")
            results = search_cds_by_title(db, args.title)
        else:
            logger.error("Specify --artist or --title")
            return 1
        
        if not results:
            logger.info("No results found")
            return 0
        
        logger.info(f"Found {len(results)} result(s):")
        for cd in results:
            logger.info(f"  {cd.artist} - {cd.title} ({cd.year})")
        
        return 0
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()


def cmd_stats(args):
    """Show collection statistics"""
    db = SessionLocal()
    
    try:
        total = count_cds(db)
        all_cds = get_all_cds(db)
        
        logger.info("=== Collection Statistics ===")
        logger.info(f"Total CDs: {total}")
        
        if all_cds:
            # Group by artist
            artists = {}
            max_items = args.max if args.max else 10
            logger.info(f"View top {max_items} collections")
            for i, cd in enumerate(all_cds, 1):
                if i <= max_items:
                    logger.info(f"{i}:  {cd.artist} - {cd.title} ({cd.year})")
                if cd.artist not in artists:
                    artists[cd.artist] = 0
                artists[cd.artist] += 1
            
            logger.info(f"Total artists: {len(artists)}")
            # Top artists
            top_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("Top 5 artists:")
            for artist, count in top_artists:
                logger.info(f"  {artist}: {count} CD(s)")
        
        return 0
    
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()


def cmd_reset(args):
    """Reset or manage database"""
    try:
        if args.full:
            logger.warning("⚠️  Full database reset requested")
            confirm = input("This will delete all data. Type 'yes' to confirm: ")
            if confirm.lower() != "yes":
                logger.info("Reset cancelled")
                return 0
            reset_db()
            logger.info("✅ Full reset complete")
            return 0
        
        elif args.clear:
            logger.warning("⚠️  Clearing all records")
            confirm = input("This will delete all CD records. Type 'yes' to confirm: ")
            if confirm.lower() != "yes":
                logger.info("Clear cancelled")
                return 0
            deleted = clear_all_records()
            logger.info(f"✅ Cleared {deleted} records")
            return 0
        
        elif args.count:
            db = SessionLocal()
            try:
                count = count_cds(db)
                logger.info(f"📊 Database contains {count} CD record(s)")
                return 0
            finally:
                db.close()
        
        else:
            logger.error("Specify --full, --clear, or --count")
            return 1
    
    except Exception as e:
        logger.error(f"Reset error: {e}", exc_info=True)
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CD Collection ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import and validate
  python scripts/main.py import data/albums.xlsx --validate-only
  
  # Import, enrich, and save to DB
  python scripts/main.py import data/albums.xlsx --enrich --db
  
  # Search database
  python scripts/main.py search --artist "Pink Floyd"
  python scripts/main.py search --title "Dark Side"
  
  # Show stats
  python scripts/main.py stats
  
  # Reset database
  python scripts/main.py reset --count
  python scripts/main.py reset --clear
  python scripts/main.py reset --full
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import CD data from Excel/CSV")
    import_parser.add_argument("file", help="Path to Excel or CSV file")
    import_parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich data via Discogs API (requires DISCOGS_TOKEN)"
    )
    import_parser.add_argument(
        "--db",
        action="store_true",
        help="Insert records into database"
    )
    import_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't import"
    )
    import_parser.set_defaults(func=cmd_import)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search database")
    search_parser.add_argument("--artist", help="Search by artist name")
    search_parser.add_argument("--title", help="Search by album title")
    search_parser.set_defaults(func=cmd_search)
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show collection statistics")
    stats_parser.add_argument(
        "--max",
        type=int,
        help="max items to show"
    )
    stats_parser.set_defaults(func=cmd_stats)
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset or manage database")
    reset_group = reset_parser.add_mutually_exclusive_group()
    reset_group.add_argument(
        "--full",
        action="store_true",
        help="Full reset: drop and recreate all tables (requires confirmation)"
    )
    reset_group.add_argument(
        "--clear",
        action="store_true",
        help="Clear all records but keep table structure (requires confirmation)"
    )
    reset_group.add_argument(
        "--count",
        action="store_true",
        help="Show current record count"
    )
    reset_parser.set_defaults(func=cmd_reset)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
