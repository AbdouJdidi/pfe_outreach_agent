# PFE Outreach Agent — V1

Local-first PFE company discovery + qualification agent.

Priority:
1. International companies
2. International startups
3. Sousse companies
4. Sousse startups
5. Tunis companies
6. Tunis startups

Domains: Cloud, DevOps, AI, Software Engineering.

## Setup (Windows PowerShell)
```powershell
cd pfe_outreach_agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
ollama list
python -m src.main llm-test
```

Set `OLLAMA_MODEL` in `.env` to the exact Qwen model you have installed. The default is `qwen3:4b`.

Then:
```powershell
python -m src.main discover
python -m src.main analyze
python -m src.main report
```

`all` runs the complete V1 pipeline:
```powershell
python -m src.main all
```

V1 does NOT send email. It discovers, researches, scores, and ranks companies locally. Contact discovery, personalized emails, approval, Gmail sending, and follow-up tracking come next.
