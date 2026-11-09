#!/usr/bin/env python3
"""Read verified private S3 snapshots; merge audit evidence locally without training labels."""
import argparse,hashlib,importlib.util,json,sys,time
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
BUCKET='artemis-mlops-research-078809709432-eu-west-2'
NAMES={'private-audit-evidence.json','private-forward-signals.json','forward-dataset-report.json','private-receipt-milestones.csv','receipt-cohort-report.json','manifest.json'}
def digest(b):return hashlib.sha256(b).hexdigest()
def date(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('Timezone missing.')
 return d.astimezone(timezone.utc)
def merged_intervals(windows):
 result=[]
 for start,end in sorted(windows):
  if end<start:raise ValueError('Invalid archive time interval.')
  if result and start<=result[-1][1]:result[-1]=(result[-1][0],max(end,result[-1][1]))
  else:result.append((start,end))
 return result
def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def merge_records(records):
 unique={};repeats=0;conflicts=set()
 for r in records:
  req=r.get('awsRequestId');key=(req,r.get('phase')) if req else ('hash',digest(json.dumps(r,sort_keys=True).encode()))
  encoded=json.dumps(r,sort_keys=True,separators=(',',':'))
  if key in unique:
   if unique[key][0]!=encoded:conflicts.add(key)
   else:repeats+=1
  else:unique[key]=(encoded,r)
 if conflicts:raise ValueError('Conflicting audit records across snapshots; stopped without producing a merged dataset.')
 return [v[1] for v in unique.values()],repeats

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--days',type=int,default=7);p.add_argument('--collector',type=Path,default=Path.home()/'collect_forward_dataset.py');p.add_argument('--builder',type=Path,default=Path.home()/'build_receipt_cohorts.py');args=p.parse_args()
 if not 1<=args.days<=30:p.error('--days must be 1 to 30')
 for path in (args.collector,args.builder):
  if not path.expanduser().is_file():p.error('Required local research script not found: '+str(path))
 import boto3
 from botocore.config import Config
 s3=boto3.client('s3',region_name='eu-west-2',config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':3}))
 cutoff=datetime.now(timezone.utc)-timedelta(days=args.days);selected=[];token=None;complete=False;began=time.monotonic()
 print('Reading verified research archives from private S3. Local output only; no AWS changes.',flush=True)
 for page in range(20):
  kw={'Bucket':BUCKET,'Prefix':'research/','MaxKeys':1000}
  if token:kw['ContinuationToken']=token
  result=s3.list_objects_v2(**kw)
  selected.extend(x for x in result.get('Contents',[]) if x['Key'].endswith('/archive-manifest.json') and x['LastModified']>=cutoff)
  if len(selected)>50:raise ValueError('More than 50 archives selected. Narrow --days before retrying.')
  if not result.get('IsTruncated'):complete=True;break
  token=result.get('NextContinuationToken')
  if time.monotonic()-began>50:break
 if not complete:raise ValueError('S3 archive listing incomplete. No merged dataset created.')
 if not selected:raise ValueError('No completed research archive manifests found in the selected time range.')
 total=0
 def read(key,limit):
  nonlocal total
  obj=s3.get_object(Bucket=BUCKET,Key=key)
  if obj['ContentLength']>limit:obj['Body'].close();raise ValueError('Archive file exceeds size limit.')
  try:data=obj['Body'].read(limit+1)
  finally:obj['Body'].close()
  total+=len(data)
  if len(data)>limit or total>250*1024*1024:raise ValueError('Archive read budget exceeded.')
  return data
 records=[];windows=[];provenance=[]
 for obj in sorted(selected,key=lambda x:x['LastModified']):
  key=obj['Key'];prefix=key[:-len('archive-manifest.json')];manifestbytes=read(key,1024*1024);m=json.loads(manifestbytes)
  if m.get('complete') is not True or m.get('prefix')!=prefix or m.get('trainingReady') is not False or m.get('labelsAssigned')!=0:raise ValueError('Archive manifest failed research-only validation.')
  entries=m.get('files',[])
  if len(entries)!=len(NAMES) or {x.get('name') for x in entries}!=NAMES:raise ValueError('Unexpected archive file set.')
  payloads={}
  for item in entries:
   name=item['name'];data=read(prefix+name,30*1024*1024)
   if len(data)!=item.get('bytes') or digest(data)!=item.get('sha256'):raise ValueError('Archive file size/hash mismatch. Stopped.')
   if name in ('private-audit-evidence.json','forward-dataset-report.json'):payloads[name]=json.loads(data)
  evidence=payloads['private-audit-evidence.json'];report=payloads['forward-dataset-report.json']
  evidence_entry=next(x for x in entries if x['name']=='private-audit-evidence.json')
  if evidence_entry['sha256']!=report.get('evidenceSha256'):raise ValueError('Archive evidence/report hash mismatch.')
  if evidence.get('paginationComplete') is not True or report.get('paginationComplete') is not True:raise ValueError('Incomplete audit search in an archive.')
  start=date(evidence['windowStartUtc']);end=date(evidence['windowEndUtc'])
  if (start,end)!=(date(report['windowStartUtc']),date(report['windowEndUtc'])) or (start,end)!=(date(m['collectionWindowStartUtc']),date(m['collectionWindowEndUtc'])):raise ValueError('Archive coverage timestamps disagree.')
  windows.append((start,end));records.extend(evidence['records']);provenance.append({'archiveManifestKey':key,'manifestSha256':digest(manifestbytes),'commit':m.get('commit'),'runId':m.get('githubRunId')})
  if time.monotonic()-began>180:raise ValueError('Archive merge time budget exceeded. Narrow --days.')
 unique,repeats=merge_records(records);intervals=merged_intervals(windows);continuous=len(intervals)==1
 collector=load_module(args.collector.expanduser(),'research_collector');builder=load_module(args.builder.expanduser(),'research_builder')
 end=max(e for _,e in windows);start=min(s for s,_ in windows)
 signals,collection=collector.aggregate(unique,end,continuous)
 evidence={'schemaVersion':1,'windowStartUtc':start.isoformat(),'windowEndUtc':end.isoformat(),'paginationComplete':continuous,'records':unique}
 eb=json.dumps(evidence,sort_keys=True,indent=2).encode()
 collection.update(schemaVersion=1,windowStartUtc=start.isoformat(),windowEndUtc=end.isoformat(),paginationComplete=continuous,evidenceSha256=digest(eb),trainingReady=False)
 folder=Path.home()/'artemis-ml'/('merged-research-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'));folder.mkdir(parents=True,mode=0o700)
 def save(name,data):
  path=folder/name;path.write_bytes(data if isinstance(data,bytes) else (json.dumps(data,indent=2)+'\n').encode());path.chmod(0o600)
 save('private-audit-evidence.json',eb);save('private-forward-signals.json',signals);save('forward-dataset-report.json',collection)
 rows=[];cohort=None
 if continuous:
  rows,cohort=builder.build(signals,evidence,collection,24)
  import csv,io
  buffer=io.StringIO()
  if rows:
   writer=csv.DictWriter(buffer,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
  save('private-merged-receipt-milestones.csv',buffer.getvalue().encode());save('receipt-cohort-report.json',cohort)
 summary={'schemaVersion':1,'reviewType':'verified_snapshot_merge','archivesVerified':len(selected),'archiveListingComplete':complete,'sourceAuditRecordCount':len(records),'uniqueAuditRecordCount':len(unique),'repeatedAuditRecordsRemoved':repeats,'coverageContinuous':continuous,'coverageIntervals':[{'startUtc':s.isoformat(),'endUtc':e.isoformat()} for s,e in intervals],'distinctSignals':len(signals),'includedSignals':len(rows) if continuous else None,'excludedSignals':cohort.get('excludedSignals') if cohort else None,'exclusionReasonCounts':cohort.get('exclusionReasonCounts') if cohort else None,'observationWindowCounts':cohort.get('observationWindowCounts') if cohort else None,'cohortProduced':continuous,'trainingReady':False,'labelsAssigned':0,'bytesRead':total,'outputDirectory':str(folder),'limitations':['Overlapping audit evidence is deduplicated by Lambda request ID and phase, not by assuming repeated signals are new samples.','Continuous archived query intervals do not prove complete publisher events, market observation or ingestion availability.','First observed successful creation receipt may precede selected archives; missing publication evidence is excluded.','If coverage has gaps, no research CSV is produced.','Stop evidence without TP1 remains unknown, never labeled a loss.','No S3 writes, source file changes, training labels or model training.']}
 save('private-archive-provenance.json',{'archives':provenance,'collectorSha256':digest(args.collector.expanduser().read_bytes()),'builderSha256':digest(args.builder.expanduser().read_bytes()),'mergedEvidenceSha256':digest(eb)})
 save('merge-report.json',summary)
 print(json.dumps(summary,indent=2));print('Aggregate report:',folder/'merge-report.json')
 print('READ ONLY S3 ACCESS. LOCAL RESEARCH OUTPUT ONLY. NO AWS CHANGES OR TRAINING.')
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('Stopped:',str(e) if isinstance(e,ValueError) else type(e).__name__+'; check local AWS access and source scripts.',file=sys.stderr);sys.exit(1)
