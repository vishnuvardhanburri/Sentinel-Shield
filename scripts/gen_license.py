"""
Sentinel Shield v2 — Master License Generator (Xavira Tech Labs Internal)
Generates hardware-bound, ECC-signed license files for clients.
"""
import json
import base64
import hashlib
import os
from datetime import datetime, timedelta
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("❌ Critical: Run 'pip install cryptography' to use the license generator.")
    exit(1)

LICENSE_DIR = "licenses"
PRIVATE_KEY_FILE = "master_private.pem"
PUBLIC_KEY_FILE = "master_public.pem"

def ensure_master_keys():
    """Generates the Xavira Tech Labs master signing keys if they don't exist."""
    if not os.path.exists(PRIVATE_KEY_FILE):
        print("🔑 Generating new Master signing keys...")
        private_key = ec.generate_private_key(ec.SECP256K1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(PRIVATE_KEY_FILE, "wb") as f: f.write(pem)

        public_key = private_key.public_key()
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(PUBLIC_KEY_FILE, "wb") as f: f.write(pub_pem)
    
    # Load keys
    with open(PRIVATE_KEY_FILE, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    with open(PUBLIC_KEY_FILE, "rb") as f:
        pub = serialization.load_pem_public_key(f.read())
    return priv, pub

def issue_license(client_name: str, machine_id: str, days_valid: int = 365, seats: int = 10):
    """Generates a cryptographically signed .sntl license file."""
    priv, _ = ensure_master_keys()
    
    expiry = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    license_data = {
        "client": client_name,
        "machine_id": machine_id,
        "expiry": expiry,
        "seats": seats,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }
    
    # Create canonical payload for signing
    payload = json.dumps(license_data, sort_keys=True).encode()
    
    # Digital Signature (Un-forgeable)
    signature = priv.sign(payload, ec.ECDSA(hashes.SHA256()))
    
    final_payload = {
        "license": license_data,
        "signature_b64": base64.b64encode(signature).decode()
    }
    
    filename = f"SNTL-{client_name.upper().replace(' ','_')[:10]}-{machine_id[:6]}.sntl"
    with open(filename, "w") as f:
        json.dump(final_payload, f, indent=2)
    
    print(f"\n✅ License Issued Successfully!")
    print(f"📄 File: {filename}")
    print(f"👤 Client: {client_name}")
    print(f"🖥️ Bound to Hardware: {machine_id}")
    print(f"⏳ Expires: {expiry}")
    print(f"🪪 IMPORTANT: Deliver {filename} to the client. Keep {PRIVATE_KEY_FILE} secret!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python gen_license.py <CLIENT_NAME> <MACHINE_ID> [DAYS] [SEATS]")
        print("Tip: Get Client Machine ID from their 'status' dashboard.")
    else:
        name = sys.argv[1]
        mid = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 365
        seats = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        issue_license(name, mid, days, seats)
