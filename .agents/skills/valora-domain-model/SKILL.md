---
name: valora-domain-model
description: Defines VALORA's core domain models, relationships, and operational event preservation rules. Use when creating or modifying database entities, schemas, or domain logic.
---

# VALORA Domain Model & Event Preservation

VALORA operates on a core thesis: **operational community data is an investment signal that directly influences property value.** The domain model reflects this relationship.

## Core Entities & Concepts

1. **Property Domain:**
   - **`Estate`**: The top-level residential complex or gated community (e.g. Amberfield Valley). Holds geographic, governance, and aggregate health metrics.
   - **`Property` / `Unit`**: Physical real estate units within an estate. Contains unit numbers, floor sizes, physical specs, and ownership associations.
   - **`Resident` / `User`**: Individuals occupying units or managing properties, linked with specific roles (`resident`, `hoa_admin`, `investor`, `estate_agent`, `service_provider`).

2. **Community & Operational Domain:**
   - **`Complaint`**: A logged operational issue (maintenance, security, noise, infrastructure) reported by a resident.
   - **`ComplaintEvent`**: State transition logs (Logged → Under Review → Assigned → In Progress → Resolved → Closed / Reopened). Captures timestamps and actors for resolution tracking.
   - **`ServiceProvider`**: Vetted third-party contractors registered to service estates, categorized by trade (plumbing, electrical, security, landscaping).
   - **`WorkOrder`**: Formal maintenance assignment dispatched to a `ServiceProvider` to resolve a `Complaint`. Tracks quotation, actual cost, time-to-dispatch, and time-to-completion.
   - **`Rating`**: Multi-dimensional feedback submitted by residents upon work order completion (quality, timeliness, professionalism).
   - **`SecurityIncident`**: Specialized complaint classification tracking perimeter breaches, access-control failures, or localized incidents.

3. **Property Health & Analytics Domain:**
   - **`LivingScore`**: Aggregate composite index (0–100) calculated per estate over a rolling 90-day window.
   - **`LivingScoreSnapshot`**: Immutable time-series snapshot capturing historical scores, sub-score breakdowns, and contributing operational factors.

## Crucial Rule: Operational Event Preservation

> **Historical operational data must never be casually updated in place, overwritten, or deleted.**

- **Immutability of Events**: Status transitions (`ComplaintEvent`, `LivingScoreSnapshot`, `Rating`) represent chronological reality. They are immutable time-series data points.
- **Future ML Feature Foundation**: Operational metrics (turnaround times, complaint densities, contractor performance) form the training feature store for downstream valuation and risk prediction models. Soft-delete and audit trails are mandatory.
