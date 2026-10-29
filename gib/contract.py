"""Explicit user-approved editorial/schedule contract; changes fail tests until authorized."""
import hashlib
import json
from pathlib import Path

CONTRACT_PATH=Path(__file__).resolve().parents[1]/"config"/"frozen_contract.json"
APPROVED_SHA256="02877e79bca8d69629f261567d5d9ad4d60777ca28b7255ff925afdccc1b741f"

def locked_contract():
    raw=CONTRACT_PATH.read_bytes()
    observed=hashlib.sha256(raw).hexdigest()
    if observed != APPROVED_SHA256:
        raise RuntimeError("FROZEN CONTRACT CHANGED: obtain explicit user confirmation before revising the pipeline, 6 sections, schedule or publication policy")
    return json.loads(raw.decode("utf-8"))

def expected_headings():
    return [f"{x['number']}｜{x['name']}" for x in locked_contract()['sections']]
