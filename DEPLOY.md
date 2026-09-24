# Deploy the team demo

1. Create a GitHub repository and upload the contents of this folder at its root, including `.streamlit/config.toml`. A private repository keeps your source private. Do not upload `.env`, `.venv`, or `.streamlit/secrets.toml`.
2. Sign in at https://share.streamlit.io and connect the GitHub account that has access to the repository.
3. Choose **Create app → Yup, I have an app**. Select your repository, branch (usually `main`), and entrypoint `app.py`.
4. Under **Advanced settings**, choose Python **3.12**. To use a shared API key, enter the following in the **Secrets** field, replacing the placeholder directly in the hosting dashboard:

   ```toml
   OPENAI_API_KEY = "your-real-key"
   ```

   The app hides the key input when this secret or an environment key exists. Without a configured key, each viewer can enter their own key in the app. Keep the real key out of GitHub and chat.
5. Deploy and wait for the app to load. For team-only access, configure **Only specific people can view this app** in its sharing settings before sharing the link. Repository privacy and app viewer access are separate settings; verify both.
6. Open the live URL, upload a small text-based PDF, build its index, and ask a question with a known answer. Verify its quotation/page and test a question absent from the filing. Confirm viewer access using a separate browser session.

The hosted app uses memory for uploads, indexes and chat. Refreshes, restarts or session expiry can require uploading and indexing again. Each teammate has a separate Streamlit session; a shared API key pays for all their API requests. This is a small demo, without persistent storage or an application-level usage quota.

Official deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
