from .config import settings
from .db import get_unanalyzed,save_analysis
from .research import research_company
from .llm import ask_qwen
def analyze():
    rows=get_unanalyzed(settings.analyze_limit)
    if not rows: print('Nothing to analyze.'); return
    for row in rows:
        print('\n🧠',row['name']); fetched=row['fetched_text'] or ''
        if not fetched:
            try: fetched=research_company(row['id'],row['website'])
            except Exception as e: print('  ⚠ research failed:',e)
        try:
            result=ask_qwen({**dict(row),'fetched_text':fetched}); save_analysis(row['id'],result.model_dump()); print(f'  → {result.score}/100 | {result.priority} | {result.pfe_potential}')
        except Exception as e: print('  ❌ Qwen failed:',e)
