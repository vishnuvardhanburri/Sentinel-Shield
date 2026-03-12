# Sentinel Shield v1.3 | Technical Security Architecture by VishnuLabs
**Elite Standard: Military-Grade Hardware-Bound Data Protection**

---

## 1. Executive Summary
Sentinel Shield is designed with a "Privacy-First, Security-Always" architecture. It ensures that 100% of analyzed data stays within your local environment, protected by encryption standards used by global financial and defense institutions.

## 2. The Multi-Layer Defense (Human Explanation)
Imagine a bank vault that doesn't just need a key, but is physically welded to the floor of your building. Even if someone steals the vault, they cannot open it without the building it belongs to.
*   **Layer 1 (The Redaction)**: Before anything is stored, we "black out" sensitive details (SSNs, medical codes).
*   **Layer 2 (The Vault)**: Everything is then encrypted. Even if someone hacks your computer files, they only see a garbled mess of characters.
*   **Layer 3 (The Hardware Lock)**: The encryption key is mathematically tied to your specific machine. It cannot be moved.

---

## 3. Technical Implementation (Auditor View)

### A. AES-256 Encryption Strategy
We use **AES-256 (GCM Mode)** for data-at-rest. Unlike standard encryption, GCM provides "Authenticated Encryption," ensuring that if even a single bit of the file is tampered with, the system will reject it.

### B. Hardware-Bound Key Derivation (PBKDF2)
The master encryption key is never stored on disk. It is derived at runtime using:
1.  **Machine UUID**: A unique identifier tied to your hardware motherboard.
2.  **SHA-256 Salting**: A cryptographically random buffer (salt) stored locally.
3.  **100,000 Iterations**: We use the PBKDF2 function with 100,000 hashing rounds to make "Brute Force" attacks computationally impossible ($15,000 value safeguard).

### C. Cross-Platform Parity
Whether running on **Python (Mac/Linux)** or **Java (Enterprise)**, our logic follows the exact same cryptographic standard, ensuring that your data remains internally consistent across your entire firm's infrastructure.

---

## 4. Secure Life-Cycle Management
### A. Purge & Self-Destruct Logic
Sentinel Shield provides a `purge-index` command for high-sensitivity project rotations. This securely wipes the AI Intelligence Layer (Vector Store) and local cache while preserving the primary secured archives. This allows firms to "reset" the AI's memory without losing historical documentation.

### B. Anti-Cloning Protection
Because the vault is mathematically tied to the hardware UUID, copying the `sentinel-vault` folder to another machine results in a "Tamper Detection" failure. The system will refuse to decrypt the state or the archives, rendering the data useless to unauthorized parties.

---

## 4. Why This Costs $15,000
1.  **Zero Cloud Exposure**: Most "AI" tools send your data to OpenAI or Google. We do not.
2.  **Liability Shield**: If an audit happens, our "Compliance Audit CSV" proves you took "Exemplary Caution" with patient/client data.
3.  **Hardware Persistence**: The vault cannot be cloned or pirated. Your license is tied to your authorized hardware.

*Developed by VishnuLabs Engineering for Professional Excellence.*
