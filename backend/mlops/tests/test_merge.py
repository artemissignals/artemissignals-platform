import importlib.util,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
p=Path(__file__).resolve().parents[1]/'merge_research_archives.py';s=importlib.util.spec_from_file_location('archive_merge',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class MergeTests(unittest.TestCase):
 def test_overlap_removed(self):
  a={'awsRequestId':'r','phase':'response','httpStatus':201};rows,n=m.merge_records([a,a]);self.assertEqual(len(rows),1);self.assertEqual(n,1)
 def test_conflicting_evidence_rejected(self):
  a={'awsRequestId':'r','phase':'response','httpStatus':201}
  with self.assertRaises(ValueError):m.merge_records([a,{**a,'httpStatus':409}])
 def test_received_response_kept_separate(self):
  a={'awsRequestId':'r','phase':'response'};rows,n=m.merge_records([a,{**a,'phase':'received'}]);self.assertEqual(len(rows),2)
 def test_missing_request_id_uses_content_hash(self):
  a={'phase':'response','httpStatus':201};rows,n=m.merge_records([a,a,{**a,'httpStatus':409}]);self.assertEqual(len(rows),2);self.assertEqual(n,1)
 def test_coverage_overlap(self):
  t=datetime(2026,11,9,tzinfo=timezone.utc);d=timedelta(days=1);self.assertEqual(len(m.merged_intervals([(t,t+2*d),(t+d,t+3*d)])),1)
 def test_gap_preserved(self):
  t=datetime(2026,11,9,tzinfo=timezone.utc);d=timedelta(days=1);self.assertEqual(len(m.merged_intervals([(t,t+d),(t+2*d,t+3*d)])),2)
 def test_reversed_interval_rejected(self):
  t=datetime(2026,11,9,tzinfo=timezone.utc)
  with self.assertRaises(ValueError):m.merged_intervals([(t,t-timedelta(hours=1))])
if __name__=='__main__':unittest.main()
