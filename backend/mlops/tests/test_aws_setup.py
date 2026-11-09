"""Static scope checks; no AWS calls."""
import importlib.util,unittest
from pathlib import Path
# Setup script is a one-time CloudShell file, outside the Git source folder.
# CI tests exercise the runner's input guard without credentials or boto3.
import os,sys,types
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('runner',ROOT/'run_collection.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
class RunnerTests(unittest.TestCase):
 def test_wrong_bucket_rejected_before_aws(self):
  with patch.dict(sys.modules,{'boto3':types.SimpleNamespace()}),patch.dict(os.environ,{'ARTEMIS_ML_BUCKET':'wrong','GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'1'}):
   with self.assertRaises(ValueError):r.main()
 def test_bad_commit_rejected_before_collection(self):
  with patch.dict(sys.modules,{'boto3':types.SimpleNamespace()}),patch.dict(os.environ,{'ARTEMIS_ML_BUCKET':'artemis-mlops-research-078809709432-eu-west-2','GITHUB_SHA':'not-a-commit','GITHUB_RUN_ID':'1'}):
   with self.assertRaises(ValueError):r.main()
if __name__=='__main__':unittest.main()
