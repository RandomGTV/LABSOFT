# LabSoft — Medical Diagnostic Laboratory Information & Reporting System

**Author / Developer:** `RANDOM_GTV`  
**Version:** `v1.0.0 (Production Release)`  
**Platform:** Desktop Application (PyQt6 / Python) & Online Web App (HTML5 / Single Page Application)

---

## 🌟 Overview

**LabSoft** is a clinical laboratory information, reporting, and billing management software designed for diagnostic centres and medical laboratories. It features automated formula calculation engines, multi-style medical letterhead report generation with high-resolution logo integration, single-sheet HbA1c with clinical notes, thermal receipt billing, and WhatsApp dispatch.

---

## 🚀 Online Web App (Client Testing Experience)

The repository includes a complete, interactive client testing single-page web app located at `index.html`. It runs directly in any modern browser without needing a backend server and saves state locally using `localStorage`.

### Live GitHub Pages Hosting Instructions

To host this web application online on your GitHub account:

1. **Initialize Git & Commit**:
   ```bash
   git init
   git add .
   git commit -m "LabSoft v1.0.0 release by RANDOM_GTV"
   git branch -M main
   ```

2. **Link to your GitHub Repository**:
   ```bash
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
   git push -u origin main
   ```

3. **Enable GitHub Pages**:
   - Go to your repository on GitHub.
   - Click **Settings** (top tabs) → **Pages** (left sidebar).
   - Under **Build and deployment**:
     - **Source**: Select `Deploy from a branch`
     - **Branch**: Select `main` and folder `/ (root)`
     - Click **Save**.
   - Your online testing web app will be live at:
     ```
     https://<YOUR_GITHUB_USERNAME>.github.io/<YOUR_REPO_NAME>/
     ```

---

## 💻 Desktop Application Features (PyQt6)

- **Fast Patient Entry**: Mandatory fields (**Name \***, **Mobile \***, **Sex \***) with real-time validation.
- **Clinical Engine**: Automated formulas (e.g. Mean Blood Glucose from HbA1c `= 28.7 * HbA1c - 46.7`, Fasting & PP Glucose, Lipid profile Friedewald LDL).
- **Letterhead Report Styles**:
  - **Classic Design**: Soft ice-blue letterhead with circular emblem, bold navy lab title, subtitle badge, and right-hand contact block.
  - **Modern Design**: Deep navy clinical band with cyan accent stripe and white typography.
  - **Preprinted Mode**: 36mm blank top margin for physical letterhead stationery.
- **HbA1c Single-Sheet Format**: Special clinical note paragraph detailing long-term glycemic control (100–120 days), single fasting glucose correlation, retinopathy progression, and hemolytic factors.
- **Organized Patient Files**: Automatically saves generated PDF reports into clean patient folders (e.g. `patients/<Patient Name>/`).
- **Counter Billing & Receipts**: Real-time receipt calculation, balance tracking, and thermal print simulation.
- **About & Credits**: Press **F1** or click **ⓘ About** in the status bar to view system information and **RANDOM_GTV** author credits.

---

## 🛠️ Running Desktop App Locally

### Requirements
- Python 3.10+
- PyQt6, pytest, openpyxl, reportlab

### Launch
```bash
cd labsoft
python main.py
```

---

## 📜 Credits
Developed with care by **RANDOM_GTV**. All rights reserved.
