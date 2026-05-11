# Known Limitations

This system is production-ready infrastructure but requires buyer-side deployment, integration, and operational ownership.

Sovereign Shield is acquisition-ready as a product foundation, but buyers should understand these deployment decisions before live regulated use.

1. Demo metrics are simulated validation data, not customer usage, revenue, or traction.
2. DPDP/GDPR/HIPAA language is implementation mapping, not legal certification.
3. mTLS enforcement expects Nginx, Envoy, or another trusted reverse proxy to terminate client certificates and forward verified certificate headers.
4. Redis is recommended for production multi-node revocation, rate limiting, and risk state. Local memory fallback is for localhost and single-node demos.
5. Off-box immutable ledger anchoring must be configured by the buyer using buyer-owned storage.
6. Local LLM quality, latency, and model governance depend on the buyer's Ollama model and hardware.
7. Cloud LLM adapters are present but optional; high-sensitivity routing should remain local unless buyer policy allows cloud processing.
8. Buyers should run their own penetration test, dependency review, and legal compliance review before processing real regulated data.
9. Cross-platform desktop and mobile builds require buyer-owned signing, notarization, app-store, and certificate-pinning configuration before external distribution.
