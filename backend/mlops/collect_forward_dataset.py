#!/usr/bin/env python3
"""Read-only bounded forward-audit collector. Private research evidence, never training labels."""
import argparse, hashlib, json, os, time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
START=datetime(2026,11,7,16,2,tzinfo=timezone.utc)
GROUP='/aws/lambda/artemis-signals-prod-v1-ingest'
FEATURES=('symbol','timeframe','direction','quality_score','entry','sl','tp1','tp2','tp3')
FIELDS=('auditSchema','auditType','awsRequestId','operation','phase','serverReceivedAt','serverCompletedAt','httpStatus','outcome','duplicateReported','signalId','eventType','publisherPublishedAt','publisherPublishedAtProvided','publisherPublishedAtValid','publisherEventAt','publisherEventAtProvided','publisherEventAtValid','qualitySourceField','observedPrice')+FEATURES
EVENTS={'TP1_HIT','TP2_HIT','TP3_HIT','SL_HIT','EXPIRED'}
def date(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (AttributeError,ValueError,TypeError):return None

def number(value,quality=False):
    try:
        if value is None or isinstance(value,bool):return False
        n=Decimal(str(value))
        return n.is_finite() and (0<=n<=100 if quality else n>0)
    except (InvalidOperation,ValueError,TypeError):return False

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def parse_message(message):
    if not isinstance(message,str):return None
    start=message.find('{')
    if start<0:return None
    try:r=json.loads(message[start:])
    except (ValueError,TypeError):return None
    if not isinstance(r,dict) or r.get('auditType')!='artemis_forward_validation' or r.get('auditSchema')!=1:return None
    return {k:r[k] for k in FIELDS if k in r}

def aggregate(records,end,complete):
    grouped=defaultdict(lambda:{'publications':[],'lifecycleResponses':[]})
    phases=Counter();responses=Counter();request_fingerprints={};conflicts=set();response_ids=set();received_ids=set();skipped=Counter()
    for r in records:
        phases[str(r.get('phase'))]+=1
        request=r.get('awsRequestId');phase=r.get('phase')
        if phase=='received' and request:received_ids.add(request)
        if phase!='response':continue
        if request:
            fp=digest(r)
            if request in request_fingerprints:
                if request_fingerprints[request]!=fp:conflicts.add(request)
                continue
            request_fingerprints[request]=fp;response_ids.add(request)
        status=r.get('httpStatus');responses[str(status)]+=1
        if type(status) is not int or not 200<=status<300:skipped['nonAcceptedResponse']+=1;continue
        sid=r.get('signalId');op=r.get('operation')
        if not isinstance(sid,str) or not sid:skipped['missingSignalId']+=1;continue
        if not date(r.get('serverReceivedAt')):skipped['invalidServerReceipt']+=1;continue
        if op=='publication':grouped[sid]['publications'].append(r)
        elif op=='lifecycle':grouped[sid]['lifecycleResponses'].append(r)
        else:skipped['otherOperation']+=1
    rows=[];finding_counts=Counter();event_types=Counter();publication_count=0;event_count=0;potential_pairs=0
    for sid,g in sorted(grouped.items()):
        pubs=sorted(g['publications'],key=lambda r:date(r['serverReceivedAt']))
        life=sorted(g['lifecycleResponses'],key=lambda r:date(r['serverReceivedAt']))
        findings=set();first=pubs[0] if pubs else None
        if first:publication_count+=1
        else:findings.add('no_publication_in_audit_window')
        # This is first observed server receipt, never assumed to be original publication.
        first_receipt=date(first['serverReceivedAt']) if first else None
        published=date(first.get('publisherPublishedAt')) if first else None
        if first and not published:findings.add('original_publication_time_unverified')
        if first and first.get('duplicateReported') is True:findings.add('first_publication_response_reports_duplicate')
        feature_sets={digest({k:p.get(k) for k in FEATURES}) for p in pubs}
        if len(feature_sets)>1:findings.add('publication_feature_conflict')
        features={k:first.get(k) for k in FEATURES} if first else {}
        if first:
            if any(not number(features.get(k),k=='quality_score') for k in ('quality_score','entry','sl','tp1','tp2','tp3')):findings.add('missing_or_invalid_numeric_features')
            if not features.get('symbol') or not features.get('timeframe') or features.get('direction') not in ('BUY','SELL'):findings.add('missing_or_invalid_categorical_features')
            if published and abs((first_receipt-published).total_seconds())>300:findings.add('publication_time_differs_from_receipt_over_5m')
            if first_receipt+timedelta(hours=24)>end:findings.add('24h_since_first_receipt_not_elapsed')
        unique={};duplicates=0;by_type_time=defaultdict(set)
        for r in life:
            evidence={k:r.get(k) for k in ('eventType','publisherEventAt','observedPrice')}
            # Identical evidence is collapsed only for research display, not proven same market event.
            key=digest(evidence)
            if key in unique:duplicates+=1;continue
            unique[key]=r
            by_type_time[(r.get('eventType'),r.get('publisherEventAt'))].add(str(r.get('observedPrice')))
        if duplicates:findings.add('repeated_lifecycle_evidence')
        if any(len(v)>1 for v in by_type_time.values()):findings.add('same_event_time_conflicting_prices')
        events=[]
        for r in unique.values():
            observed=date(r.get('publisherEventAt'));received=date(r['serverReceivedAt']);kind=r.get('eventType')
            if kind not in EVENTS:findings.add('unknown_lifecycle_event_type')
            if observed is None:findings.add('missing_or_invalid_publisher_event_time')
            if not number(r.get('observedPrice')):findings.add('missing_or_invalid_observed_price')
            delay=(received-observed).total_seconds() if observed else None
            if delay is not None and delay< -300:findings.add('publisher_event_over_5m_in_future')
            if delay is not None and delay>300:findings.add('publisher_event_delay_over_5m')
            if observed and first_receipt and observed<first_receipt:findings.add('event_precedes_first_publication_receipt')
            if r.get('awsRequestId') in conflicts:findings.add('conflicting_response_for_request')
            event_types[str(kind)]+=1
            events.append({'eventType':kind,'publisherEventAt':r.get('publisherEventAt'),'serverReceivedAt':r['serverReceivedAt'],'observedPrice':r.get('observedPrice'),'receiptDelaySeconds':delay,'duplicateReported':r.get('duplicateReported')})
        if any(p.get('awsRequestId') in conflicts for p in pubs):findings.add('conflicting_response_for_request')
        if not events:findings.add('no_lifecycle_evidence')
        if not complete:findings.add('audit_search_incomplete')
        # No absence of TP1 is converted into a stop-first/loss label.
        kinds={r.get('eventType') for r in events}
        if 'TP1_HIT' in kinds and 'SL_HIT' in kinds:potential_pairs+=1
        findings.add('publisher_retry_and_observation_completeness_unverified')
        finding_counts.update(findings);event_count+=len(events)
        rows.append({'signalId':sid,'featuresAsFirstObserved':features,'firstObservedPublicationReceiptUtc':first['serverReceivedAt'] if first else None,'publisherPublishedAt':first.get('publisherPublishedAt') if first else None,'publicationResponseCount':len(pubs),'lifecycleResponseCount':len(life),'uniqueLifecycleEvidenceCount':len(events),'repeatedLifecycleEvidenceCount':duplicates,'events':events,'reviewFindings':sorted(findings),'trainingLabel':None,'trainingReady':False})
    report={'auditPhaseCounts':dict(phases),'httpStatusCounts':dict(responses),'skippedResponseCounts':dict(skipped),'distinctSignals':len(rows),'signalsWithPublication':publication_count,'publicationResponses':sum(len(v['publications']) for v in grouped.values()),'acceptedLifecycleResponses':sum(len(v['lifecycleResponses']) for v in grouped.values()),'uniqueLifecycleEvidenceRows':event_count,'uniqueLifecycleEvidenceByType':dict(event_types),'signalsWithBothTP1AndStopEvidence':potential_pairs,'reviewFindingCounts':dict(sorted(finding_counts.items())),'responsesWithoutReceivedPhase':len(response_ids-received_ids),'receivedWithoutResponsePhase':len(received_ids-response_ids),'conflictingRequestResponseRecords':len(conflicts),'trainingReady':False,'labelsAssigned':0}
    return rows,report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hours',type=int,default=72);args=p.parse_args()
    if not 1<=args.hours<=168:p.error('--hours must be 1 to 168')
    import boto3
    end=datetime.now(timezone.utc);start=max(START,end-timedelta(hours=args.hours))
    client=boto3.client('logs',region_name='eu-west-2')
    params={'logGroupName':GROUP,'startTime':int(start.timestamp()*1000),'endTime':int(end.timestamp()*1000),'filterPattern':'"artemis_forward_validation"','limit':1000}
    seen=set();records=[];pages=0;complete=False;reason=None;began=time.monotonic()
    print('Reading audit logs only. Creating private local research files; no training or AWS changes.',flush=True)
    while pages<100 and time.monotonic()-began<50:
        result=client.filter_log_events(**params);pages+=1
        for e in result.get('events',[]):
            key=e.get('eventId') or digest({'timestamp':e.get('timestamp'),'message':e.get('message')})
            if key in seen:continue
            seen.add(key);r=parse_message(e.get('message'))
            if r is not None:records.append(r)
        token=result.get('nextToken')
        if not token:complete=True;break
        if token==params.get('nextToken'):reason='repeated_pagination_token';break
        params['nextToken']=token
    if not complete and reason is None:reason='page_limit' if pages>=100 else 'time_budget'
    rows,report=aggregate(records,end,complete)
    folder=Path.home()/'artemis-ml'/('forward-dataset-'+end.strftime('%Y%m%d-%H%M%S-%f'));folder.mkdir(parents=True,mode=0o700)
    evidence={'schemaVersion':1,'windowStartUtc':start.isoformat(),'windowEndUtc':end.isoformat(),'paginationComplete':complete,'records':records}
    data=json.dumps(evidence,sort_keys=True,indent=2).encode()
    for name,blob in [('private-audit-evidence.json',data),('private-forward-signals.json',json.dumps(rows,indent=2).encode())]:
        f=folder/name;f.write_bytes(blob);f.chmod(0o600)
    report.update(schemaVersion=1,reviewType='forward_only_research_dataset',windowStartUtc=start.isoformat(),windowEndUtc=end.isoformat(),paginationComplete=complete,incompleteReason=reason,pagesRead=pages,evidenceSha256=hashlib.sha256(data).hexdigest(),outputDirectory=str(folder),limitations=[
        'First observed server receipt is not verified original publication time. Replays may predate this search.',
        'HTTP acceptance and observed prices do not independently verify market execution or event completeness.',
        'Equal event type, publisher timestamp and price are grouped as repeated evidence, not proven identical market events.',
        'No training labels assigned. Unresolved or missing outcomes are not losses.',
        'Publisher retry behavior, replacement closure provenance and publication-time features still require verification.',
        'A complete log search covers this bounded window only; it does not prove every publisher event arrived.',
        'No DynamoDB access, historical dataset modification, S3 upload, model training or resource creation.'
    ])
    path=folder/'forward-dataset-report.json';path.write_text(json.dumps(report,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(report,indent=2));print('Aggregate report:',path)
    print('Private evidence stays local. Share only the aggregate report.')
    print('NO AWS RESOURCES OR SIGNAL RECORDS MODIFIED. NO LABELS ASSIGNED. NO TRAINING STARTED.')
if __name__=='__main__':main()
