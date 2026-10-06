---
name: valora-api-contracts
description: Enforces API design standards, DTO contracts, serialization rules, pagination, error schemas, and authorization for VALORA's FastAPI backend. Use when implementing or updating API endpoints and client communication.
---

# VALORA API Contracts & Standards

All client-server communication between the React frontend and FastAPI backend adheres strictly to `/api/v1` DTO-based conventions.

## 1. Versioning & Path Conventions
- All endpoints must be namespaced under `/api/v1/`.
- Paths must use lowercase hyphen-separated nouns for collections (e.g. `/api/v1/estates`, `/api/v1/complaints`, `/api/v1/work-orders`).

## 2. DTOs and Data Contracts
- Every request payload must be validated with an explicit Pydantic request schema (e.g. `CreateComplaintRequest`).
- Every response payload must return a defined Pydantic response schema (e.g. `ComplaintResponse`).
- Field naming must be consistent across the wire:
  - If frontend expects camelCase or specific identifiers (e.g., `id`), schemas must declare `Field(..., serialization_alias="id")` and `model_config = {"from_attributes": True, "populate_by_name": True}`.
  - Never leak raw ORM entity models directly across the API boundary.

## 3. Standardized Error Responses
- Errors must never return raw unhandled traceback HTML or unstructured strings.
- All HTTP errors must follow the standard envelope:
  ```json
  {
    "detail": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Complaint with ID 42 was not found.",
      "request_id": "req_01h9x3k5..."
    }
  }
  ```

## 4. Pagination & Filtering
- Collection endpoints must support standard query parameters:
  - `page`: 1-based page index (default: `1`)
  - `size`: items per page (default: `20`, max: `100`)
- Paginated responses must include metadata:
  ```json
  {
    "items": [...],
    "total": 142,
    "page": 1,
    "size": 20,
    "pages": 8
  }
  ```

## 5. Security & Authorization
- Endpoints requiring authentication must use JWT Bearer tokens: `Authorization: Bearer <token>`.
- Use FastAPI dependencies (`Depends(get_current_user)`, `Depends(require_roles(["hoa_admin"]))`) to guard routes before business execution.
- Validate estate-level and unit-level ownership to prevent Insecure Direct Object References (IDOR).
