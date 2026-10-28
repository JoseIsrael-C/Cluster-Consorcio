#!/usr/bin/env python3
"""Minimal third-party verifier for consortium certificates (the three checks of Section 3.2 of the paper).

  1. Registry:  verify(h) on the read-only gateway returns valid, the issuing campus i and the issuance time t.
                h = keccak256 of the signed revision of the PDF, i.e. the bytes up to the end of the ByteRange of
                the first (issuing) signature, so later incremental updates (e.g. long-term-validation data) do
                not change h.
  2. Signature: the PAdES signature is intact, chains to the configured X.509 trust anchor, carries an RFC 3161
                timestamp that also chains to a trust anchor and is not later than t, and the signer certificate
                is not revoked (CRL/OCSP; hard-fail by default).
  3. Binding:   the SHA-256 fingerprint of the signer certificate (DER) equals signingCertAt(i, t) on chain.

The certificate is accepted only if all three checks pass (exit code 0); otherwise the exit code is 1.
The verifier never sends the PDF or any personal data anywhere: only h and (i, t) are used in read-only calls.

Usage:
  python verify_certificate.py titulo.pdf --rpc http://gateway:8545 --contract 0x... \
      --trust-anchor ac-sat.pem [--tsa-anchor tsa-root.pem] [--crl ac.crl] [--no-fetch] [--soft-fail] [--json]
"""
import argparse
import hashlib
import json
import sys
from datetime import timedelta

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from asn1crypto import pem, x509 as asn1_x509
from web3 import Web3

ABI = [
    {"type": "function", "name": "verify", "stateMutability": "view",
     "inputs": [{"name": "h", "type": "bytes32"}],
     "outputs": [{"name": "valid", "type": "bool"}, {"name": "id", "type": "uint256"},
                 {"name": "issuer", "type": "uint8"}, {"name": "current", "type": "uint8"},
                 {"name": "at", "type": "uint64"}]},
    {"type": "function", "name": "signingCertAt", "stateMutability": "view",
     "inputs": [{"name": "campusId", "type": "uint8"}, {"name": "at", "type": "uint64"}],
     "outputs": [{"name": "fingerprint", "type": "bytes32"}]},
]
TS_TOLERANCE = timedelta(minutes=5)  # clock skew allowed between the TSA and the block timestamp


def load_certs(path):
    data = open(path, "rb").read()
    if pem.detect(data):
        return [asn1_x509.Certificate.load(der) for _, _, der in pem.unarmor(data, multiple=True)]
    return [asn1_x509.Certificate.load(data)]


def load_crl(path):
    data = open(path, "rb").read()
    if pem.detect(data):
        return [der for _, _, der in pem.unarmor(data, multiple=True)]
    return [data]


def first_signature(pdf_bytes):
    import io
    reader = PdfFileReader(io.BytesIO(pdf_bytes))
    sigs = reader.embedded_signatures
    if not sigs:
        return reader, None
    first = min(sigs, key=lambda s: s.signed_revision)
    return reader, first


def document_hash(pdf_bytes, sig):
    """keccak256 of the bytes covered by the first signature's revision (end of its ByteRange)."""
    br = [int(x) for x in sig.byte_range]
    end = br[2] + br[3]
    return Web3.keccak(pdf_bytes[:end])


