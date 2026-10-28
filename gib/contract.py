"""Explicit user-approved editorial/schedule contract; changes fail tests until authorized."""
import hashlib
import json
from pathlib import Path

CONTRACT_PATH=Path(__file__).resolve().parents[1]/"config"/"frozen_contract.json"
APPROVED_SHA256="762aad52c5169a956ed3fc162cd04e4619f33f1167ec31d1727c590f56347f5d"

def locked_contract():
    raw=CONTRACT_PATH.read_bytes()
    observed=hashlib.sha256(raw).hexdigest()
    if observed != APPROVED_SHA256:
        raise RuntimeError("FROZEN CONTRACT CHANGED: obtain explicit user confirmation before revising the pipeline, 6 sections, schedule or publication policy")
    return json.loads(raw.decode("utf-8"))

def expected_headings():
    return [f"{x['number']}｜{x['name']}" for x in locked_contract()['sections']]
