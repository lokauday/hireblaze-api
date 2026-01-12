# Duplicate Operation ID Fix

## Summary

Fixed duplicate FastAPI operation ID warnings by removing duplicate endpoint definitions.

## Issues Fixed

### 1. Duplicate `weekly_report` endpoint in `interview.py`
- **Location**: `app/api/routes/interview.py`
- **Issue**: Two identical `@router.get("/weekly-report")` endpoints defined (lines 259-297 and 299-339)
- **Fix**: Removed the first duplicate, kept the second version which includes proper float conversions for scores

### 2. Duplicate `generate_company_pack_endpoint` in `ai.py`
- **Location**: `app/api/routes/ai.py`
- **Issue**: Two identical `@router.post("/company-pack")` endpoints defined (lines 570-625 and 628-683)
- **Fix**: Removed the first duplicate, kept the second version

### 3. Missing import for `generate_company_pack`
- **Location**: `app/api/routes/ai.py`
- **Issue**: `generate_company_pack` was being called but not imported
- **Fix**: Added import: `from app.services.company_pack_service import generate_company_pack`

## Changes Made

### `app/api/routes/interview.py`
- Removed duplicate `weekly_report` function (first occurrence)
- Kept the improved version with proper float conversions

### `app/api/routes/ai.py`
- Added import: `from app.services.company_pack_service import generate_company_pack`
- Removed duplicate `generate_company_pack_endpoint` function (first occurrence)

## Verification

After these fixes, the warnings should be gone:
- ✅ No more "Duplicate Operation ID weekly_report_api_v1_interview_weekly_report_get"
- ✅ No more "Duplicate Operation ID generate_company_pack_endpoint_api_v1_ai_company_pack_post"

## Testing

Restart the server and verify:
1. No duplicate operation ID warnings in logs
2. `/api/v1/interview/weekly-report` endpoint works correctly
3. `/api/v1/ai/company-pack` endpoint works correctly