def verify(pdf_path, rpc, contract, anchors, tsa_anchors=None, crls=None, fetch=True, soft_fail=False):
    pdf = open(pdf_path, "rb").read()
    report = {"file": pdf_path, "checks": {}, "accepted": False}
    reader, sig = first_signature(pdf)
    if sig is None:
        report["checks"]["registry"] = {"ok": False, "reason": "the PDF has no signature"}
        return report
    h = document_hash(pdf, sig)
    report["hash"] = h.hex()

    # ---- check 1: registry
    w3 = Web3(Web3.HTTPProvider(rpc))
    c = w3.eth.contract(address=Web3.to_checksum_address(contract), abi=ABI)
    valid, cid, issuer, current, at = c.functions.verify(h).call()
    report["checks"]["registry"] = {
        "ok": bool(valid), "id": cid, "issuer": issuer, "currentCampus": current, "issuedAt": at,
        "reason": None if valid else ("hash not registered" if cid == 0 else "revoked or issued while compromised"),
    }

    # ---- check 2: PAdES signature, trust anchor, timestamp, revocation
    mode = "soft-fail" if soft_fail else "hard-fail"
    crl_list = crls or []
    vc = ValidationContext(trust_roots=anchors, crls=crl_list, allow_fetching=fetch, revocation_mode=mode)
    tvc = ValidationContext(trust_roots=tsa_anchors or anchors, crls=crl_list, allow_fetching=fetch,
                            revocation_mode=mode)
    reasons = []
    try:
        st = validate_pdf_signature(sig, signer_validation_context=vc, ts_validation_context=tvc)
        if not (st.intact and st.valid):
            reasons.append("signature not intact or cryptographically invalid")
        if not st.trusted:
            reasons.append("signer certificate does not chain to the trust anchor")
        if st.revoked:
            reasons.append("signer certificate revoked")
        ts = st.timestamp_validity
        ts_time = None
        if ts is None:
            reasons.append("no RFC 3161 signature timestamp")
        else:
            ts_time = ts.timestamp
            if not (ts.intact and ts.valid and ts.trusted):
                reasons.append("timestamp not valid or not trusted")
            elif valid and ts_time.timestamp() > at + TS_TOLERANCE.total_seconds():
                reasons.append("timestamp later than the on-chain issuance time")
        if not st.bottom_line and not reasons:
            reasons.append("signature rejected: " + st.summary())
        report["checks"]["signature"] = {
            "ok": not reasons, "signer": sig.signer_cert.subject.human_friendly,
            "timestamp": ts_time.isoformat() if ts_time else None, "coverage": str(st.coverage),
            "reason": "; ".join(reasons) or None,
        }
    except Exception as e:  # malformed signature, unreadable CMS, ...
        report["checks"]["signature"] = {"ok": False, "reason": f"validation error: {e}"}

    # ---- check 3: binding of the signer certificate to the issuing campus at time t
    fp = hashlib.sha256(sig.signer_cert.dump()).digest()
    if valid:
        reg = c.functions.signingCertAt(issuer, at).call()
        ok = reg == fp
        report["checks"]["binding"] = {
            "ok": ok, "signerFingerprint": "0x" + fp.hex(), "registered": "0x" + reg.hex(),
            "reason": None if ok else "signer certificate is not the one registered for the issuing campus at t",
        }
    else:
        report["checks"]["binding"] = {"ok": False, "signerFingerprint": "0x" + fp.hex(),
                                       "reason": "no valid registry entry to bind to"}

    report["accepted"] = all(v["ok"] for v in report["checks"].values())
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--rpc", required=True, help="read-only gateway JSON-RPC URL")
    ap.add_argument("--contract", required=True, help="CertificateConsortium address")
    ap.add_argument("--trust-anchor", required=True, action="append", help="PEM/DER root certificate(s)")
    ap.add_argument("--tsa-anchor", action="append", help="root(s) for the timestamp authority (default: trust anchors)")
    ap.add_argument("--crl", action="append", help="CRL file(s) to use in addition to fetching")
    ap.add_argument("--no-fetch", action="store_true", help="do not fetch CRL/OCSP over the network")
    ap.add_argument("--soft-fail", action="store_true", help="accept when revocation information is unavailable")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    anchors = [c for p in a.trust_anchor for c in load_certs(p)]
    tsa = [c for p in a.tsa_anchor for c in load_certs(p)] if a.tsa_anchor else None
    crls = [x for p in (a.crl or []) for x in load_crl(p)]
    r = verify(a.pdf, a.rpc, a.contract, anchors, tsa, crls, fetch=not a.no_fetch, soft_fail=a.soft_fail)
    if a.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        for name, chk in r["checks"].items():
            print(f"[{'PASS' if chk['ok'] else 'FAIL'}] {name}" + (f": {chk['reason']}" if chk.get("reason") else ""))
        print("ACCEPTED" if r["accepted"] else "REJECTED")
    sys.exit(0 if r["accepted"] else 1)


if __name__ == "__main__":
    main()
