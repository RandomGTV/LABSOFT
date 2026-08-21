# LabSoft — UI/UX redesign brief

For **New Mithra Medical Laboratory**, Chettiyankinar Road, Kuttippala, Kerala.
Written to be handed to Google Stitch, Claude Design, or a human designer.
Everything below describes the product as it works today; nothing here is
aspirational unless the section says so.

---

## 1. What the product is

Offline laboratory software for a small pathology lab. It registers a patient,
records which tests they are having, takes the money, captures the results,
prints or WhatsApps a PDF report, and keeps the ledger.

The **report PDF is the product**. Everything else exists to get to it quickly
and without a mistake.

- **One Windows PC**, kept at the reception counter. No server, no cloud login.
- Works with **no internet**. Backups are copied into a Google Drive folder and
  Drive uploads them whenever the connection returns.
- Data is a single SQLite file. ~170 tests seeded, ~24 of them auto-calculated.
- Desktop app (Python + PyQt6). Window opens at **1180 × 820**, commonly
  maximised on a **1366 × 768 or 1920 × 1080** monitor.
- **Mouse and keyboard.** No touch, no phone. Screen readers are not in use but
  keyboard-only operation is.

---

## 2. Who uses it

| | Who | What they do all day | What they need from the UI |
|---|---|---|---|
| **Reception** | Saheed | Registers walk-ins, takes payment, hands over reports | Speed on one screen. Finds a returning patient from three letters. Never has to scroll to find the money. |
| **Technologist** | Ritu | Types results off the analyser printout | Big, tab-ordered number boxes. Instant "that value is out of range" feedback. Never loses typing. |
| **Lab in-charge / owner** | Abdunnaser | Verifies, sends, checks the day's takings, edits the test master | Everything the other two have, plus Settings, Staff and Summaries. |

Each person signs in with a **username and a 4+ character PIN**. Permissions are
ticked per person; **tabs a person cannot use do not appear at all** (not greyed
out). An administrator has everything.

**Skill level:** competent with a keyboard, not with computers. The interface
must never require a guess. Error messages say what to do next, in plain
English, never a code.

**Pace:** a queue of people standing at the counter. A patient is registered in
under 30 seconds. Any redesign that adds a click to the common path is worse,
however much prettier it is.

---

## 3. The screens

Nine tabs across the top, then dialogs. Permission-gated tabs marked ⚿.

### 3.1 Job — the main screen (90% of all use)

One screen does registration, test selection, billing and result entry. This is
deliberate and must survive any redesign: the lab rejected a wizard.

Vertical bands, in this order:

1. **Header** — `Job — FARAS .M. Kutty` · `Report No 51359` · `Due 21-08-2026 · in 6h` · status pill (Registered / In progress / Ready to send / Sent ✓)
2. **Patient** — Name · Initial · Mobile · Sex · Age + unit · Referred by Dr · "Patient history" link
   - Under the boxes, one line: `Prints as: FARAS .M. Kutty` and/or `Still needed: a mobile number` (amber)
   - Typing 2+ letters drops a **suggestion list** of returning patients under the name box
3. **Tests** — a wrap of ~12 panel buttons (CBC, Lipid Profile, Thyroid Profile, Full Body Checkup…) plus a type-to-add search box. A "Repeat last visit's tests" button appears for returning patients.
4. **Bill** — big amount, paid/outstanding, `Print bill…` and `Make the bill`. Sits **above** results because money is settled before work starts.
5. **Results** — a scrolling grid, one row per test, grouped by heading:
   `Test name │ [value box] │ unit │ normal range │ [FLAG chip] │ ⋯`
   - Calculated rows are italic, grey, dashed, read-only
   - Flag chips: **HIGH** (red) **LOW** (blue) **CHECK** (amber) **N** (green)
   - A progress bar under the grid
6. **Actions** — New job · Save · Bill · Preview · … · `6 of 7 entered` · **Check & make report** (green, primary)
7. **Notes** — amber callouts explaining why the green button is disabled

### 3.2 Work Queue
Search box + table: Report No · Patient (name over mobile) · Tests · Received ·
Progress `4/6` · Status pill. Overdue rows in red. Buttons: Open · Preview ·
Send / reprint · Correct & reissue.

### 3.3 Patients
Search box, then a **two-pane split**: patient list on the left; on the right
their details, every visit as a file row, and an "Open folder" note. Each patient
has a real folder on disk holding their PDFs.

