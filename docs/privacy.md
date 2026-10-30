# Privacy and confidentiality

- The application stores project records and any ingested text in a local SQLite file.
- New database files are restricted to owner access when filesystem permissions are available; content is **not encrypted** by the application.
- Search queries are sent to the configured public metadata provider and stored in local search history.
- Ingested documents and their extracted text remain local. No manuscript-upload, OCR service, analytics, telemetry, or AI model endpoint is integrated.
- Provider requests use public APIs and may log queries according to provider policy. Do not include patient identifiers or confidential terms in public queries.
- Treat database files, WAL sidecars, exports, and backups as confidential research material.
- For peer-review manuscripts, unpublished data, or patient-level information, check institutional, journal, consent, and provider requirements before any external processing.

The user remains responsible for secure storage, access control, retention, lawful basis, and deletion of research data.
