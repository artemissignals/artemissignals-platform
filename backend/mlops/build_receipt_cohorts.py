#!/usr/bin/env python3
"""Offline receipt-based milestone research. Never converts missing events into losses."""
import argparse,csv,hashlib,io,json,os
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
VERSION='receipt-milestones-v1'
FEATURES=('symbol','timeframe','direction','quality_score','entry','sl','tp1','tp2','tp3')
BLOCKERS={'publication_feature_conflict','conflicting_response_for_request','same_event_time_conflicting_prices','missing_or_invalid_numeric_features','missing_or_invalid_categorical_features','first_publication_response_reports_duplicate','no_publication_in_audit_window','audit_search_incomplete','missing_or_invalid_publisher_event_time','missing_or_invalid_observed_price','unknown_lifecycle_event_type','publisher_event_over_5m_in_future','event_precedes_first_publication_receipt'}
TYPES={'TP1_HIT','TP2_HIT','TP3_HIT','SL_HIT','EXPIRED'}
def date(value):
    if not isinstance(value,str):raise ValueError('Timezone-aware timestamp required.')
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Timezone-aware timestamp required.')
    return d.astimezone(timezone.utc)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def build(rows,evidence,report,hours):
    if report.get('paginationComplete') is not True or evidence.get('paginationComplete') is not True:raise ValueError('Source log search was incomplete. Do not build this cohort.')
    if evidence.get('windowEndUtc')!=report.get('windowEndUtc') or evidence.get('windowStartUtc')!=report.get('windowStartUtc'):raise ValueError('Evidence and report windows differ.')
    cutoff=date(report['windowEndUtc'])
    accepted={};seen_ids=set();lifecycle_evidence=set()
    for r in evidence.get('records',[]):
        status=r.get('httpStatus')
        if r.get('phase')=='response' and r.get('operation')=='lifecycle' and type(status) is int and 200<=status<300:
            lifecycle_evidence.add(tuple(r.get(k) for k in ('signalId','eventType','publisherEventAt','serverReceivedAt','observedPrice')))
        if r.get('phase')!='response' or r.get('operation')!='publication' or r.get('httpStatus')!=201 or r.get('duplicateReported') is not False:continue
        sid=r.get('signalId')
        if not sid:continue
        if sid not in accepted or date(r['serverReceivedAt'])<date(accepted[sid]['serverReceivedAt']):accepted[sid]=r
    output=[];exclusions=Counter();states=Counter();flags=Counter();counts=Counter();markets=Counter()
    for r in rows:
        sid=r.get('signalId')
        if not sid or sid in seen_ids:raise ValueError('Missing or duplicate signal ID in research file.')
        seen_ids.add(sid)
        findings=set(r.get('reviewFindings',[]));blocked=findings&BLOCKERS
        p=accepted.get(sid)
        if p is None:blocked.add('no_audited_201_nonduplicate_publication')
        if blocked:
            exclusions.update(blocked);continue
        receipt=date(p['serverReceivedAt'])
        if r.get('firstObservedPublicationReceiptUtc')!=p['serverReceivedAt']:raise ValueError('First publication receipt disagrees with audit evidence.')
        features=r.get('featuresAsFirstObserved',{})
        if any(features.get(k)!=p.get(k) for k in FEATURES):raise ValueError('Feature values disagree with first accepted publication evidence.')
        if receipt<date(report['windowStartUtc']) or receipt>cutoff:raise ValueError('Publication outside reviewed audit window.')
        end=receipt+timedelta(hours=hours);mature=end<=cutoff
        state='window_elapsed' if mature else 'window_open';states[state]+=1;markets[str(features.get('symbol','UNKNOWN'))]+=1
        observed={};delayed=False;events=r.get('events',[])
        for e in events:
            if (sid,e.get('eventType'),e.get('publisherEventAt'),e.get('serverReceivedAt'),e.get('observedPrice')) not in lifecycle_evidence:raise ValueError('Lifecycle evidence disagrees with audit records.')
            kind=e.get('eventType')
            if kind not in TYPES:raise ValueError('Unknown lifecycle event type.')
            when=date(e['publisherEventAt']);received=date(e['serverReceivedAt'])
            if received>cutoff:raise ValueError('Event receipt is later than the frozen evidence cutoff.')
            if received<receipt or when<receipt:raise ValueError('Event precedes publication receipt; refresh evidence review.')
            if (received-when).total_seconds()>300:delayed=True
            if receipt<=when<=end:
                if kind not in observed or when<observed[kind]:observed[kind]=when
        # These fields represent recorded evidence; blank never means negative/loss.
        row={'signal_id':sid,**{k:features.get(k) for k in FEATURES},'observation_start_utc':receipt.isoformat(),'observation_start_basis':'first_audited_201_nonduplicate_server_receipt','publisher_signal_time_verified':False,'window_end_utc':end.isoformat(),'evidence_cutoff_utc':cutoff.isoformat(),'window_state':state,'window_elapsed_does_not_prove_event_completeness':True}
        for key,kind in (('tp1','TP1_HIT'),('tp2','TP2_HIT'),('tp3','TP3_HIT'),('stop','SL_HIT')):
            row['observed_'+key+'_within_window']=1 if kind in observed else ''
            row['first_observed_'+key+'_at_utc']=observed[kind].isoformat() if kind in observed else ''
            if kind in observed:counts[key+'_observed']+=1
        if 'TP1_HIT' in observed and 'SL_HIT' in observed:
            order='tp1_before_stop' if observed['TP1_HIT']<observed['SL_HIT'] else 'stop_before_tp1' if observed['SL_HIT']<observed['TP1_HIT'] else 'same_timestamp_ambiguous'
        elif 'TP1_HIT' in observed:order='tp1_observed_no_stop_observed'
        elif 'SL_HIT' in observed:order='stop_observed_tp1_unknown'
        else:order='no_tp1_or_stop_observed'
        flags[order]+=1
        row.update(observed_event_order=order,expiration_event_observed_within_window='EXPIRED' in observed,replacement_closure_coverage='not_collected',lifecycle_delay_over_5m=delayed,training_label='',training_ready=False)
        output.append(row)
    summary={'methodologyVersion':VERSION,'windowHours':hours,'evidenceCutoffUtc':cutoff.isoformat(),'inputSignals':len(rows),'includedSignals':len(output),'excludedSignals':len(rows)-len(output),'exclusionReasonCounts':dict(exclusions),'observationWindowCounts':dict(states),'recordedMilestonesWithinWindow':dict(counts),'recordedTP1StopOrder':dict(flags),'byInstrument':dict(markets),'trainingReady':False,'labelsAssigned':0,'limitations':['This is receipt-based target tracking, not original market signal timing, trade execution, returns, or predictive evaluation.','24 hours is a provisional research horizon. An elapsed window does not prove complete event observation.','Blank milestone fields mean unknown/not observed, never a negative outcome or loss.','Events are grouped by publisher observation time, using only evidence received by the frozen source cutoff.','Stop-before-TP1 is recorded evidence order only; terminal-state rejection can conceal earlier events.','Replacement closures are not collected by this audit. No uncensored cohort or survival labels are claimed.','No chronological train/test split or model training is performed. Overlap and selection bias remain unresolved.']}
    return output,summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',required=True,type=Path);p.add_argument('--hours',type=int,default=24);args=p.parse_args()
    if not 1<=args.hours<=168:p.error('--hours must be 1 to 168')
    source=args.source_dir.expanduser().resolve();rp=source/'forward-dataset-report.json';ep=source/'private-audit-evidence.json';sp=source/'private-forward-signals.json'
    blobs={x.name:x.read_bytes() for x in (rp,ep,sp)}
    report=json.loads(blobs[rp.name]);evidence=json.loads(blobs[ep.name]);signals=json.loads(blobs[sp.name])
    if sha(blobs[ep.name])!=report.get('evidenceSha256'):raise SystemExit('Evidence hash mismatch. No output written.')
    rows,summary=build(signals,evidence,report,args.hours)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f');folder=Path.home()/'artemis-ml'/('receipt-cohorts-'+stamp);folder.mkdir(parents=True,mode=0o700)
    f=io.StringIO()
    if rows:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    data=f.getvalue().encode();csvpath=folder/'private-receipt-milestones.csv';csvpath.write_bytes(data);csvpath.chmod(0o600)
    manifest={'schemaVersion':1,'methodologyVersion':VERSION,'sourceDirectory':str(source),'sourceFileSha256':{k:sha(v) for k,v in blobs.items()},'outputCsvSha256':sha(data),'csvColumns':list(rows[0]) if rows else [],'rowCount':len(rows),'trainingReady':False}
    for filename,obj in [('manifest.json',manifest),('receipt-cohort-report.json',{**summary,'outputDirectory':str(folder)})]:
        path=folder/filename;path.write_text(json.dumps(obj,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({**summary,'outputDirectory':str(folder)},indent=2))
    print('Aggregate report:',folder/'receipt-cohort-report.json')
    print('Private CSV stays local. NO AWS CALLS. SOURCE DATA UNCHANGED. NO TRAINING LABELS OR MODEL TRAINING.')
if __name__=='__main__':main()
