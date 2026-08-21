# LabSoft

Laboratory reporting for **New Mithra Medical Laboratory**.
Runs on one Windows PC, works without internet, keeps everything in a single file.

---

## Getting started

1. Copy the whole `LabSoft` folder somewhere sensible — `F:\LabSoft` is fine.
2. Double-click **`INSTALL.bat`** once. It checks Python is present, installs what's
   needed, and puts a **LabSoft** icon on your Desktop.
   - If it says Python is missing, install it from python.org and **tick
     "Add python.exe to PATH"** on the first screen of the installer, then run
     `INSTALL.bat` again.
3. Start the program from the Desktop icon.
4. The first time it opens it asks you to create the **administrator account** —
   a name, a username and a PIN. Keep that PIN safe: without an administrator
   nobody can reach Settings. You can skip this if you are the only person who
   uses the PC, and set it up later.

The first time it opens, about 170 tests are loaded with their usual normal
values — haematology, biochemistry, liver and renal, lipids, thyroid,
electrolytes, coagulation, iron studies, hormones, tumour markers, cardiac,
serology, urine, stool, semen analysis and cultures. Change or delete anything you don't use under the **Tests** tab.

### Before you use it for real

Under **Settings**:

- Set **Next report number** so your series carries on unbroken (e.g. `51359`).
- Add your **logo**, **header photo** and, if you want, a **scanned signature**.
- Check the two signatory names and their qualifications.
- Choose the **letterhead design** — *Modern* is the new teal band, *Classic* is
  the heading you have always used. Print one of each and keep whichever the lab
  prefers.
- Turn **Print the letterhead** off if you print onto preprinted stationery.
- Pick the **on-screen theme**: daylight or night. Reports always print on white
  whichever you choose.

---

## Staff and permissions

**The Staff tab** (administrators only). *Create login* asks for a name, a
username and a PIN, and you tick exactly what that person may do:

| Tick | Lets them |
|---|---|
| Results | Register patients and enter results |
| Reports | Make and send reports |
| Billing | Make bills and take payments |
| Money | See the ledger, dues, commissions and summaries |
| Tests master | Edit tests, panels and referring doctors |
| Settings | Change the lab details and report layout |
| Delete | Delete jobs and restore backups |
| Staff | Add and edit accounts |

An **administrator** has all of them without ticking anything. Tabs a person
cannot use simply do not appear for them.

PINs are stored scrambled — nobody, not even an administrator, can read someone's
PIN back; you can only set a new one. Every report, bill and change is recorded
against the person who made it.

The last administrator cannot be turned off or demoted, so the lab can never lock
itself out of its own Settings.

---

## A normal day

**New patient** — press `F2`, or open the **Job** tab.

Type the name, then the **initial** in the small box beside it: *FARAS Kutty*
and *M* print as **FARAS .M. Kutty**, and the line underneath shows you exactly
that before anything is saved.

**Name, mobile and sex are all required.** LabSoft will not let a job be
finished without them — the number is how the report reaches the patient and
how they are recognised next visit, and the sex decides which normal range each
result is judged against. What is still needed is shown beside the boxes as you
go, not sprung on you at the end. Results you have already typed are kept
either way; it is *finishing* that waits, not your work.

Returning patients appear underneath from very little typing — `far`, the
initials `fmk`, a later word like `kutty`, or part of the mobile number all find
*FARAS .M. Kutty*. Click them and everything fills in.

**Referred by Dr** is a list, not a typing box. Pick the doctor and their name
goes on the report and their commission onto the bill. *Add a new doctor…* at
the foot of the list adds one without leaving the job.

If they've been before, a **Repeat last visit's tests** button appears — one
click adds exactly what they had last time, which is what most follow-up visits
need.

**Pick the tests** — click a panel button (CBC, Lipid Profile, Thyroid…) or type
a test name in the search box and press Enter.

**Make the bill** — the Bill band sits between the tests and the results,
because the money is settled at the counter before work starts. It shows the
total, what's been paid and what's outstanding. If you reach the report without
a bill, LabSoft asks once — then lets you continue, because an urgent case must
never wait on paperwork.

**Print bill…** shows the receipt on screen: the lab's letterhead, the charges,
the discount, what has been paid and what is still due, with the amount written
out in words. From there you can print it, save it as a PDF, or send it on
WhatsApp. It works before a bill is saved too, so a patient asking "how much
will it be?" can be handed a proforma without anything being committed. Old
bills reprint from **Money → Print bill…**, which is what people ask for when
they need one for a claim.

