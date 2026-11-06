"""PDF/image ingestion and CLIP visual + lexical reciprocal-rank retrieval."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import numpy as np

MODEL='openai/clip-vit-base-patch32'
REVISION='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'

def words(text):return re.findall(r'[a-z0-9]+',text.lower())

def lexical_scores(pages,query):
 counts=[Counter(words(p['text'])) for p in pages]
 vocab=sorted(set().union(*(set(c) for c in counts)))
 if not vocab:return np.zeros(len(pages))
 idf=np.array([np.log((1+len(pages))/(1+sum(w in c for c in counts)))+1 for w in vocab])
 def vec(count):
  v=np.array([count[w] for w in vocab])*idf;n=np.linalg.norm(v)
  return v/n if n else v
 return np.array([vec(c) for c in counts])@vec(Counter(words(query)))

def rank(lexical,visual,mode='hybrid'):
 if mode not in ['text','visual','hybrid']:raise ValueError('Invalid retrieval mode')
 if len(lexical)!=len(visual) or not len(lexical):raise ValueError('Invalid score dimensions')
 if mode=='text':return np.argsort(-np.asarray(lexical),kind='stable').tolist()
 if mode=='visual':return np.argsort(-np.asarray(visual),kind='stable').tolist()
 score=np.zeros(len(lexical))
 for values in [lexical,visual]:
  # An empty lexical query contributes no artificial tie-order preference.
  if np.allclose(values,0):continue
  for position,index in enumerate(np.argsort(-np.asarray(values),kind='stable')):score[index]+=1/(60+position+1)
 return np.argsort(-score,kind='stable').tolist()

def clip():
 import torch
 from transformers import CLIPModel,CLIPProcessor
 torch.set_num_threads(2)
 return CLIPModel.from_pretrained(MODEL,revision=REVISION).eval(),CLIPProcessor.from_pretrained(MODEL,revision=REVISION)

def ingest(source,index_dir):
 import pymupdf
 from PIL import Image
 import torch
 index_dir=Path(index_dir);index_dir.mkdir(parents=True,exist_ok=True)
 source=Path(source).resolve();pages=[];images=[]
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 if source.suffix.lower()=='.pdf':
  with pymupdf.open(source) as document:
   if not 1<=len(document)<=50:raise ValueError('PDF must contain 1–50 pages')
   for number,page in enumerate(document):
    image_name=f'page-{number+1}.png';page.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(str(index_dir/image_name))
    tables=[]
    for table in page.find_tables().tables:tables.append({'bbox':list(table.bbox),'rows':table.extract()})
    pages.append({'page':number+1,'text':page.get_text(),'image':image_name,'tables':tables,'width':page.rect.width,'height':page.rect.height,'words':[list(w[:5]) for w in page.get_text('words')]})
    images.append(Image.open(index_dir/image_name).convert('RGB'))
 else:
  with Image.open(source) as image:
   image.convert('RGB').save(index_dir/'page-1.png')
  images=[Image.open(index_dir/'page-1.png').convert('RGB')]
  pages=[{'page':1,'text':'','image':'page-1.png','tables':[]}]
 model,processor=clip()
 with torch.inference_mode():
  # Full forward uses the model's normalized image embeddings consistently across versions.
  outputs=model(**processor(text=['document page'],images=images,return_tensors='pt',padding=True))
  embeddings=outputs.image_embeds.cpu().numpy()
 np.save(index_dir/'images.npy',embeddings)
 manifest={'source_name':source.name,'source_sha256':digest,'model':MODEL,'revision':REVISION,'pages':pages}
 (index_dir/'manifest.json').write_text(json.dumps(manifest,indent=2))
 return manifest

def search(index_dir,query,mode='hybrid',top_k=2,loaded=None):
 import torch
 index_dir=Path(index_dir);manifest=json.loads((index_dir/'manifest.json').read_text());pages=manifest['pages']
 if not query.strip() or len(query)>1000:raise ValueError('Question must contain 1–1000 characters')
 model,processor=loaded or clip()
 # Use the text tower directly; CLIP text is deliberately truncated to its 77-token capacity.
 with torch.inference_mode():
  inputs=processor(text=[query],return_tensors='pt',padding=True,truncation=True)
  text=model.get_text_features(**inputs)
  if not isinstance(text,torch.Tensor):text=text.pooler_output
  text=text/text.norm(dim=-1,keepdim=True)
 visual=(np.load(index_dir/'images.npy')@text.cpu().numpy().T).ravel()
 lexical=lexical_scores(pages,query)
 order=rank(lexical,visual,mode)[:top_k]
 return [dict(pages[i],visual_score=round(float(visual[i]),4),lexical_score=round(float(lexical[i]),4),citation=f"{manifest['source_name']}#page={pages[i]['page']}") for i in order]

def report(index_dir,query,results,target):
 import base64
 index_dir=Path(index_dir)
 parts=[]
 for p in results:
  encoded=base64.b64encode((index_dir/p['image']).read_bytes()).decode()
  # Embedded source page plus safely escaped extracted evidence. No generated factual answer.
  highlights=''
  query_words={w for w in words(query) if len(w)>3}
  for x0,y0,x1,y1,word in p.get('words',[]):
   if set(words(word)) & query_words:
    highlights+=f'<span aria-hidden="true" style="position:absolute;background:#fff00055;border:1px solid #eaca26;left:{100*x0/p["width"]:.3f}%;top:{100*y0/p["height"]:.3f}%;width:{100*(x1-x0)/p["width"]:.3f}%;height:{100*(y1-y0)/p["height"]:.3f}%"></span>'
  parts.append(f'<article><h2>Page {p["page"]} · {html.escape(p["citation"])}</h2><p>Visual: {p["visual_score"]} · Lexical: {p["lexical_score"]}</p><div style="position:relative;max-width:550px"><img style="display:block;width:100%" alt="Source page {p["page"]}" src="data:image/png;base64,{encoded}">{highlights}</div><pre>{html.escape(p["text"]) or "Image-only page: inspect the visual evidence."}</pre></article>')
 Path(target).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Document evidence</title><style>body{font:16px system-ui;background:#101b19;color:#e4ede5;max-width:1000px;margin:40px auto;padding:20px}h1{color:#c8f580}article{border-top:1px solid #607568;padding:25px 0}img{max-width:100%;width:550px}pre{white-space:pre-wrap;line-height:1.6}</style><h1>'+html.escape(query)+'</h1><p>Retrieved source evidence. Yellow highlights mark query-word matches, not verified answer spans. No generative answering or chart arithmetic is performed.</p>'+''.join(parts)+'</html>')

if __name__=='__main__':
 parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
 create=sub.add_parser('index');create.add_argument('source');create.add_argument('--output',default='local-index')
 query=sub.add_parser('query');query.add_argument('question');query.add_argument('--index',default='local-index');query.add_argument('--mode',choices=['text','visual','hybrid'],default='hybrid');query.add_argument('--report',default='reports/evidence.html')
 args=parser.parse_args()
 if args.command=='index':print(json.dumps(ingest(args.source,args.output),indent=2))
 else:
  result=search(args.index,args.question,args.mode);report(args.index,args.question,result,args.report);print(json.dumps(result,indent=2))
