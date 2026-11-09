#!/usr/bin/env python3
"""Run bounded audit collection, build research cohorts and archive privately. No training."""
import hashlib,json,os,re,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=('private-audit-evidence.json','private-forward-signals.json','forward-dataset-report.json','private-receipt-milestones.csv','receipt-cohort-report.json','manifest.json')
def main():
    import boto3
    bucket=os.environ['ARTEMIS_ML_BUCKET'];commit=os.environ['GITHUB_SHA'];run=os.environ['GITHUB_RUN_ID'];attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1')
    if not re.fullmatch(r'artemis-mlops-research-078809709432-eu-west-2',bucket):raise ValueError('Unexpected research bucket.')
    if not re.fullmatch(r'[0-9a-f]{40,64}',commit) or not run.isdigit() or not attempt.isdigit():raise ValueError('Invalid GitHub run metadata.')
    # Capture subprocess output: never upload private data as GitHub artifacts or print record-level files.
    def invoke(name,*args):
        p=subprocess.run([sys.executable,str(ROOT/name),*args],capture_output=True,text=True)
        if p.returncode:raise RuntimeError(name+' failed. No dataset upload attempted. Error type/details withheld; rerun locally for investigation.')
        lines=p.stdout.splitlines();marker='Aggregate report: '
        found=[x[len(marker):] for x in lines if x.startswith(marker)]
        if len(found)!=1:raise RuntimeError('Expected aggregate report path was not produced.')
        path=Path(found[0]).resolve()
        if not path.is_relative_to((Path.home()/'artemis-ml').resolve()):raise ValueError('Unexpected output directory.')
        return path,json.loads(path.read_text())
    cp,collection=invoke('collect_forward_dataset.py','--hours','72')
    if collection.get('paginationComplete') is not True:raise RuntimeError('Collection incomplete; no cohort or S3 upload created. Investigate pagination/time budget.')
    if collection.get('signalsWithPublication',0)<1:raise RuntimeError('No audited publications found; no upload created.')
    rp,cohort=invoke('build_receipt_cohorts.py','--source-dir',str(cp.parent))
    if cohort.get('labelsAssigned')!=0 or cohort.get('trainingReady') is not False:raise RuntimeError('Research-only guard failed.')
    paths=[cp.parent/x for x in FILES[:3]]+[rp.parent/x for x in FILES[3:]]
    entries=[];s3=boto3.client('s3',region_name='eu-west-2')
    prefix='research/'+run+'-'+attempt+'-'+commit[:12]+'-'+uuid.uuid4().hex+'/'
    for path in paths:
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();key=prefix+path.name
        s3.put_object(Bucket=bucket,Key=key,Body=data,ServerSideEncryption='AES256',ContentType='text/csv' if path.suffix=='.csv' else 'application/json',Metadata={'sha256':digest,'git-commit':commit},IfNoneMatch='*')
        head=s3.head_object(Bucket=bucket,Key=key)
        if head['ContentLength']!=len(data) or head.get('Metadata',{}).get('sha256')!=digest:raise RuntimeError('S3 upload verification failed.')
        entries.append({'name':path.name,'sha256':digest,'bytes':len(data),'versionId':head.get('VersionId')})
    archive={'schemaVersion':1,'commit':commit,'githubRunId':run,'githubRunAttempt':attempt,'prefix':prefix,'files':entries,'collectionWindowStartUtc':collection['windowStartUtc'],'collectionWindowEndUtc':collection['windowEndUtc'],'trainingReady':False,'labelsAssigned':0,'complete':True}
    # Upload this last: absence of this manifest means the archive is incomplete.
    data=json.dumps(archive,indent=2).encode();digest=hashlib.sha256(data).hexdigest()
    s3.put_object(Bucket=bucket,Key=prefix+'archive-manifest.json',Body=data,ServerSideEncryption='AES256',ContentType='application/json',Metadata={'sha256':digest},IfNoneMatch='*')
    check=s3.head_object(Bucket=bucket,Key=prefix+'archive-manifest.json')
    if check['ContentLength']!=len(data) or check.get('Metadata',{}).get('sha256')!=digest:raise RuntimeError('Archive manifest verification failed.')
    mp,merged=invoke('merge_research_archives.py','--collector',str(ROOT/'collect_forward_dataset.py'),'--builder',str(ROOT/'build_receipt_cohorts.py'))
    if merged.get('coverageContinuous') is not True or merged.get('cohortProduced') is not True or merged.get('labelsAssigned')!=0 or merged.get('trainingReady') is not False:
        raise RuntimeError('Merged research guard failed. Snapshot remains archived; no merged CSV uploaded.')
    merged_entries=[]
    merged_names=('private-audit-evidence.json','private-forward-signals.json','forward-dataset-report.json','private-merged-receipt-milestones.csv','receipt-cohort-report.json','private-archive-provenance.json','merge-report.json')
    for name in merged_names:
        data=(mp.parent/name).read_bytes();digest=hashlib.sha256(data).hexdigest();key=prefix+'merged/'+name
        s3.put_object(Bucket=bucket,Key=key,Body=data,ServerSideEncryption='AES256',ContentType='text/csv' if name.endswith('.csv') else 'application/json',Metadata={'sha256':digest,'git-commit':commit},IfNoneMatch='*')
        head=s3.head_object(Bucket=bucket,Key=key)
        if head['ContentLength']!=len(data) or head.get('Metadata',{}).get('sha256')!=digest:raise RuntimeError('Merged upload verification failed.')
        merged_entries.append({'name':name,'sha256':digest,'bytes':len(data),'versionId':head.get('VersionId')})
    data=json.dumps({'schemaVersion':1,'complete':True,'trainingReady':False,'labelsAssigned':0,'commit':commit,'files':merged_entries,'prefix':prefix+'merged/'},indent=2).encode()
    digest=hashlib.sha256(data).hexdigest()
    s3.put_object(Bucket=bucket,Key=prefix+'merged/merge-manifest.json',Body=data,ServerSideEncryption='AES256',ContentType='application/json',Metadata={'sha256':digest},IfNoneMatch='*')
    head=s3.head_object(Bucket=bucket,Key=prefix+'merged/merge-manifest.json')
    if head['ContentLength']!=len(data) or head.get('Metadata',{}).get('sha256')!=digest:raise RuntimeError('Merged manifest verification failed.')
    summary='## Research archive verified\n\n- Signals collected: '+str(collection['distinctSignals'])+'\n- Included in research CSV: '+str(cohort['includedSignals'])+'\n- Observation windows: '+json.dumps(cohort['observationWindowCounts'])+'\n- Private archive: `s3://'+bucket+'/'+prefix+'`\n- Collection pagination: complete\n- Training labels: none\n- Model training: disabled\n\nThis is a rolling 72-hour snapshot, not incremental or complete long-term event capture.\n'
    summary+='\n## Merged research verified\n\n- Archives verified: '+str(merged['archivesVerified'])+'\n- Repeated audit records removed: '+str(merged['repeatedAuditRecordsRemoved'])+'\n- Included signals: '+str(merged['includedSignals'])+'\n- Merged archive: `s3://'+bucket+'/'+prefix+'merged/`\n- Training: disabled\n'
    if os.environ.get('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(summary)
    print(summary)
if __name__=='__main__':main()
