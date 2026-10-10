# Raw Strength Calisthenics — Employee Audit Manager

The complete Python application, including the historical audit seed data, is contained in `app.py`. `audit_seed.py` and `requirements.txt` are not needed in this version.

## Build the Windows executable with GitHub Actions

1. Create a private GitHub repository.
2. Upload `app.py` to the repository root.
3. Upload `.github/workflows/build-windows.yml` with that exact path.
4. Open **Actions** and run **Build Raw Strength Employee Audit Manager (Windows)**, or push to `main`/`master`.
5. After a successful run, download the `RawStrengthEmployeeAuditManager-Windows-EXE` artifact.
6. Extract it to obtain `RawStrengthEmployeeAuditManager.exe`.

Dependencies are installed on the GitHub Windows runner, not on the target PC. The EXE is intended to run offline after build. The GUI and Windows printing must still be tested on a Windows machine before production use.


Report Center supports three report types (Audit / EOD, Employee Attendance, Employee Details), each exportable to PDF, Word, or CSV. Choose Consolidated for all employees or Individual for one selected employee.
