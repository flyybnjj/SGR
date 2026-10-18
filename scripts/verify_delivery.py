
import csv
import json
import os
from pathlib import Path
import sys
import unittest
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.test.runner import DiscoverRunner

records=[]
class EvidenceResult(unittest.TextTestResult):
    def record(self,test,state,detail=''):
        name=test.id()
        records.append({'requisito':'PDF A1-A4 / C1-C6','modulo':name.split('.')[0],
          'precondiciones':'Base temporal migrada; fixtures del caso; correo en memoria cuando corresponde',
          'pasos':name,'esperado':test.shortDescription() or 'Se cumplen todas las aserciones del caso',
          'obtenido':detail or 'Todas las aserciones se cumplieron','estado':state,
          'evidencia':name,'responsable':'Benjamin Avalos; ejecución automatizada asistida por Codex',
          'fecha':datetime.now(timezone.utc).isoformat()})
    def addSuccess(self,test):super().addSuccess(test);self.record(test,'APROBADO')
    def addFailure(self,test,err):super().addFailure(test,err);self.record(test,'FALLÓ',str(err[1]))
    def addError(self,test,err):super().addError(test,err);self.record(test,'ERROR',str(err[1]))
    def addSkip(self,test,reason):super().addSkip(test,reason);self.record(test,'PENDIENTE',reason)
class EvidenceRunner(DiscoverRunner):
    def get_resultclass(self):return EvidenceResult

if __name__=='__main__':
    out=ROOT/'docs/evidencias';out.mkdir(parents=True,exist_ok=True)
    failures=EvidenceRunner(verbosity=1,interactive=False).run_tests(sys.argv[1:] or ['.'])
    (out/'pruebas-funcionales.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    if records:
        with (out/'matriz-funcional.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    sys.exit(bool(failures))
