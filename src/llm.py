import json,requests
from pydantic import BaseModel,Field
from .config import settings
class CompanyAnalysis(BaseModel):
    score:int=Field(ge=0,le=100); priority:str; domains:list[str]; remote_compatible:bool; pfe_potential:str; reasoning:str
def ask_qwen(company):
    prompt=f'''You are a recruiting research assistant. Candidate: {settings.candidate_profile}
Company: {company.get('name')} | {company.get('website')} | {company.get('location')} | {company.get('company_type')}
Description: {company.get('description')}
Website/careers evidence: {(company.get('fetched_text') or '')[:18000]}
Analyze ONLY evidence. Do not invent. Return JSON only: {{"score":0,"priority":"HIGH|MEDIUM|LOW","domains":[],"remote_compatible":true,"pfe_potential":"high|medium|low|unknown","reasoning":"short factual explanation"}}
Technical fit: Cloud/DevOps/AI/software. PFE potential requires evidence; senior hiring alone is not proof of a PFE. If remote restrictions exclude Tunisia, say so. Priority order: international companies, international startups, Sousse companies/startups, Tunis companies/startups.'''
    r=requests.post(settings.ollama_base_url.rstrip('/')+'/api/generate',json={'model':settings.ollama_model,'prompt':prompt,'stream':False,'format':'json','options':{'temperature':0.1,'num_ctx':4096}},timeout=600); r.raise_for_status()
    return CompanyAnalysis.model_validate(json.loads(r.json()['response']))
def test(): print(ask_qwen({'name':'Example Cloud Company','website':'https://example.com','location':'Remote / Europe','company_type':'company','description':'AWS Kubernetes cloud platform','fetched_text':'Engineering careers page; remote engineering team.'}).model_dump_json(indent=2))
