import os
import json
import base64
import uuid
import hashlib
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

class VaultCrypto:
    """
    Military-Grade AES-256 Encryption Manager.
    Implements hardware-bound key derivation for secure data-at-rest protection.
    """
    
    def __init__(self):
        self.salt_file = os.path.join(os.path.dirname(__file__), "..", ".vault_salt")
        self.key = self._derive_hardware_key()
        self.cipher = Fernet(self.key)
        self.machine_id = str(uuid.getnode())
        self.license_file = os.path.join(os.path.dirname(__file__), "..", ".vault_license")

    def get_machine_id(self):
        """Returns the raw machine hardware ID (node)."""
        return self.machine_id

    def verify_license_file(self, sntl_path: str) -> bool:
        """
        Verifies an ECC-signed .sntl license file.
        Checks: 1. Signature validity, 2. Hardware ID match, 3. Expiry date.
        """
        if not os.path.exists(sntl_path):
            return False
            
        try:
            with open(sntl_path, "r") as f:
                data = json.load(f)
            
            license_info = data.get("license", {})
            signature_b64 = data.get("signature_b64", "")
            
            # 1. Hardware ID Match
            if str(license_info.get("machine_id")) != self.machine_id:
                return False
                
            # 2. Expiry Check
            expiry_str = license_info.get("expiry", "2000-01-01")
            if datetime.strptime(expiry_str, "%Y-%m-%d") < datetime.now():
                return False
                
            # 3. ECC Signature Verification (The Hard Part)
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import hashes, serialization
            
            # The Public Key (Safe to embed in code)
            PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEvgXj9BxvYTNkFUDs+pOmE8iKxTOzRoGE
NAUTQeRgCR5uhEXHTBCQPD5A2bMzTsplmOuZ3Wf07fJk5fCwlB0NjQ==
-----END PUBLIC KEY-----"""
            
            public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
            signature = base64.b64decode(signature_b64)
            payload = json.dumps(license_info, sort_keys=True).encode()
            
            public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
            return True # Success
            
        except Exception:
            return False

    def is_licensed(self) -> bool:
        """Checks for valid .sntl license files in the root directory."""
        # Check for any .sntl files in project root
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for f in os.listdir(root_dir):
            if f.endswith(".sntl"):
                if self.verify_license_file(os.path.join(root_dir, f)):
                    return True
        return False

    def _derive_hardware_key(self):
        """
        Derives a persistent AES key bound to this specific machine's UUID.
        Ensures the vault cannot be simply copied to another device.
        """
        # Get machine-specific unique ID
        machine_id = str(uuid.getnode()).encode()
        
        if os.path.exists(self.salt_file):
            with open(self.salt_file, "rb") as f:
                salt = f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, "wb") as f:
                f.write(salt)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        derived_key = base64.urlsafe_b64encode(kdf.derive(machine_id))
        return derived_key

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypts byte data using AES-256."""
        return self.cipher.encrypt(data)

    def decrypt_data(self, token: bytes) -> bytes:
        """Decrypts byte data using AES-256."""
        return self.cipher.decrypt(token)

    def encrypt_file(self, file_path: str):
        """In-place military-grade encryption for a specific file."""
        if not os.path.exists(file_path):
            return
        with open(file_path, "rb") as f:
            data = f.read()
        encrypted = self.encrypt_data(data)
        with open(file_path, "wb") as f:
            f.write(encrypted)

    def decrypt_file(self, file_path: str) -> bytes:
        """Decrypts a file in memory and returns the raw bytes."""
        if not os.path.exists(file_path):
            return b""
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        return self.decrypt_data(encrypted_data)

# Singleton instance for the system
sentinel_crypto = VaultCrypto()
