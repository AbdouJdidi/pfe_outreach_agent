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
You are writing a real PFE application email for Abderrahmen Jedidi.

The email must sound like a genuine personal application, similar to an
email a strong final-year engineering student would send directly to a
company. It must NOT sound like a generic cold-email template.

====================
CANDIDATE
====================

Name: Abderrahmen Jedidi

Education:
- Final-year software engineering student
- Faculty of Sciences of Tunis (FST), Tunisia

PFE:
- 6-month graduation internship
- START DATE: February 2027
- This date is fixed.
- NEVER use July, October, January, "immediately", "early October",
  "early July", or any other starting date.

Internship experience:
- Satoripop — DevOps / Cloud
- Tunisie Telecom — Software / Full-Stack Engineering
- VISIOAD — Software Engineering / DevOps / AI-related work
- Dot-IT — Software Engineering / Full-Stack Development

Other experience:
- Freelance software development
- Experience building solutions around real client requirements

Technical interests:
- Cloud
- DevOps
- Applied AI
- Software Engineering
- Backend development

Technical background:
- AWS
- Docker
- CI/CD
- GCP
- Linux
- Node.js
- Python

Certifications:
- AWS Certified Solutions Architect – Associate
- AWS Certified Cloud Practitioner

Personal project:
- ClipForge
- AI-powered clipping agent
- Automates parts of the content-production workflow
- Designed to operate with minimal supervision

Phone:
+216 53 158 628

====================
COMPANY
====================

Name: {evidence["name"]}
Website: {evidence["website"]}
Location: {evidence["location"]}
Technical domains: {evidence["domains"]}

Website evidence:
{evidence["website_evidence"]}

====================
CONTACT
====================

Email: {contact["email"]}
Contact type: {contact["contact_type"]}
Source: {contact["source_url"]}

====================
EMAIL STRUCTURE
====================

Write the email using this general structure:

1. Greeting.

2. Opening:
   Introduce Abderrahmen as a final-year software engineering student
   at FST Tunisia and clearly state that he is applying for a
   6-month PFE starting in February 2027.

3. Experience paragraph:
   Briefly mention the four internships at Satoripop, Tunisie Telecom,
   VISIOAD and Dot-IT.

   Do NOT describe every internship in detail.
   The goal is to establish that the candidate already has practical
   professional experience.

4. Additional profile paragraph:
   Mention freelance software development experience.

   Mention ClipForge as an example of the candidate's initiative and
   applied AI interest.

5. Certifications:
   Mention the AWS Certified Solutions Architect – Associate and
   AWS Certified Cloud Practitioner certifications.

6. COMPANY-SPECIFIC PARAGRAPH:
   This is the most important paragraph.

   Explain what specifically interests the candidate about THIS company.

   Use ONE or TWO concrete facts from the website evidence.

   Connect those facts to the candidate's actual background and
   interests.

   Examples:
   - AI company → emphasize ClipForge + applied AI + software engineering
   - Cloud/DevOps company → emphasize AWS + Docker + CI/CD + cloud experience
   - Software agency → emphasize internships + backend/full-stack + freelance work
   - Mixed company → combine only the most relevant parts

7. Closing:
   Clearly say that the candidate would welcome the opportunity to
   contribute as a PFE intern and discuss whether there is an opportunity
   within the company.

8. Say that the CV is attached.

9. Sign:

Best regards,

Abderrahmen Jedidi
+216 53 158 628

====================
IMPORTANT RULES
====================

- The PFE starts in February 2027. This is NON-NEGOTIABLE.
- NEVER invent another start date.
- NEVER say "available immediately".
- NEVER say "available to start".
- Do not invent an internship program.
- We are proactively asking whether the company would consider a PFE.
- Do not claim that the company currently has a PFE opening unless the
  website evidence explicitly says so.
- Do not invent technologies used by the company.
- Do not invent technologies used by the candidate.
- Do not claim the candidate used Kubernetes unless it is explicitly
  present in the candidate profile above.
- Do not invent company projects.
- Only use company-specific facts supported by the website evidence.
- Do not mention every technical skill just to fill space.
- Keep the email around 230-300 words.
- Professional but natural English.
- Confident but not arrogant.
- No exaggerated praise.
- No "dream company".
- No "perfect fit".
- No "I am extremely passionate".
- No generic corporate fluff.
- Do not sound like an automated outreach campaign.
- Do not mention AI generation.
- Do not use placeholders.
- Do not use "[Your Name]", "[Company]", "[Month]", etc.

GREETING:

For jobs@, careers@, contact@ or another generic company address:
"Dear [Company] Team,"

For a clearly identifiable person:
"Dear Mr. [Surname],"
or
"Dear Ms. [Surname],"

Do not invent a person's name.

SUBJECT:

Create a natural subject based on the company and relevant technical
area.

Examples:
"PFE Application – Cloud & DevOps – February 2027"
"PFE Application – Software Engineering & AI – February 2027"
"PFE Application – Software Engineering – February 2027"

Do not use the exact same subject for every company.

====================
RETURN FORMAT
====================

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

        raw = response.json().get("response", "")

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
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