# C05-ADR-0001 — Local fixture MVP
Status: Proposed (`DESIGN_ASSUMPTION`).
Context: menandai cacat visual pada satu jenis produk untuk review inspektur; research/data/provider setup for this concept is not verified.
Decision: local generated PNG + pixel baseline + held-out annotations; baseline offline, AI separately configured, human review before export. Vertex AI/Gemini vision adapter; Cloud Storage optional, tanpa kamera live.
Alternative: full external integration first. Rejected for the initial MVP because it adds data/credential dependencies before domain behavior is exercised.
Consequences: fixture pipeline can be built immediately; synthetic evaluation proves implementation properties only. External efficacy, licenses and cloud compatibility remain open. This does not guarantee hackathon eligibility or production readiness.