### 3.4 Doctors
Search + Add doctor / Edit / Remove / Show hidden, then a table:
Name · Profession · Hospital or clinic · Contact number · Qualification ·
Commission % · Patients sent.

### 3.5 Tests ⚿
Search + New test / Edit / Hide, then a table: Code · Name · Group · Specimen ·
Unit · Normal Value · Formula. Import from Excel/CSV, Panels, and a formula
editor that validates as you type.

### 3.6 Billing ⚿ (the ledger)
Search + date range + doctor filter + "Unpaid only", then a table of every job:
Report No · Date · Patient · Referred by · Charged · Discount · Net · Paid ·
Balance · Commission. Outstanding rows amber. A totals strip along the bottom.

### 3.7 Summaries ⚿
Day / month totals, dues, commission per doctor, test counts.

### 3.8 Staff ⚿
Search + Create login / Edit / Set a new PIN / Turn off access, then:
Name · Username · Account type · "May…" (the permission list in plain words).

### 3.9 Settings ⚿
Long scrolling form in grouped boxes: Laboratory details · Signatories · Report ·
Numbering · WhatsApp · **Appearance** (theme, letterhead design) · Printing ·
Images · Cloud backup · Staff · Data and backups.

### 3.10 Dialogs

| Dialog | What it is |
|---|---|
| **Sign in** | Full-screen teal gradient, white card, lab emblem, user dropdown, PIN field |
| **Report preview** | The rendered A4 page on a grey backdrop, page/zoom controls, Print · Save a copy · [detailed sheets] · Close · **Looks right — send** |
| **Bill / receipt preview** | Same treatment, one page. Print · Save as PDF · Send on WhatsApp |
| **Send report** | A file card (PDF chip, name, size), the phone number, an editable message, then Print · Open folder · Use WhatsApp Web · **Open WhatsApp && send** |
| **Bill** | Editable charge lines, discount, totals strip, payments list, add-payment row |
| **Test editor** | Code, name, group, specimen, unit, decimals, result type, rate, turnaround, formula (live-validated), a normal-values table, detailed-PDF toggle + interpretation |
| **Doctor editor / Staff editor** | Small forms; the staff one has a permission tick-list |

---

## 4. Key flows to design for

**A. Register → bill → results → send** (the whole day, one screen)
`F2` → type name → pick a suggestion or type fresh → panel button → the Bill band
→ result boxes fill from the top, Tab moves down → `F9` → preview → send.

**B. Returning patient**
Type `fmk` → suggestion appears → click → everything fills → "Repeat last visit's
tests" → results.

**C. Something is missing**
The green button stays off. An amber line beside the boxes says *what*, and a
callout at the foot says *why*. Never a dead end without a reason.

**D. The report goes out**
LabSoft saves the PDF, opens WhatsApp on the number, types the message, brings
the window forward and **pastes the report in**. The human presses Send. That
last step is deliberately manual and should stay visually distinct.

---

## 5. Current visual language

Keep the bones; the redesign is about polish, density and hierarchy.

**On-screen palette (light)**

| Token | Hex | Used for |
|---|---|---|
| brand | `#0F5C73` | primary buttons, tab underline, section headings, focus ring |
| brand-dark | `#0A4356` | hover |
| brand-soft | `#E6F1F4` | selected rows, panel buttons |
| red | `#C1121F` | HIGH flag, errors, danger text |
| green | `#16703F` | GO button, "saved", paid |
| amber | `#8A5A00` | warnings, outstanding money |
| blue | `#1A5FB4` | LOW flag |
| ink / ink2 / ink3 | `#141719` / `#4A5157` / `#616A72` | body / secondary / hint |
| line / line2 | `#C3CBD2` / `#EDF0F3` | borders / dividers |
| bg / panel | `#F4F6F8` / `#FFFFFF` | page / cards |

**On-screen palette (night)** — same roles, inverted surfaces:
brand `#5FC6DE` · bg `#141A1F` · panel `#1C242A` · ink `#EEF2F5` ·
line `#3C464E` · red `#FF8A8A` · green `#6FD79B` · amber `#F0C066`.

**The printed report is its own thing** and is never dark:
teal `#0B6E7F`, deep teal `#075462`, accent `#2AA5A0`, tint `#EAF4F5`,
on white, Times New Roman body with Arial in the letterhead.

**Type** — Segoe UI, 11pt base. Field labels are 9pt, 700 weight, uppercase,
letter-spaced, in ink3. Headings 15pt/700.

