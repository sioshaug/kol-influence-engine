# Getting Started — a plain-English guide

No coding experience needed. You'll run the app on your computer first, then put it online with a shareable link. Total time: about 15–20 minutes.

---

## Part A — Run it on your computer (~5 min)

**1. Open Terminal.**
Press `Cmd + Space`, type `Terminal`, press Enter. A text window opens — you'll paste a few lines here.

**2. Check Python is installed.** Type and press Enter:
```
python3 --version
```
- See a version like `Python 3.11`? Continue.
- "command not found"? Install Python from https://www.python.org/downloads/ (download the macOS installer, run it), then close and reopen Terminal.

**3. Go into the project folder.**
Type `cd` followed by a space, then **drag the `kol-influence-engine` folder from Finder into the Terminal window**, then press Enter. (Dragging avoids typing the long folder path.)

**4. Install the building blocks** (one-time). Paste, press Enter, wait ~1 min:
```
pip3 install -r requirements.txt
```

**5. Create demo data and launch:**
```
python3 scripts/make_sample_fixture.py
streamlit run app.py
```
Your browser opens with the app running. This is the **sample version** (fictional names) — good for a first look, not for sharing.

> To stop the app at any time: click the Terminal window and press `Ctrl + C`.

---

## Part B — Load the real Multiple Myeloma data (~5 min)

**6. Stop the app** (`Ctrl + C`), then build the live dataset:
```
python3 scripts/build_cache.py
```
This downloads real data from PubMed + ClinicalTrials.gov. A few minutes is normal. Then relaunch:
```
streamlit run app.py
```
The "sample data" warning disappears — you're now viewing **real experts**.

**Take 4 screenshots here** (you'll use them on LinkedIn and your CV):
1. Overview tab  2. Tiered list  3. Network map  4. A KOL brief

---

## Part C — Put it online (shareable link) (~10 min)

**7. Create a free GitHub account** at https://github.com (skip if you have one).

**8. Upload the project (no typing).**
- Install **GitHub Desktop**: https://desktop.github.com
- Open it, sign in, choose **File → Add Local Repository**, select the `kol-influence-engine` folder.
- Click **Publish repository**. **Untick "Keep this code private"** (it must be public for free hosting). Publish.

**9. Deploy the app.**
- Go to https://share.streamlit.io and sign in with GitHub.
- Click **New app** → choose your repo → set **Main file path** to `app.py` → **Deploy**.
- Wait a few minutes. You'll get a public link like `https://your-app.streamlit.app`.

**10. Share it.**
Open `docs/PORTFOLIO.md` for a ready-to-post LinkedIn write-up, resume bullets, and interview talking points. Attach your screenshots and paste your link.

---

## If something goes wrong
- Copy the red error text from Terminal and send it over — most issues are a one-line fix.
- Steps 4 and 6 need an internet connection.
- Want a different therapeutic area instead of multiple myeloma? See `docs/DEPLOY.md`.

---

## Quick reference (all commands)
```
python3 --version
cd  [drag the kol-influence-engine folder here]
pip3 install -r requirements.txt
python3 scripts/make_sample_fixture.py     # demo data
streamlit run app.py                        # run it
python3 scripts/build_cache.py              # real Multiple Myeloma data
```
