# Deploying to Streamlit Community Cloud (free)

Result: a public URL like `https://kol-engine.streamlit.app` for LinkedIn and your CV.

## 1. Prepare the repo
```bash
cd kol-influence-engine
python scripts/make_sample_fixture.py        # ensures data/sample/ exists
# OPTIONAL but recommended for a fast, real demo:
python scripts/build_cache.py                # builds data/cache/ from live data
```
If you build the live cache and want it served on the public app, commit it:
```bash
# edit .gitignore and remove the line "data/cache/", then:
git add -f data/cache
```

## 2. Push to GitHub
```bash
git init
git add .
git commit -m "KOL Influence Mapping Engine"
git branch -M main
git remote add origin https://github.com/<you>/kol-influence-engine.git
git push -u origin main
```
The repo must be **public** for the free Streamlit tier.

## 3. Deploy
1. Sign in at **https://share.streamlit.io** with GitHub.
2. **New app** → select your repo → branch `main` → main file path `app.py`.
3. **Deploy**. First build installs `requirements.txt` (a couple of minutes).

## 4. (Optional) build live data on the server
If you did NOT commit `data/cache/`, the app runs on the sample fixture. To load
real data on the server, either commit the cache (step 1) or add a one-off run of
`scripts/build_cache.py` — note Streamlit Cloud has internet access, so the live
ingestion works there.

## Notes
- No secrets required for the public demo (briefs are pre-generated and cached).
- If you later wire in an LLM for briefs, add the key under **App → Settings → Secrets**, never in code.
- Free tier sleeps after inactivity; the first visit after a nap takes ~30s to wake.