**Shape** — 6px radius on buttons and cards, 5px on inputs. 1px borders. Focus is
a 2px brand ring, never a glow. Buttons are ≥32px tall; the result boxes and
panel buttons are deliberately larger than that.

---

## 6. Rules that must not be broken

These are not preferences. Each one exists because of something that went wrong.

1. **The abnormal flags never print.** They are on screen only, to catch a `1480`
   typed instead of `148`. The patient's report looks exactly like the lab's
   existing paper.
2. **Colour is never the only signal.** Every flag has text (`HIGH`, `LOW`) as
   well as colour. Overdue rows say "overdue" as well as being red.
3. **Both themes are measured against WCAG 2.1 AA** and the build fails if a
   colour drops below 4.5:1 for text or 3:1 for a border. Any new colour has to
   clear that in both themes.
4. **Nothing is lost if the power goes.** Results save as you leave each box, not
   when Save is pressed. A redesign must not introduce a "commit" step.
5. **Blocking is for finishing, never for typing.** Name, mobile and sex are
   required to *finish* a job — but a half-filled draft still saves the results
   already typed.
6. **The bill sits above the results**, because the money is settled at the
   counter before the work starts.
7. **Sending is manual.** The software prepares everything; a person presses
   Send. Nothing reaches a patient without a human deciding.
8. **Sent reports are never overwritten.** Corrections create a revision and both
   are kept.
9. **Tabs a person may not use are absent**, not disabled. A greyed-out tab is an
   invitation to ask why.
10. **Every list filters as you type.** No Enter, no Search button.

---

## 7. What the redesign should fix

Honest list of where the current UI is weakest:

- **The Job screen is dense and flat.** Five stacked group boxes with the same
  weight. The eye has nowhere to land. It needs rhythm — where does the work
  actually start?
- **Result rows are a plain grid.** Seven columns of equal weight; the value and
  its flag are what matter and should dominate. Long test names crowd them.
- **Tables all look the same** — Queue, Patients, Doctors, Tests, Billing and
  Staff share one style, so the tabs feel interchangeable. Each list has a
  different job and could show it.
- **Empty and loading states are text in the middle of a box.** They could
  actually teach a new operator what to do.
- **Status is scattered** — a pill top-right, a progress bar mid-screen, a
  counter bottom-right, an amber callout below that. One clear status region
  would serve better.
- **Settings is one long scroll** of eleven group boxes. It wants sections or a
  side rail.
- **Wide monitors waste space.** Everything is a single column; a 1920px screen
  leaves the right third empty on most tabs.
- **The night theme is a straight inversion.** It is readable and passes
  contrast, but it was not designed — it was derived.
- **Dialogs have no shared anatomy.** Some have hints, some don't; button order
  drifts between them.

**Not in scope:** the printed report and receipt layouts. Those match the lab's
existing stationery and are signed off.

---

## 8. Prompts you can paste

### Google Stitch — whole app

> Design a desktop application UI for **LabSoft**, offline laboratory software
> used by a small Indian pathology lab on one Windows PC at the reception
> counter. Desktop web layout, 1440×900. Nine top tabs: Job, Work Queue,
> Patients, Doctors, Tests, Billing, Summaries, Staff, Settings.
> Clinical, calm, high-contrast — teal `#0F5C73` primary on a near-white
> `#F4F6F8` page with white cards, Segoe UI / Inter type, 6px radii, 1px
> borders, no gradients, no shadows heavier than a card lift.
> The users are fast typists working with a queue of people waiting: dense but
> unhurried, generous hit targets, obvious keyboard focus. Include a matching
> dark theme on `#141A1F` / `#1C242A` with `#5FC6DE` primary.

### Google Stitch — the Job screen (the one that matters)

> Design the main working screen of a pathology lab desktop app. One screen does
> everything, top to bottom:
> a header with the patient's name, report number, due time and a status pill;
> a **Patient** section with Name, a narrow Initial box, Mobile, Sex, Age with a
> unit dropdown, and a "Referred by Dr" dropdown showing each doctor with their
> hospital, plus a small line underneath reading "Prints as: FARAS .M. Kutty";
> a **Tests** section of about twelve soft-teal pill buttons (CBC, Lipid Profile,
> Thyroid Profile…) over a type-to-add search field;
> a **Bill** strip showing a large amount, what is paid, what is outstanding, and
> two buttons;
> a **Results** area — a scrolling list grouped by heading, each row: test name,
> a number input, its unit, the normal range in grey, and a small coloured status
> chip reading HIGH, LOW or N. Some rows are italic and read-only because they
> are calculated;
> a bottom action bar: New job, Save, Bill, Preview, a "6 of 7 entered" counter,
> and a wide green primary button "Check & make report".
> Teal `#0F5C73` primary, green `#16703F` for the go button, red `#C1121F` /
> blue `#1A5FB4` / amber `#8A5A00` for the chips. Clinical, not playful.

