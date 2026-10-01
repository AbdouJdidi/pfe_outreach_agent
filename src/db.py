import sqlite3
from pathlib import Path
import json

DB_PATH = Path("data/pfe_agent.db")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,
            domain TEXT UNIQUE NOT NULL,
            website TEXT,

            location TEXT,
            company_type TEXT,

            description TEXT,

            source TEXT,
            source_url TEXT,

            raw_text TEXT,
            fetched_text TEXT,

            verified INTEGER DEFAULT 0,
            discovery_score INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS analyses (
            company_id INTEGER PRIMARY KEY,

            score INTEGER,
            priority TEXT,

            domains TEXT,

            remote_compatible INTEGER,
            pfe_potential TEXT,

            reasoning TEXT,
            raw_json TEXT,

            analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_companies_domain
        ON companies(domain);

        CREATE INDEX IF NOT EXISTS idx_companies_verified
        ON companies(verified);

        CREATE INDEX IF NOT EXISTS idx_analyses_score
        ON analyses(score);
        """)


def upsert_company(x):
    with connect() as c:
        c.execute("""
            INSERT INTO companies (
                name,
                domain,
                website,
                location,
                company_type,
                description,
                source,
                source_url,
                raw_text,
                verified,
                discovery_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(domain) DO UPDATE SET

                name = CASE
                    WHEN excluded.name IS NOT NULL
                    AND excluded.name != ''
                    THEN excluded.name
                    ELSE companies.name
                END,

                website = COALESCE(
                    excluded.website,
                    companies.website
                ),

                location = COALESCE(
                    excluded.location,
                    companies.location
                ),

                company_type = COALESCE(
                    excluded.company_type,
                    companies.company_type
                ),

                description = COALESCE(
                    excluded.description,
                    companies.description
                ),

                source = COALESCE(
                    excluded.source,
                    companies.source
                ),

                source_url = COALESCE(
                    excluded.source_url,
                    companies.source_url
                ),

                raw_text = COALESCE(
                    excluded.raw_text,
                    companies.raw_text
                ),

                verified = MAX(
                    companies.verified,
                    excluded.verified
                ),

                discovery_score = MAX(
                    companies.discovery_score,
                    excluded.discovery_score
                ),

                updated_at = CURRENT_TIMESTAMP
        """, (
            x.get("name"),
            x.get("domain"),
            x.get("website"),
            x.get("location"),
            x.get("company_type"),
            x.get("description"),
            x.get("source"),
            x.get("source_url"),
            x.get("raw_text"),
            int(x.get("verified", 0)),
            int(x.get("discovery_score", 0)),
        ))


def get_unanalyzed(limit=100):
    with connect() as c:
        return c.execute("""
            SELECT c.*
            FROM companies c
            LEFT JOIN analyses a
                ON a.company_id = c.id

            WHERE a.company_id IS NULL
              AND c.verified = 1

            ORDER BY c.discovery_score DESC, c.id

            LIMIT ?
        """, (limit,)).fetchall()


def save_fetched_text(cid, text):
    with connect() as c:
        c.execute("""
            UPDATE companies
            SET fetched_text = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (text[:30000], cid))


def save_analysis(cid, r):
    with connect() as c:
        c.execute("""
            INSERT INTO analyses (
                company_id,
                score,
                priority,
                domains,
                remote_compatible,
                pfe_potential,
                reasoning,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(company_id) DO UPDATE SET

                score = excluded.score,
                priority = excluded.priority,
                domains = excluded.domains,
                remote_compatible = excluded.remote_compatible,
                pfe_potential = excluded.pfe_potential,
                reasoning = excluded.reasoning,
                raw_json = excluded.raw_json,
                analyzed_at = CURRENT_TIMESTAMP
        """, (
            cid,
            r["score"],
            r["priority"],
            json.dumps(r["domains"], ensure_ascii=False),
            int(r["remote_compatible"]),
            r["pfe_potential"],
            r["reasoning"],
            json.dumps(r, ensure_ascii=False),
        ))


def ranked(limit=50):
    with connect() as c:
        return c.execute("""
            SELECT
                c.name,
                c.domain,
                c.website,
                c.location,
                c.company_type,
                c.source,
                c.verified,
                c.discovery_score,

                a.score,
                a.priority,
                a.domains,
                a.remote_compatible,
                a.pfe_potential,
                a.reasoning

            FROM companies c

            JOIN analyses a
                ON a.company_id = c.id

            ORDER BY a.score DESC

            LIMIT ?
        """, (limit,)).fetchall()


def stats():
    with connect() as c:
        companies = c.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()[0]

        verified = c.execute(
            "SELECT COUNT(*) FROM companies WHERE verified = 1"
        ).fetchone()[0]

        analyzed = c.execute(
            "SELECT COUNT(*) FROM analyses"
        ).fetchone()[0]

        return {
            "companies": companies,
            "verified": verified,
            "analyzed": analyzed,
        }