**Type the results** — the boxes appear right below. Tab moves down. Grey dashed
boxes work themselves out and can't be typed into.

A coloured marker shows beside anything outside the normal range. **That marker
is for you, not the patient** — it doesn't print. It's there to catch a `1480`
typed instead of `148`.

**Finish** — press `F9` (*Check & make report*). If anything is still empty it
says exactly which tests. Otherwise **the report opens on screen so you can read
it before anyone else does**. Page through it, zoom in, print it, or press
*Looks right — send*. You can also press `F8` at any time to preview the report
as it stands. Turn the automatic preview off in Settings if you'd rather go
straight to sending.

**Send** — everything is done for you. LabSoft saves the PDF, opens WhatsApp on
the patient's number, types your message, brings the window to the front and
pastes the report in.

**You press Send.** That one step is deliberately left to you — nothing goes to
a patient without a person deciding it should.

While it is attaching, don't touch the keyboard. If another window steals focus
part-way through, LabSoft stops rather than pasting the report somewhere it
doesn't belong, and tells you to press `Ctrl+V` yourself. You can switch
automatic attaching off in **Settings → WhatsApp**.

**What was tested is on the report.** Each group heading carries the specimen
underneath it — *Specimen : Serum*, *Whole Blood (EDTA)*, *Fluoride Plasma*.
Where one heading covers tests run on different specimens — HbA1c and fasting
glucose both sit under Bio-Chemistry — the specimen is printed against each
result instead, because a single line claiming one specimen for both would be
wrong.

**Some tests come with a full explanation.** HbA1c, TSH, PSA, Vitamin D and
semen analysis are also issued on their own sheet, with the result, anything
calculated from it, and the standard interpretation printed beneath. The result
still appears on the main report as usual; the detailed sheet is an extra PDF
saved beside it and offered when you send. Any test can be set up this way under
**Tests** — tick *Also issue this test on its own detailed PDF* and type the
interpretation.

**If a test could not be run** — click **⋯** beside it and choose *Mark as not
done*. It stays on the job for your records but is left off the patient's
report, and it no longer blocks *Check & make report*.

---

## Keyboard

| Key | Does |
|---|---|
| `F2` | New job |
| `Ctrl+S` | Save |
| `F9` | Check and make the report |
| `F8` | Preview the report |
| `F4` | Open the bill |
| `Ctrl+F` | Search the work queue |
| `F5` | Refresh |
| `Ctrl+1` / `Ctrl+2` | Job screen / Work queue |

---

## Things worth knowing

**Nothing is lost if the power goes.** Results are saved as you leave each box,
not when you press Save.

**Reports can't be sent half-finished.** Verify stays greyed out until every test
has a value or is marked not done.

**Sent reports are never overwritten.** To correct one, use *Correct & reissue*
in the work queue. The original stays exactly as it was sent, and both are kept —
so if a result is ever questioned, you can show what actually went out.

**Backups happen by themselves** every time the program opens, into
`data\backups`. The last 30 are kept. The bottom-right corner shows the time of
the last one — if it ever says *none yet*, tell someone.

**To back up by hand**, copy `data\lab.db` to a pendrive. That one file is
everything.

**Backups also go to Google Drive.** Install Google Drive for Desktop on the lab
PC and LabSoft finds it by itself — every backup is copied into
`LabSoft Backups - New MITHRA` and Google uploads it. LabSoft never signs in to
anything and stores no password; it just puts the file in the Drive folder. It
works with no internet too — the copy is made locally and Drive catches up
later. Settings → Cloud backup shows where the copies are going, and works the
same with OneDrive, Dropbox, or a folder you choose yourself.

