import json
import re

import requests

from .config import settings
from .db import (
    connect,
    get_contacts,
    save_outreach,
)


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_company_context(company_id):
    with connect() as c:
        row = c.execute("""
            SELECT
                c.id,
                c.name,
                c.website,
                c.location,
                c.description,
                c.fetched_text,
                a.domains,
                a.raw_json
            FROM companies c
            LEFT JOIN analyses a
                ON a.company_id = c.id
            WHERE c.id = ?
        """, (company_id,)).fetchone()

        return row


def choose_contacts(limit=100):
    contacts = get_contacts(limit)

    selected = []

    for contact in contacts:
        email = contact["email"].lower()
        contact_type = contact["contact_type"]

        # Highest priority: recruitment / internship channels
        if contact_type in {
            "careers",
            "jobs",
            "recruiting",
            "hr",
        }:
            selected.append(contact)
            continue

        # Personal employee email found on a career/internship page.
        source = (contact["source_url"] or "").lower()

        if (
            contact_type == "other"
            and any(
                keyword in source
                for keyword in [
                    "career",
                    "internship",
                    "jobs",
                    "recruit",
                ]
            )
        ):
            selected.append(contact)
            continue

        # Generic contact only as fallback.
        if contact_type == "contact":
            selected.append(contact)

    # Deduplicate company + email.
    result = []
    seen = set()

    for contact in selected:
        key = (
            contact["company_id"],
            contact["email"].lower(),
        )

        if key not in seen:
            result.append(contact)
            seen.add(key)

    return result


def build_company_evidence(company):
    text = company["fetched_text"] or ""

    # Keep enough context for personalization,
    # but don't send 30k chars to Qwen.
    text = clean_text(text)[:10000]

    domains = []

    if company["domains"]:
        try:
            domains = json.loads(company["domains"])
        except Exception:
            domains = []

    return {
        "name": company["name"],
        "website": company["website"],
        "location": company["location"],
        "domains": domains,
        "website_evidence": text,
    }


def generate_email(company, contact):
    evidence = build_company_evidence(company)

    prompt = f"""
You are writing a professional cold email for a final-year
software engineering student applying for a 6-month PFE
(final-year graduation internship).

Candidate profile:

- Final-year software engineering student at FST Tunisia
- Looking for a 6-month PFE
- Main interests: Cloud, DevOps, AI and Software Engineering
- AWS Solutions Architect – Associate
- Experience with Docker, CI/CD, GCP, Linux
- Backend development with Node.js and Python
- Software engineering experience
- Based in Tunisia
- Available for a 6-month final-year internship

Company:

Name: {evidence["name"]}
Website: {evidence["website"]}
Location: {evidence["location"]}
Technical domains: {evidence["domains"]}

Website evidence:
{evidence["website_evidence"]}

Contact:
{contact["email"]}

Contact type:
{contact["contact_type"]}

Contact source:
{contact["source_url"]}

TASK:

Write ONE concise personalized PFE application email.

Requirements:

1. Mention the company by name.
2. Mention ONE or TWO specific things from the website evidence
   that genuinely connect to the candidate's Cloud/DevOps/AI/
   Software Engineering interests.
3. Clearly ask about a 6-month PFE opportunity.
4. Do not claim that the company offers internships unless
   the evidence explicitly shows it.
5. If the contact is a generic careers/jobs/contact address,
   address the company/team naturally rather than inventing
   a person's name.
6. If the contact is clearly a person's email, do not invent
   their job title.
7. Keep the email concise: approximately 150-200 words.
8. Natural professional English.
9. No exaggerated praise.
10. Do not say "I am passionate" repeatedly.
11. Do not mention that an AI generated the email.
12. Do not invent technologies or projects not present in the
    candidate profile or company evidence.

Return ONLY valid JSON:

{{
  "subject": "...",
  "body": "..."
}}
"""

    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096,
                },
            },
            timeout=180,
        )

        response.raise_for_status()

        raw = response.json().get(
            "response",
            "",
        )

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                raw,
                re.DOTALL,
            )

            if match:
                return json.loads(match.group(0))

    except Exception as e:
        print(f"   ⚠ email generation failed: {e}")

    return None


def generate_outreach():
    contacts = choose_contacts()

    if not contacts:
        print("No suitable contacts found.")
        return

    print(
        f"Found {len(contacts)} outreach contacts."
    )

    generated = 0

    for contact in contacts:

        company = get_company_context(
            contact["company_id"]
        )

        if not company:
            continue

        print(
            f"\n✉️  {company['name']}"
        )

        print(
            f"   → {contact['email']}"
        )

        result = generate_email(
            company,
            contact,
        )

        if not result:
            print(
                "   ❌ could not generate email"
            )
            continue

        subject = result.get(
            "subject",
            "",
        ).strip()

        body = result.get(
            "body",
            "",
        ).strip()

        if not subject or not body:
            print(
                "   ❌ invalid email returned"
            )
            continue

        save_outreach(
            company_id=company["id"],
            contact_id=contact["id"],
            subject=subject,
            body=body,
        )

        generated += 1

        print(
            f"   ✓ draft generated"
        )

    print("\n" + "=" * 60)
    print(
        f"Generated {generated} outreach drafts."
    )
    print("=" * 60)


def show_outreach():
    from .db import get_outreach

    rows = get_outreach()

    if not rows:
        print("No outreach drafts found.")
        return

    for i, row in enumerate(rows, 1):

        print("\n" + "=" * 80)

        print(
            f"{i}. {row['name']}"
        )

        print(
            f"To: {row['email']}"
        )

        print(
            f"Subject: {row['subject']}"
        )

        print("-" * 80)

        print(row["body"])

        print("-" * 80)

        print(
            f"Status: {row['status']}"
        )


if __name__ == "__main__":
    generate_outreach()