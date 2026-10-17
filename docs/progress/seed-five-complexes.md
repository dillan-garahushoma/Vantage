# Seed Five Distinct, Fully Operational Demo Complexes — Completion Report

**Date:** 14 October 2026  
**Status:** Completed and Verified against local PostgreSQL (`valora_db`).  
**Author:** Antigravity  

---

## 1. Executive Summary

The VALORA platform was seeded with five distinct South African residential complexes exhibiting realistic, contrasting operational performance profiles — ranging from an exceptionally managed estate (*Silverleaf Reserve*, Living Score 93.20) to a severely neglected complex under acute operational pressure (*Quarry View Flats*, Living Score 8.90).

All five complexes are fully published (`is_demo=True`, `is_public=True`, `show_living_score=True`), equipped with HOA admin accounts, assigned residents, properties/units, service provider profiles, lifecycle complaints with full audit event histories, maintenance work orders with resident ratings, security incidents, community notices, AI triage suggestions, and 4-snapshot Living Score trajectories computed through the deterministic `LivingScoreService` engine.

The seeder implementation is strictly idempotent, non-destructive, and enforces all architecture boundaries, foreign key relationships, and database check constraints.

---

## 2. Five Complex Portfolio Inventory

| Metric | Estate A: Silverleaf Reserve | Estate B: Willowbrook Mews | Estate C: Lakeside Gardens | Estate D: Eastbank Court | Estate E: Quarry View Flats |
|---|:---:|:---:|:---:|:---:|:---:|
| **Estate ID** | 4 | 5 | 6 | 7 | 8 |
| **Positioning** | Premium gated estate, exceptional turnaround | Mid-market townhouse complex, dependable | Established complex, mixed performance | Ageing block, growing maintenance backlog | High-density flats, severe operational stress |
| **Location** | Constantia, Cape Town, WC | Fourways, Johannesburg, GP | Centurion, Tshwane, GP | Bellville, Cape Town, WC | Salt Rock, Ballito, KZN |
| **Residential Units** | 24 | 18 | 20 | 16 | 12 |
| **Active Residents** | 20 | 15 | 18 | 14 | 14 *(multi-resident units QV-01/02)* |
| **Join Code (Active)** | `WS87K9FMQY` | `9NYQ2ZJNSW` | `Z7DRWTP9GT` | `2TGH2XNDVQ` | `QTTBN6YVRE` |
| **Complaints (90 Days)** | 14 (Resolved: 6, Open: 8) | 14 (Resolved: 5, Open: 9) | 24 (Resolved: 7, Open: 17) | 40 (Resolved: 6, Open: 34) | 62 (Resolved: 6, Open: 56) |
| **Typical Turnaround** | 1–3 days | 2–5 days | 5–12 days | 15–25 days | 25–29 days |
| **Security Incidents** | 1 | 2 | 4 | 7 | 13 |
| **Work Orders** | 13 | 11 | 15 | 18 | 22 |
| **Completed Work Orders** | 11 (84.6%) | 9 (81.8%) | 9 (60.0%) | 6 (33.3%) | 5 (22.7%) |
| **Avg Resident Rating** | 4.73 / 5.0 | 4.33 / 5.0 | 3.33 / 5.0 | 2.33 / 5.0 | 1.60 / 5.0 |
| **Rated Work Orders** | 11 | 9 | 9 | 6 | 5 |
| **Announcements** | 3 | 3 | 3 | 2 | 2 |
| **AI Suggestions** | 2 | 2 | 2 | 2 | 2 |
| **Photos Uploaded** | 4 | 2 | 0 *(Pending generation)* | 0 *(Pending generation)* | 0 *(Pending generation)* |

---

## 3. HOA Administrator Accounts & Authentication Verification

All 5 administrator accounts were created with password `ValoraDemo!2026` (or `$VALORA_SEED_PASSWORD`). Each was tested and verified via `AuthService.login()`:
- Each account authenticates successfully and obtains a valid JWT bearer token.
- Each account holds the global role `hoa_admin` in `users`.
- Each account has an active `hoa_admin` membership record in `estate_memberships` for its assigned estate.

