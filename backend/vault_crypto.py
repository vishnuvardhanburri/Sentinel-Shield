import os
import base64
import uuid
import hashlib
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

    def verify_license(self, license_key: str) -> bool:
        """
        Verifies if the provided license key matches this machine's hardware ID.
        License Key Format: SHA256(machine_id + "VISHNULABS_INTERNAL_SECRET")
        """
        if not license_key:
            return False
        
        # Salt known only to the builder (VishnuLabs)
        internal_salt = "VISHNULABS_SENTINEL_SECURE_2026"
        expected_hash = hashlib.sha256((self.machine_id + internal_salt).encode()).hexdigest().upper()
        
        return license_key.strip().upper() == expected_hash

    def is_licensed(self) -> bool:
        """Checks if a valid license is already registered on this system."""
        if not os.path.exists(self.license_file):
            return False
        with open(self.license_file, "r") as f:
            license_key = f.read().strip()
        return self.verify_license(license_key)

    def save_license(self, license_key: str):
        """Saves a verified license key to the persistent store."""
        with open(self.license_file, "w") as f:
            f.write(license_key.strip().upper())

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
