\# Frontend work rules

\- Only edit files in app/ui/ and .streamlit/config.toml.

\- Do not rename or change functions in services/, models/, utils/,

&#x20; sql\_scripts/ or tests/.

\- Login and role access must behave exactly as before.

\- After each change run: python -m pytest tests/ -v (must stay green).

\- Reset demo data with: python scripts/reset\_demo.py

\- Demo logins: doctor\_smith/doctor123, pharmacist\_jane/pharmacist123,

&#x20; admin\_officer/admin123

\- Design target: light dashboard, see the screenshots in docs/design/

