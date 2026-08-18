# CHANGELOG — KERDOSTAT

All notable changes to the Kerdostat backend system will be documented in this file.

## [1.0.0] - 2026-07-22

### Added
- **Autopilot (HOTL) Service**: Integrated automated trade proposal evaluation service (`app/services/autopilot.py`).
- **User Mode Endpoint**: Added `PATCH /user/mode` endpoint for toggling between `COPILOT` (HITL) and `AUTOPILOT` (HOTL).
- **JWT Mode Claim**: Embedded `mode` field into JWT access token payloads and refreshed user profiles.
- **Interrupt / Resume Flow**: Implemented `POST /trade/{id}/interrupt` and `POST /trade/{id}/resume` endpoints with audit log records.
- **SSL Fallback & Resilience**: Integrated SSL unverified context handling and `generate_mock_ohlcv()` dataset generator to handle network/API outages gracefully.
- **OWASP Input Validation**: Enhanced Pydantic schemas with positive numerical constraints and ticker symbol regex checks.
- **Alembic Migration**: Added migration script `e5f6g7h8i9j0_add_mode_to_users.py` for DB schema updates.
- **Testing Suite**: Added `tests/test_autopilot_interrupt.py` covering all TC-01 to TC-12 scenarios.
- **Documentation**: Generated `API_USER_GUIDE.md`, updated `README.md`, and exported `postman/kerdostat.postman_collection.json`.

### Changed
- Refactored `/signal/generate` to trigger Autopilot evaluation automatically when `user.mode == "AUTOPILOT"`.
- Updated `/trade/execute/{id}` to support executing proposals in `RESUMED` status.