**Every patient has a folder.** Reports are filed under
`patients\<Name> <Mobile> #<id>\`, one folder per person, alongside a
`_patient details.txt` card listing their details and every visit. Those folders
open in Explorer without LabSoft running — useful years later, on another
computer, or straight from a backup. The **Patients** tab shows the same thing
inside the program: search a person, see every visit, open or resend any old
report, or click *Open folder*.

---

## Doctors

**The Doctors tab.** Everyone who refers patients here, with their profession,
the hospital or clinic they work from, and a contact number — the one you ring
when a result needs telling straight away. That number is for the lab; it never
prints on a report.

*Add doctor*, *Edit*, and *Remove*. Removing hides a doctor rather than deleting
them, because past jobs and unpaid commissions still point at that record;
*Show hidden* brings them back. The list says how many patients each has sent.

Search the list by name, profession, hospital or number.

---

## Finding things

Every list has a search box, and typing filters as you go — no Enter needed.
`Ctrl+F` jumps to the search box **on the screen you are looking at**.

| Screen | Search finds |
|---|---|
| Work Queue | name, mobile or report number |
| Patients | name, initials or mobile |
| Doctors | name, profession, hospital or number |
| Tests | code or test name |
| Billing | patient, mobile, report number or doctor |
| Staff | name or username |

---

## Adding a test yourself

**Tests → New test.**

- **Code** is a short name used in formulas — `GLU_F`, `HB`.
- **Specimen** prints on the report — Serum, Plasma, Whole Blood (EDTA), Urine.
  Pick from the list or type your own.
- **Unit** is joined onto the value, so `mg/dl` prints as `105mg/dl`.
- **Its own detailed PDF** — tick it, and type the **interpretation** below. A
  line of all capitals becomes a sub-heading; a line starting with four spaces
  keeps its spacing, so a small table of ranges lines up.
- **Normal values** — the *Prints as* column is what actually appears in the
  Normal Value column, so type it exactly as you want it read. Add several rows
  if the range differs by sex or age; the most specific match wins.
- **Formula** — leave empty for a measured test. For a calculated one, use other
  tests' codes: `TP - ALB`, or `CHOL - HDL - TG/5`. It tells you as you type
  whether it makes sense and what it works out to.

Loops are refused (`A` needing `B` while `B` needs `A`), and a calculated test
stays **blank** rather than wrong if one of its inputs is missing.

To load your existing list in bulk: **Tests → Import from Excel/CSV**. It shows
what it will add, change and skip before writing anything.

---

## If something goes wrong

**The icon flashes a black box and nothing opens** — run **`DIAGNOSE.bat`** in the
LabSoft folder. It runs the program with the window held open and prints exactly
what is wrong, usually in the first few lines.

This nearly always means Python is installed twice on the PC and LabSoft was
started with the copy that has nothing installed in it. `INSTALL.bat` now records
which Python it used, and the launcher checks before starting — so running
`INSTALL.bat` once more normally settles it for good.

**"Python was not found"** — run `INSTALL.bat`, and make sure "Add python.exe to
PATH" was ticked when Python was installed.

**The printer isn't working** — the PDF is still saved. Find it in the `reports`
folder, by month.

**WhatsApp doesn't open** — the send window has a **Use WhatsApp Web** button
that opens the chat in your browser instead of the desktop app. If neither
works, *Open folder* shows you the PDF so you can attach it yourself.

To check WhatsApp without making a report: **Settings → Check WhatsApp**. It
says whether WhatsApp Desktop was found on this PC, and lets you open a test
chat with your own number. If the desktop app misbehaves, set **Open using** to
`web` in Settings and it will always use the browser.

**Wrong data, or something looks corrupted** — Settings → *Restore from a
backup*. Your current data is saved first, so a restore can itself be undone.

Unexpected errors are written to `logs\error.log` with the date and time.

---

## Folders

```
LabSoft\
  main.py              the program
  INSTALL.bat          run once, first time
  RUN LabSoft.bat      starts it
  BUILD_EXE.bat        optional: makes a standalone .exe
  data\lab.db          ALL your data — this is the file to back up
  data\backups\        automatic dated copies, last 30
  assets\              logo, header photo, signature
  patients\             one folder per patient — reports + details card
  reports\2026-08\     the same PDFs filed by month
  exports\             Excel files you export
  logs\error.log       problems, with dates
```

---

## For whoever maintains this

```
pip install -r requirements-dev.txt
python -m pytest          # 505 tests
python main.py
```

The code is in four layers, and the rule that keeps it honest is that
**`app/core/` does the arithmetic and never imports PyQt**:

- `app/db/` — schema, migrations, and every SQL statement
- `app/core/` — formula parser, reference ranges, billing, turnaround
- `app/ui/` — one file per screen; screens never calculate anything themselves
- `app/output/` — the report renderer, the WhatsApp handoff, Excel

Money is stored as whole **paise integers**, never floats. Report layout lives in
`app/output/report.py` and is drawn with QPainter, so the signature block can sit
at the foot of the page and the header can repeat on page two. The receipt in
`app/output/receipt.py` borrows the same renderer, which is why the bill and the
report cannot drift apart.

Both screen themes live in `app/ui/style.py` as two colour dictionaries. Screens
read `style.RED`, `style.PANEL` and so on *inside* functions, never at import
time, so switching theme rebinds them; `tests/test_contrast.py` measures both
palettes against WCAG AA and fails the build if a colour stops being readable.