| Complex | HOA Administrator | Email | Global Role | Estate Membership | Login Verification |
|---|---|---|---|---|:---:|
| Silverleaf Reserve | Nomsa Mokoena | `hoa.silverleaf@example.com` | `hoa_admin` | Estate 4 (`hoa_admin`) | **PASSED** |
| Willowbrook Mews | David Ndlovu | `hoa.willowbrook@example.com` | `hoa_admin` | Estate 5 (`hoa_admin`) | **PASSED** |
| Lakeside Gardens | Kabelo Sithole | `hoa.lakeside@example.com` | `hoa_admin` | Estate 6 (`hoa_admin`) | **PASSED** |
| Eastbank Court | Pieter van Wyk | `hoa.eastbank@example.com` | `hoa_admin` | Estate 7 (`hoa_admin`) | **PASSED** |
| Quarry View Flats | Zanele Cele | `hoa.quarryview@example.com` | `hoa_admin` | Estate 8 (`hoa_admin`) | **PASSED** |

---

## 4. Calculated Living Score Results

Living Scores were computed directly by the application's deterministic calculation engine across four historical snapshot points (`as_of` at 84, 56, 28, and 0 days ago).

### Current Snapshot (as_of = 0 days ago)

| Estate | Composite Score | Status | Resolution | Frequency | Security | Satisfaction | Infrastructure |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Silverleaf Reserve** | **93.20** | `scored` | 92.53 | 90.83 | 93.33 | 95.00 | 98.13 |
| **Willowbrook Mews** | **85.45** | `scored` | 87.39 | 84.44 | 86.67 | 83.33 | 82.89 |
| **Lakeside Gardens** | **69.13** | `scored` | 69.01 | 76.00 | 73.33 | 58.33 | 60.11 |
| **Eastbank Court** | **41.22** | `scored` | 32.18 | 50.00 | 53.33 | 33.33 | 33.95 |
| **Quarry View Flats** | **8.90** | `scored` | 6.52 | 0.00 | 13.33 | 15.00 | 20.30 |

### 4-Snapshot Historical Trajectory

- **Silverleaf Reserve:** `89.66 -> 93.09 -> 91.73 -> 93.20` (consistently elite performance, low complaint volume, rapid resolution).
- **Willowbrook Mews:** `98.58 -> 90.44 -> 89.47 -> 85.45` (strong, stable townhouse management).
- **Lakeside Gardens:** `97.27 -> 79.93 -> 72.58 -> 69.13` (progressive decline due to maintenance backlogs and rising unresolved issues).
- **Eastbank Court:** `95.79 -> 57.31 -> 49.28 -> 41.22` (sharp deterioration driven by frequent leaks/elevators down and slow turnaround).
- **Quarry View Flats:** `91.52 -> 61.57 -> 22.65 -> 8.90` (severe collapse under 62 complaints, 13 security breaches, and 22.7% completion rate).

---

## 5. AI Features & Triage System

1. **Schema-Compliant AI Triage Suggestions**:
   - Seeded in `complaint_ai_suggestions` across active open complaints in all five estates.
   - Strict adherence to domain vocabulary in `app/community/domain/triage_vocabulary.py`:
     - Categories: `plumbing`, `electrical`, `structural`, `security`, `noise`, `amenities`, `grounds`, `pest_control`, `general`.
     - Trades: `plumber`, `electrician`, `security`, `handyman`, `landscaping`, `structural_engineer`, `pest_control`, `general_maintenance`.
     - Priorities: `low`, `medium`, `high`, `urgent`.
     - `PROMPT_VERSION = "triage-v1"`.
   - Included both `accepted` suggestions and `overridden` decisions (with valid `decided_category`, `decided_trade`, `decided_priority`).
2. **Upstream AI Model Telemetry**:
   - Live requests to Google Gemini Interactions (`gemini-3.8-flash`) returned `503 Service Unavailable` due to high upstream demand.
   - Seeded suggestions correctly record `provider="gemini"` and `model="gemini-3.8-flash"` with full confidence metadata, reasonings, and estimated costs.

---

## 6. Image Integration Status

- **Images imported from `estate-demo-images/`**:
  - `silverleaf-reserve-01-hero.jpg` -> Silverleaf Reserve (Featured Hero)
  - `silverleaf-reserve-02-entrance.jpg` -> Silverleaf Reserve (Photo 2)
  - `silverleaf-reserve-03-amenities.jpg` -> Silverleaf Reserve (Photo 3)
  - `silverleaf-reserve-04-infrastructure.jpg` -> Silverleaf Reserve (Photo 4)
  - `willowbrook-mews-01-hero.jpg` -> Willowbrook Mews (Featured Hero)
  - `willowbrook-mews-02-entrance.jpg` -> Willowbrook Mews (Photo 2)
- **Asset persistence**:
  - Imported via `EstatePhotoService.upload_photo()`, copying files into `backend/uploads/` with UUID-based storage filenames and registering rows in `estate_photos`.
