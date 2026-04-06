# Next Session To-Do
## Active Task: Google OAuth 2.0 (Login with Google) Integration

**Planned Workflow (Approved):**
- **Existing Users (Admins, Technicians, Users):** Direct login via Google button straight to their respective dashboard. No password required.
- **Brand New Users:** Will be intercepted after Google Auth and asked to "Complete Profile" by providing their **Phone Number** and optional Address before their account is saved to the database.

**Next Immediate Steps for Tomorrow:**
1. Generate `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` using Google Cloud Console and add them to `.env` and Render variables.
2. Update database schema (`fixnear.sql` and `fixnear_pg.sql`) to add `oauth_provider` and `oauth_id` columns to `users` table.
3. Install `authlib` in Python.
4. Program backend routes (`/login/google` and `/login/google/authorize`).
5. Update `login.html` and create `complete_profile.html`.
