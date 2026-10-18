"""Carga de lectura controlada; requiere cookie temporal local NO versionada."""
import argparse,json,statistics,time,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

def percentile(values,p):
 ordered=sorted(values);return ordered[min(len(ordered)-1,int((len(ordered)-1)*p))] if ordered else 0

def run(base,cookie,paths,concurrency,duration):
 deadline=time.monotonic()+duration;rows=[];lock=threading.Lock()
 def worker(index):
  session=requests.Session();session.cookies.set('sessionid',cookie)
  local=[];n=index
  while time.monotonic()<deadline:
   path=paths[n%len(paths)];n+=1;start=time.monotonic()
   try:
    response=session.get(base+path,timeout=5,allow_redirects=False)
    status=response.status_code
   except requests.RequestException:status=0
   local.append((1000*(time.monotonic()-start),status))
  with lock:rows.extend(local)
 start=time.monotonic()
 with ThreadPoolExecutor(max_workers=concurrency) as pool:list(pool.map(worker,range(concurrency)))
 elapsed=time.monotonic()-start;latencies=[r[0] for r in rows];errors=sum(status!=200 for _,status in rows)
 return {'concurrency':concurrency,'duration_s':round(elapsed,3),'requests':len(rows),'rps':round(len(rows)/elapsed,2),'mean_ms':round(statistics.mean(latencies),2),'p95_ms':round(percentile(latencies,.95),2),'errors':errors,'error_percent':round(100*errors/max(1,len(rows)),2),'status_codes':sorted(set(s for _,s in rows))}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--session-file',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 cookie=json.loads(args.session_file.read_text())['root'];paths=['/','/mantenedores/delegaciones/','/mantenedores/usuarios/','/mantenedores/roles/','/mantenedores/metas/','/mantenedores/tipos-atencion/','/mantenedores/sub-atenciones/']
 results=[]
 for level in [1,3,5,10]:
  result=run(args.base,cookie,paths,level,10);results.append(result);print(json.dumps(result),flush=True)
  if result['error_percent']>5 or result['p95_ms']>2000:break
 session=requests.Session();session.cookies.set('sessionid',cookie);recovery=[]
 for _ in range(20):
  start=time.monotonic();r=session.get(args.base+'/',timeout=5,allow_redirects=False);recovery.append((1000*(time.monotonic()-start),r.status_code))
 final={'environment':args.base,'date':'2026-10-18','tool':'Python requests / ThreadPoolExecutor','scenario':'GET autenticados de dashboard y seis mantenedores; sin escrituras de negocio','thresholds':{'p95_ms':1500,'errors_percent_below':1,'stop_errors_percent':5,'stop_p95_ms':2000},'levels':results,'recovery':{'requests':len(recovery),'errors':sum(s!=200 for _,s in recovery),'p95_ms':round(percentile([t for t,_ in recovery],.95),2)},'accepted':all(r['p95_ms']<=1500 and r['error_percent']<1 for r in results) and all(s==200 for _,s in recovery)}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(final,indent=2),encoding='utf-8');print('Aceptación:',final['accepted'])
