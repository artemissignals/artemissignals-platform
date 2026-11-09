import copy,importlib.util,json,unittest
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('collect_forward_dataset');b=load('build_receipt_cohorts')
class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.f=dict(symbol='GBPUSD',timeframe='H1',direction='SELL',quality_score='95',entry='1.2',sl='1.3',tp1='1.1',tp2='1',tp3='.9')
  self.p=dict(signalId='s',phase='response',operation='publication',httpStatus=201,duplicateReported=False,serverReceivedAt='2026-11-07T17:00:00Z',awsRequestId='p',**self.f)
  self.e=dict(eventType='SL_HIT',publisherEventAt='2026-11-07T18:00:00Z',serverReceivedAt='2026-11-07T18:00:02Z',observedPrice='1.3')
  self.audit=dict(self.e,signalId='s',phase='response',operation='lifecycle',httpStatus=201,awsRequestId='e')
  self.ev=dict(paginationComplete=True,windowStartUtc='2026-11-07T16:02:00Z',windowEndUtc='2026-11-09T07:51:00Z',records=[self.p,self.audit])
  self.report={k:self.ev[k] for k in ('paginationComplete','windowStartUtc','windowEndUtc')}
  self.row=dict(signalId='s',featuresAsFirstObserved=self.f,firstObservedPublicationReceiptUtc=self.p['serverReceivedAt'],events=[self.e],reviewFindings=[])
 def build(self):return b.build([self.row],self.ev,self.report,24)
 def test_stop_without_tp1_is_unknown(self):
  rows,r=self.build();self.assertEqual(rows[0]['observed_tp1_within_window'],'');self.assertEqual(rows[0]['observed_event_order'],'stop_observed_tp1_unknown');self.assertEqual(r['labelsAssigned'],0);self.assertEqual(rows[0]['training_label'],'')
 def test_tp1_then_stop_preserves_both(self):
  e=dict(self.e,eventType='TP1_HIT',publisherEventAt='2026-11-07T17:30:00Z',serverReceivedAt='2026-11-07T17:30:02Z',observedPrice='1.1');self.row['events'].append(e);self.ev['records'].append(dict(e,signalId='s',phase='response',operation='lifecycle',httpStatus=201))
  rows,_=self.build();self.assertEqual(rows[0]['observed_event_order'],'tp1_before_stop');self.assertEqual(rows[0]['observed_tp1_within_window'],1);self.assertEqual(rows[0]['observed_stop_within_window'],1)
 def test_elapsed_window_uses_frozen_cutoff(self):
  rows,_=self.build();self.assertEqual(rows[0]['window_state'],'window_elapsed');self.ev['windowEndUtc']=self.report['windowEndUtc']='2026-11-07T19:00:00Z';rows,_=self.build();self.assertEqual(rows[0]['window_state'],'window_open')
 def test_incomplete_search_rejected(self):
  self.report['paginationComplete']=False
  with self.assertRaises(ValueError):self.build()
 def test_altered_event_rejected(self):
  self.row['events']=[dict(self.e,observedPrice='9')]
  with self.assertRaises(ValueError):self.build()
 def test_altered_feature_rejected(self):
  self.row['featuresAsFirstObserved']=dict(self.f,entry='9')
  with self.assertRaises(ValueError):self.build()
 def test_duplicate_signal_rejected(self):
  with self.assertRaises(ValueError):b.build([self.row,self.row],self.ev,self.report,24)
 def test_publication_conflict_excluded(self):
  self.row['reviewFindings']=['publication_feature_conflict'];rows,r=self.build();self.assertEqual(rows,[]);self.assertEqual(r['excludedSignals'],1)
 def test_no_creation_evidence_excluded(self):
  self.p['duplicateReported']=True;rows,r=self.build();self.assertEqual(rows,[])
 def test_unknown_log_fields_not_exported(self):
  r=c.parse_message(json.dumps(dict(self.p,auditSchema=1,auditType='artemis_forward_validation',secret='private')));self.assertNotIn('secret',r)
 def test_retries_grouped_without_labels(self):
  rows,r=c.aggregate([self.p,self.audit,dict(self.audit,awsRequestId='retry')],datetime(2026,11,9,tzinfo=timezone.utc),True);self.assertEqual(rows[0]['uniqueLifecycleEvidenceCount'],1);self.assertEqual(rows[0]['repeatedLifecycleEvidenceCount'],1);self.assertIsNone(rows[0]['trainingLabel'])
 def test_rejected_response_not_used(self):
  rows,r=c.aggregate([dict(self.p,httpStatus=409)],datetime(2026,11,9,tzinfo=timezone.utc),True);self.assertEqual(rows,[])
if __name__=='__main__':unittest.main()
