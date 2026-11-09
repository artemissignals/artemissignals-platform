# Artemis research pipeline

This folder holds receipt-based signal research tooling. It does not train or deploy a model.

- `collect_forward_dataset.py`: bounded, read-only CloudWatch collection; requires boto3 and AWS log-read access when manually run in CloudShell.
- `build_receipt_cohorts.py`: offline receipt-based milestone CSV and aggregate report.
- `tests/`: synthetic fixtures only; no AWS calls or credentials required.

The GitHub workflow checks syntax and tests on pushes and pull requests. It has no AWS credentials, no schedule, and no training or deployment step.

## Existing CloudShell use

Run the collector, then use its output directory as the builder input:

```bash
python3 backend/mlops/collect_forward_dataset.py
python3 backend/mlops/build_receipt_cohorts.py --source-dir /actual/collector/output/directory
```

The collector reads up to 72 hours by default (maximum selectable 168 hours). It is a bounded research tool, not an incremental archival service. Review paginationComplete before using results. Long-term collection and S3 storage require a separate restricted AWS role, checkpointing, retention configuration and automation workflow.

Do not commit real reports, CSV files, audit evidence, credentials or production Lambda backups.

## Research definition

Start: first audited publication HTTP 201 with duplicateReported=false, within the reviewed log window. This is server receipt time, not verified original signal time.

Horizon: provisional 24 hours. An elapsed window does not establish event completeness.

Milestones: observed TP1/TP2/TP3/stop events, with publisher observation time and frozen server receipt cutoff. Missing outcomes stay blank. Stops after TP milestones preserve both facts. No losses, win rates, training labels or predictive claims are inferred.

Known gaps: replacement-closure coverage, publisher-side completeness, overlapping setups, time-based evaluation design, concentration and sample size. Historical labels remain provisional. No model training authorized by this check workflow.
