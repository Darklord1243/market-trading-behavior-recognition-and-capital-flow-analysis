"""AFAC2026 Track-1 pipeline package.

Modules (per brief §9):
  ingest      raw-L2 reader + nested-JSON book parsing + cumulative->tick
  features    per-(stock, day) feature computation (critical path)
  aggregate   window (hh) -> daily (stock, day) feature matrix
  rules       Stage-1 soft-rule scorer (游资 vs 量化机构) + intent gate
  label       Stage-2 weak labels + confidence
  model       Stage-3 LightGBM/XGBoost heads (stub)
  cluster     Task-1 bounded-K clustering (stub)
  postprocess canonical label mapping + CSV writers (4-col, UTF-8-sig, guarded)
"""