### Claude Design — canvas of screens

> Build a design canvas for **LabSoft**, offline pathology-lab software for one
> Windows PC. Artboards at 1440×900, light theme, plus a dark variant of the Job
> screen. Draw these screens: (1) Job — patient, tests, bill and results on one
> page; (2) Work Queue table with status pills; (3) Patients split view;
> (4) Doctors table; (5) Billing ledger with filters and a totals strip;
> (6) Report preview dialog over a dimmed backdrop; (7) Send-on-WhatsApp dialog;
> (8) Sign-in card on a teal gradient.
> Palette: brand `#0F5C73`, brand-soft `#E6F1F4`, ink `#141719`, hint `#616A72`,
> line `#C3CBD2`, page `#F4F6F8`, card `#FFFFFF`; red `#C1121F`, green `#16703F`,
> amber `#8A5A00`, blue `#1A5FB4`. Segoe UI. 6px radii, 1px borders, flat.
> Field labels 9px uppercase 700 in hint grey. Buttons at least 32px tall.
> Fix these problems from the current build: flat visual rhythm on the Job
> screen, result rows where the value does not dominate, six tables that all look
> alike, scattered status indicators, a single-column layout that wastes a wide
> monitor, and a dark theme that was derived rather than designed.

### Either tool — one screen at a time

Paste section **3.x** for the screen, plus section **5** (visual language) and
section **6** (rules). That is enough context on its own.

---

## 9. Sample content for mockups

Use real-looking data — placeholder text hides density problems.

- **Patients:** FARAS .M. Kutty · 34 · Male · 9876543210 · Anil .K. Sharma · 52 ·
  Male · Sunita .R. Devi · 40 · Female · Krishnan .P. Nair · 61 · Male
- **Doctors:** Dr. S. Mehta — Cardiologist · City Heart Centre · 9800011122 ·
  Dr. A. Iyer — Paediatrician · Kuttippala Clinic · Dr. Reena Thomas —
  Gynaecologist · Mother Care Hospital
- **Report numbers:** 51359, 51360, 51361 (their series continues unbroken)
- **Results:** Total Cholesterol 238 mg/dl (normal < 200) **HIGH** ·
  HDL Cholesterol 38 mg/dl (> 40) **LOW** · LDL Cholesterol 162 mg/dl calculated ·
  HbA1c 7.8 % (< 5.7) **HIGH** · TSH 6.40 µIU/ml (0.27 – 4.2) **HIGH**
- **Money:** ₹1,590.00 charged · 10% discount · ₹1,431.00 net · ₹500.00 paid ·
  ₹931.00 due — Indian grouping (`1,84,300.00`), ₹ symbol, two decimals
- **Panels:** CBC · Blood Sugar F & PP · Lipid Profile · Liver Function Test ·
  Renal Function Test · Thyroid Profile · Diabetic Profile · Iron Studies ·
  Coagulation Profile · Cardiac Profile · Electrolytes · Full Body Checkup
- **Test groups:** HAEMATOLOGY · BIO-CHEMISTRY (Routine) · LIVER FUNCTION TEST ·
  RENAL FUNCTION TEST · LIPID PROFILE · THYROID PROFILE · ELECTROLYTES ·
  IRON STUDIES · SEROLOGY · URINE · CULTURE & SENSITIVITY

---

## 10. Handing the design back

Whatever comes out of Stitch or Claude Design needs to be buildable in PyQt6
widgets, so:

- **Layouts must be box-based** — rows, columns and grids. No absolute
  positioning, no overlapping cards, no free-floating elements.
- **Say the spacing.** Padding, gaps and column widths as numbers.
- **Name colours as tokens**, not one-off hexes, so both themes stay in step.
- **Show every state** for anything interactive: rest, hover, focus, disabled,
  and for inputs also read-only and error.
- Avoid effects that Qt does not do cheaply: blurs, complex shadows, gradients on
  text, custom-shaped controls, animation beyond a simple fade.
- Web-only patterns to avoid: hover-only menus, tooltips carrying essential
  information, infinite scroll, sticky elements that overlap content.

Exports as PNG or a spec sheet are enough — the rebuild happens in code.
