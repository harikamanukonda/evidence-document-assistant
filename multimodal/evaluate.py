"""Compare page retrieval modes on a small transparent fixture."""
import json
from pathlib import Path
import time
from multimodal.index import clip,search,report
ROOT=Path(__file__).resolve().parents[1]
CASES=[('Which region has the highest on-time delivery rate?',1),('How many orders did the South region process?',1),('Which month had the highest electricity usage?',2),('A bar chart showing monthly energy consumption',2),('How quickly must severity-one alerts be acknowledged?',3),('How long are application logs retained?',3)]
if __name__=='__main__':
 loaded=clip();rows=[]
 for mode in ['text','visual','hybrid']:
  for question,page in CASES:
   start=time.perf_counter();results=search(ROOT/'local-index',question,mode,top_k=3,loaded=loaded)
   position=next(i+1 for i,p in enumerate(results) if p['page']==page)
   rows.append({'mode':mode,'question':question,'expected_page':page,'retrieved_page':results[0]['page'],'reciprocal_rank':1/position,'latency_seconds':time.perf_counter()-start})
 aggregate={mode:{'recall_at_1':sum(r['retrieved_page']==r['expected_page'] for r in rows if r['mode']==mode)/len(CASES),'mrr':sum(r['reciprocal_rank'] for r in rows if r['mode']==mode)/len(CASES)} for mode in ['text','visual','hybrid']}
 result={'aggregate':aggregate,'rows':rows,'limitations':['Six hand-written questions over a fictional three-page report.','CLIP is a general image-text retriever, not a document OCR model; small text and numeric reasoning are weak points.','No generated-answer accuracy claim; this evaluates page retrieval only.']}
 (ROOT/'reports/multimodal-evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
 question=CASES[0][0];results=search(ROOT/'local-index',question,'hybrid',loaded=loaded)
 report(ROOT/'local-index',question,results,ROOT/'reports/multimodal-evidence.html')
 print(json.dumps(aggregate,indent=2))
