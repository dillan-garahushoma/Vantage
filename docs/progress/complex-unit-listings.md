# Complex → unit listing refinement

## Delivered in this batch

- Kept `Estate` as the operational tenant boundary and `Property` as a unit inside that estate.
- Added HOA-managed public listing fields to a unit: title, description, amenities, publication flag and availability status. All new units default to private/not available.
- Added unit photo metadata and upload/read/delete routes. Files use the existing re-encode, thumbnail, EXIF/GPS stripping and random public-id pipeline.
- Public complex detail now returns only units that are explicitly published, currently available, complete, and associated with an explicitly published complex.
- The anonymous DTO intentionally excludes unit number, street address, resident/occupancy data and internal property identifiers.
- Public unit photos are served only while the parent complex is public and the unit is public and available. HOA members can preview unpublished unit photos through an estate-authorized endpoint.
- Added a public unit section to the complex detail page and HOA controls for unit copy, amenities, availability, publication and photos.
- Added integration and frontend coverage for the public listing contract, photo visibility and management form.

## Data-integrity decision

The five seeded complex names are not safe to merge automatically into one estate. They have different suburbs/cities/provinces, separate HOA admins, residents, units, complaints, work orders, incidents, announcements and Living Score histories. `estate_id` is the authorization and analytics tenant boundary. Moving those records would rewrite history and membership semantics, not merely change listing presentation.

This batch does **not** delete or merge those five estate records, and it does not modify a connected database. The current seed fixtures remain internal operational scenarios. To meet the requested “one complex with five units” showcase, select the intended parent complex and provide five actual unit-level image sets and listing details; then publish those five unit records under that estate. If the five named records are definitely synthetic and must be retired, perform that as a separately reviewed, reversible data migration with explicit mapping of memberships, complaints, work orders, incidents and score history.

## Validation

- Tests added/updated: `backend/tests/test_public_unit_listings_migration.py`, `backend/tests/test_onb_master_p2_photos_and_public.py`, `backend/tests/test_production_demo_isolation.py`, `frontend/src/routes/PublicEstateDetail.test.jsx`, `frontend/src/routes/Properties.test.jsx`.
- Test/build commands were not run in this GitHub-only editing environment. Treat all changed code and tests as **written, not run** until CI succeeds.
- Migration revision: `c7e2a9b4d6f1`, based on `e8c3a1f9d5b7`.
