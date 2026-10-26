"""CI-only live trust-chain canary, without system roots or automatic retrieval."""

import hashlib
import json
import os
import socket
import ssl
from typing import Any, cast

from .downloader import HOSTS, HostPolicy
from .tls import ROOTS, create_context


def main() -> int:
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("DUSTY_CI_CA_CANARY") != "1":
        print("TLS chain canary requires explicit CI opt-in")
        return 2
    for host in sorted(HOSTS):
        HostPolicy().validate("https://" + host)
        for mode in ("default", "RSA", "ECC"):
            context = create_context(system=False)
            if mode != "default":
                context.maximum_version = ssl.TLSVersion.TLSv1_2
                context.set_ciphers(
                    "ECDHE-RSA-AES128-GCM-SHA256"
                    if mode == "RSA"
                    else "ECDHE-ECDSA-AES128-GCM-SHA256"
                )
            try:
                with socket.create_connection((host, 443), timeout=20) as raw:
                    with context.wrap_socket(raw, server_hostname=host) as connection:
                        # Verified against CPython 3.12.11/OpenSSL. This private
                        # chain API is CI diagnostics only, not downloader logic.
                        chain = cast(Any, connection)._sslobj.get_verified_chain()
                        fingerprints = [
                            hashlib.sha256(ssl.PEM_cert_to_DER_cert(c.public_bytes())).hexdigest()
                            for c in chain
                        ]
                        if fingerprints[-1] not in {v[1] for v in ROOTS.values()}:
                            raise ssl.SSLError("Verified chain did not end at a bundled root")
                        print(
                            json.dumps(
                                {"host": host, "profile": mode, "chain_sha256": fingerprints}
                            )
                        )
            except ssl.SSLError as exc:
                if mode != "default" and exc.reason == "SSLV3_ALERT_HANDSHAKE_FAILURE":
                    print(json.dumps({"host": host, "profile": mode, "not_served": True}))
                    continue
                print(
                    "TLS chain canary FAILED for "
                    + host
                    + " ("
                    + mode
                    + "): review bundled roots; no insecure fallback is permitted"
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
