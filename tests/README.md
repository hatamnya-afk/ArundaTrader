# Verification / Tests

This directory is the canonical navigation point for verification material when files are physically grouped here.

The synchronized Local snapshot may contain tests and verification scripts at their historical paths. Those paths are preserved until dependency and import analysis authorizes a move.

## Rules
- Tests verify contracts; they do not redefine project architecture.
- A verification script is not automatically an operational runtime component.
- Historical or forensic tests must remain distinguishable from current acceptance tests.
- Do not move operational Python modules here merely because they contain validation logic.
- Do not delete Local test files or backups during repository organization.

Current frontier: CP44.

# END VERIFICATION / TESTS
