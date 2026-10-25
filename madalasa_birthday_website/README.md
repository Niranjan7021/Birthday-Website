# Madalasa Birthday Website 💚

Flask + SQLite birthday surprise website, including 491 photos imported from the ZIP provided in chat, a birthday code page, Yes/No interaction, five questions, feedback, birthday letter, and a private admin dashboard.

## Run on Windows
1. Install Python 3.11+ from https://www.python.org/downloads/ and tick **Add Python to PATH**.
2. Double-click `run_windows.bat`. It installs dependencies and starts the app.
3. Open http://127.0.0.1:5000.
4. Birthday code: `7021`.
5. Private admin: http://127.0.0.1:5000/admin/login — username `admin`, password `NiraAdmin@2026`.

## Important before sharing online
- On first run, `.env` is copied from `.env.example`. Change `SECRET_KEY` and `ADMIN_PASSWORD` to unique values before hosting. Keep the admin password private; it is separate from birthday code `7021`.
- This project is set up for local testing. Public hosting needs HTTPS, a production WSGI server, and persistent storage for `instance/birthday.db` and `static/gallery/`.
- Visitors are told that selected interactions and submitted answers are stored for the private dashboard. Passwords and keystrokes are never logged.
- Do not delete `instance/birthday.db` if you want to keep saved feedback and answers.

## Admin features
Overview stats, Yes/No answers, question answers, feedback inbox with search/read/unread/delete/CSV export, and interaction history.