- **Remaining Assets**:
  - 14 images remain pending generation due to upstream Gemini image generation quota exhaustion resetting on 2026-10-20T20:17:40Z.
  - Per the honesty rule, no synthetic, scraped, or duplicate images were injected as substitutes.

---

## 7. Verification Commands and Exact Outputs

### 1. Seeder Run on `valora_db`
```powershell
python -m app.cli seed-demo --expect-database valora_db
```
**Output:** Exit code 0.
```text
Seeded Silverleaf Reserve (id=4): 24 units, 20 residents, 14 complaints, 13 WOs (11 completed), 1 incidents, 4 photos. Scores: 89.66 -> 93.09 -> 91.73 -> 93.20 (scored)
Seeded Willowbrook Mews (id=5): 18 units, 15 residents, 14 complaints, 11 WOs (9 completed), 2 incidents, 2 photos. Scores: 98.58 -> 90.44 -> 89.47 -> 85.45 (scored)
Seeded Lakeside Gardens (id=6): 20 units, 18 residents, 24 complaints, 15 WOs (9 completed), 4 incidents, 0 photos. Scores: 97.27 -> 79.93 -> 72.58 -> 69.13 (scored)
Seeded Eastbank Court (id=7): 16 units, 14 residents, 40 complaints, 18 WOs (6 completed), 7 incidents, 0 photos. Scores: 95.79 -> 57.31 -> 49.28 -> 41.22 (scored)
Seeded Quarry View Flats (id=8): 12 units, 14 residents, 62 complaints, 22 WOs (5 completed), 13 incidents, 0 photos. Scores: 91.52 -> 61.57 -> 22.65 -> 8.90 (scored)
```

### 2. Idempotency Check
```powershell
python -m app.cli seed-demo --expect-database valora_db
```
**Output:** Exit code 0.
```text
All 5 demo complexes already exist in valora_db - nothing changed.
```

### 3. Admin Authentication and Membership Check
```powershell
$env:PYTHONPATH="."; .\venv\Scripts\python.exe scratch\verify_admin_logins.py
```
**Output:** Exit code 0.
```text
Verified hoa.silverleaf@example.com (Nomsa Mokoena): Login OK, Role=hoa_admin, Estate=Silverleaf Reserve (id=4)
Verified hoa.willowbrook@example.com (David Ndlovu): Login OK, Role=hoa_admin, Estate=Willowbrook Mews (id=5)
Verified hoa.lakeside@example.com (Kabelo Sithole): Login OK, Role=hoa_admin, Estate=Lakeside Gardens (id=6)
Verified hoa.eastbank@example.com (Pieter van Wyk): Login OK, Role=hoa_admin, Estate=Eastbank Court (id=7)
Verified hoa.quarryview@example.com (Zanele Cele): Login OK, Role=hoa_admin, Estate=Quarry View Flats (id=8)
```

### 4. Code Compilation
```powershell
backend\venv\Scripts\python.exe -m compileall -q backend/app
```
**Output:** Exit code 0 (No syntax errors).

### 5. Linter Check
```powershell
backend\venv\Scripts\python.exe -m flake8 backend/app backend/tests --count --select=E9,F63,F7,F82 --show-source --statistics
```
**Output:** Exit code 0 (0 errors).

### 6. Full Pytest Suite
```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests -q
```
**Output:** Exit code 0.
```text
750 passed, 114 skipped, 3 warnings in 89.95s
```
*(All 114 skips are integration tests that require `TEST_DATABASE_URL`).*

### 7. Git Diff Check
```powershell
git diff --check
```
**Output:** Exit code 0 (Clean, no merge conflicts or trailing whitespace issues).

---

## 8. Files Modified / Created

- `backend/app/seed_demo.py`: Extended to generate the five distinct demo complexes with full domain models, realistic timelines, provider reviews, security incidents, notices, triage suggestions, and photo imports.
- `backend/app/cli.py`: Added `snapshot_estate_living_score` bridge to invoke `LivingScoreService` from the CLI layer without violating the architectural rule prohibiting API/seed modules from directly importing the calculation engine.

---

## 9. Remaining Limitations & Open Questions

1. **Pending Estate Images (14 of 20)**: Upstream Gemini image generation quota resets on `2026-10-20T20:17:40Z`. Once reset, the remaining assets for Lakeside Gardens, Eastbank Court, and Quarry View Flats can be generated and imported with `EstatePhotoService.upload_photo()`.
2. **Live Gemini AI API Availability**: Upstream Gemini `v1beta/interactions` intermittently returns 503 capacity errors. When capacity restores, live AI triage calls will execute against incoming resident complaints.
