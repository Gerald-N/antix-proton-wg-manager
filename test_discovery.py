#!/usr/bin/env python3
import tempfile
import os
from pathlib import Path
from app.backend.wireguard import list_profiles
from app.utils.logging_setup import redact

def main():
    print("=== TESTING REDACTION ===")
    secret_text = "PrivateKey = super_secret_key_12345\nPresharedKey = another_secret\n"
    print(f"Original:\n{secret_text}")
    print(f"Redacted:\n{redact(secret_text)}")
    assert "super_secret" not in redact(secret_text)

    print("\n=== TESTING DISCOVERY ===")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # Valid profile
        (d / "valid-01.conf").write_text("[Interface]\nPrivateKey = test_key\nAddress = 10.0.0.2/32\n[Peer]\nPublicKey = peer_key\n")
        # Invalid profile (missing Peer)
        (d / "invalid-01.conf").write_text("[Interface]\nPrivateKey = test_key\n")
        # Not a conf file
        (d / "ignore.txt").write_text("hello")

        profiles = list_profiles(d)
        print(f"Discovered: {profiles}")
        assert profiles == ["valid-01"], f"Expected ['valid-01'], got {profiles}"
        
    print("\nAll tests passed.")

if __name__ == "__main__":
    main()
