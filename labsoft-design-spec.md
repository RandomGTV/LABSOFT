# LabSoft — Design Specification

**Lab:** New Mithra Medical Laboratory, Chettiyankinar Road, Kuttippala
**Date:** 18 August 2026
**Status:** Design agreed, awaiting final review before implementation planning

---

## 1. What this is

A Windows desktop program for a small pathology laboratory. One person registers a
patient, enters test results, and sends a PDF report to the patient on WhatsApp. Billing
exists as a record-keeping ledger, not as a step you are forced through.

The report PDF is the product. Everything else in the program exists to get that PDF out
faster and with fewer mistakes.

### Non-goals

These are deliberately excluded. Adding any of them later is a new project, not a tweak.

- Water, food, soil or any non-medical testing
- GST or tax invoicing
- User accounts, passwords, roles or permissions
- Multi-computer or networked operation
- Cloud sync, online patient portal, or a mobile app
- Direct instrument/analyser interfacing
- Inventory, reagent stock, or appointment booking

---

## 2. Constraints

| Constraint | Value |
|---|---|
| Platform | Windows, single PC |
| Connectivity | Fully offline; internet only at the moment a WhatsApp message is sent |
| Users | 1–2 people, no login |
| Technology | Python 3.12 + PyQt6 + SQLite, packaged with PyInstaller into one `.exe` |
| Data | One file, `data/lab.db` |
| Report format | Visually identical to the lab's existing printed report |

---

## 3. Program layout on disk

```
LabSoft/
  LabSoft.exe
  data/
    lab.db                  all data, one file
    backups/                lab_2026-08-18.db, ... (last 30 kept)
  assets/
    logo.png                lab emblem
    header_photo.png        top-right image
    signature.png           optional scanned signature
  reports/
    2026-08/                generated PDFs, foldered by month
  exports/                  Excel/CSV summaries
  templates/
    report.html             report layout, editable without a code change
  logs/
    error.log               rolling error log
```

Backup is copying `data/lab.db`. The program copies it into `backups/` at every startup,
names it by date, and deletes copies older than 30 days. The status bar shows the time of
the last successful backup so a silent failure cannot go unnoticed.

---

## 4. Architecture

Four layers. The rule that makes this work: **arithmetic lives only in `core/`, and
`core/` never imports PyQt.** Anything that computes a number can therefore be tested
without opening a window.

### `db/` — storage

Schema definition, versioned migrations, and query functions. The only place SQL is
written. Exposes plain Python dicts and dataclasses upward; nothing above this layer knows
SQLite exists.

Migrations are numbered and forward-only. A `schema_version` row records the current
version; on startup the program applies any newer migrations in order, taking a backup
first. This is what allows the program to be updated later without the lab losing data.

### `core/` — the brains, pure Python, no UI

| Module | Responsibility |
|---|---|
| `formula.py` | Evaluates derived test formulas |
| `ranges.py` | Decides Normal / High / Low from a reference rule |
| `billing.py` | Bill totals, discounts, payments, balance, commission |
| `turnaround.py` | Due date/time from receipt time and each test's TAT |
| `numbering.py` | Report number allocation |

Each is a small module of pure functions with no shared mutable state. Every one is unit
tested against a table of known inputs and expected outputs before any screen is built.

### `ui/` — screens, deliberately thin

One file per screen. Screens read input, call `core`, and display what comes back. A screen
never performs a calculation itself. If a screen file starts containing arithmetic, that
arithmetic belongs in `core/`.

### `output/` — the deliverable

Renders an HTML template through Qt's `QTextDocument` to either a printer (`QPrinter`) or a
PDF file (`QPdfWriter`). The template is a file on disk, not a string in the code, so the
report layout can be adjusted without touching program logic. Also handles the WhatsApp
handoff.

---

## 5. Data model

### Masters

**`patients`** — `id`, `name`, `phone`, `sex`, `age_value`, `age_unit` (years/months/days),
`address`, `notes`, `created_at`.

Age is stored as a number plus a unit rather than a date of birth, because that is what the
lab records and what the report prints. A date of birth field is available but optional; when
present, age is calculated from it at registration time and then frozen onto the job, so a
reprint years later still shows the age the patient was on the day of the test.

**`referrers`** — `id`, `name`, `qualification`, `phone`, `commission_percent`, `active`.

**`tests`** — the heart of the system.

| Column | Purpose |
|---|---|
| `id`, `code` | `GLU_F`, `HB` — short code used in formulas |
| `name` | Prints as-is: `Blood Glucose [Fasting]` |
| `group_name` | Bold heading row: `BIO-CHEMISTRY (Routine)` |
| `unit` | `mg/dl` — appended directly to the value on the report |
| `decimals` | How many decimal places to display |
| `result_type` | `numeric`, `text`, or `option` |
| `options` | For `option` type: `Positive|Negative` |
| `formula` | Optional, e.g. `TP - ALB`. Empty for directly-measured tests |
| `rate` | Price, for the billing ledger |
| `tat_hours` | Turnaround time, used to compute the due time |
| `sort_order` | Position within its group on the report |
| `active` | Hidden from pickers when off, but old reports still render |

**`reference_ranges`** — one test can have several rows, selected by patient:
`test_id`, `sex` (`M`/`F`/`any`), `age_min`, `age_max`, `rule_type`, `low`, `high`,
`text_value`, `display_text`.

`rule_type` is one of four shapes, which covers everything a pathology report needs:

| Type | Example | Flagged abnormal when |
|---|---|---|
| `range` | `70 - 110mg/dl` | below low or above high |
| `max` | `< 200mg/dl` | above high |
| `min` | `> 40mg/dl` | below low |
| `text` | `Negative` | result differs from `text_value` |

`display_text` is what prints in the Normal Value column. It is stored as literal text
rather than assembled from the numbers, so the printed report can read exactly as the lab
writes it today, including spacing and unit style.

**`panels`** — named groups of tests (`CBC`, `Lipid Profile`, `Thyroid Profile`) with an
optional bundled price and a `quick_button` flag for the one-click buttons on the job screen.
`panel_tests` links panels to tests.

### Work

**`jobs`** — one visit by one patient.

`id`, `report_no`, `patient_id`, `referrer_id`, `received_at`, `due_at`, `reported_at`,
`status`, `age_at_test`, `sex_at_test`, `remarks`, `revision_no`, `sent_at`, `sent_via`.

`status` moves: `draft` → `in_progress` → `ready` → `sent`.

Patient age and sex are copied onto the job because reference ranges depend on them. If a
patient's record is later corrected, old reports must not silently change.

**`job_tests`** — `job_id`, `test_id`, `sort_order`, `not_done`.

**`results`** — `job_test_id`, `raw_value`, `computed_value`, `display_value`, `flag`,
`entered_at`.

`display_value` is stored as the exact string that was printed. This is what guarantees a
reprint in 2029 is byte-identical to the original, even if a test's units or decimal places
have since been edited in the master.

### Money

**`bills`** — `job_id`, `gross`, `discount_type`, `discount_value`, `net`, `created_at`.
**`bill_items`** — `bill_id`, `test_id` or `panel_id`, `rate`, `qty`.
**`payments`** — `bill_id`, `amount`, `mode` (cash/UPI/card), `paid_at`, `note`.
**`commissions`** — `job_id`, `referrer_id`, `base_amount`, `percent`, `amount`, `paid_at`.

A job with no bill row is valid and reports normally. Billing never blocks a report.

### System

**`settings`** — key/value: lab name, address, phone, email, both signatory names and
qualifications, footer lines, print-header on/off, WhatsApp message template, next report
number.

**`audit_log`** — `when`, `action`, `entity`, `entity_id`, `detail`. Records report
generation, sending, reprints, revisions, deletions, result edits after verification, and
settings changes. With no logins this is the only record of what happened, so it is written
for every state-changing action and is never editable from the UI.

---

## 6. Auto-calculation

### Derived results

A test with a `formula` computes itself from other tests in the same job. The formula is
written using test codes: `TP - ALB`, `TC - HDL - TG/5`, `(A + B) / 2`.

Formulas are evaluated by a purpose-built parser supporting `+ - * / ( )`, numbers, test
codes, and the functions `round`, `min`, `max`, `abs`. **Python's `eval` is not used**, and
the parser has no access to variables, attributes, imports or function calls beyond that
list. A malformed formula raises a clear error naming the test; it cannot crash the program
or execute anything.

Dependencies are resolved by topological sort, so a formula may reference another derived
test. A circular reference (`A = B + 1`, `B = A - 1`) is detected when the formula is saved
in the Tests master, and rejected there with a message naming the cycle — not left to fail
at result-entry time.

If a formula's input is blank, the derived test stays blank rather than computing from a
zero. Deriving `LDL = 0` from an empty HDL box would be a wrong result on a medical report,
which is worse than no result.

### Reference flagging

On leaving a result box, the program picks the matching `reference_ranges` row for the
patient's sex and age, applies the rule, and stores a flag of `N`, `H`, `L` or `A`.

**The flag is shown on screen in colour. It is not printed.** Per the lab's decision the
printed report stays exactly as it is today — plain values in the Observed column, the range
in the Normal column. The flag's purpose is to catch a typing error before the report goes
out. Printing flags is a settings toggle that stays switched off; the data is there if the
lab changes its mind.

If no reference range matches the patient's age and sex, the value is stored with flag `A`
(unassessed) and the screen shows a grey dash rather than a false "Normal".

### Turnaround

`due_at = received_at + max(tat_hours of all tests on the job)`. Jobs past due with status
below `ready` show red in the queue and are counted in the status bar.

### Billing

Gross is the sum of test rates, with a panel's bundled price replacing its members' rates
when a whole panel is selected. Discount is a percentage or a flat amount. Balance is
net minus the sum of payments. Commission is the referrer's percentage of the net.

All money is stored in **paise as integers**, never as floating point, and formatted for
display only at the edge. Floating-point rupees produce totals that are off by a paisa and
dues lists that never reconcile.

---

## 7. Screens

### 7.1 Job screen — one screen for everything

The lab asked for register and result entry in a single screen, and this is the primary
screen of the program. It opens with `F2` from anywhere and has three stacked bands:

**Top — patient.** Name, phone, sex, age, referring doctor. Typing into Name searches
existing patients as you type; picking one fills the rest and shows their history count.
Report number is allocated and displayed here.

**Middle — tests.** A row of large one-click buttons for the lab's common panels, plus a
type-ahead box for individual tests. Selected tests appear as removable chips. Choosing a
panel adds all its tests at once.

**Bottom — results.** The result grid appears the moment the first test is chosen, in the
same screen. Columns: Test / Result / Unit / Normal Value / flag. Derived tests show as
read-only grey boxes and fill themselves in. Tab moves down the column; Enter moves down;
the grid never requires the mouse.

Actions: **Save** (`Ctrl+S`), **Verify & make PDF** (`F9`), **Bill** (`F4`, optional).

Verify is blocked while any test is neither filled nor ticked "not done". This is the single
most valuable guard in the program: it makes an incomplete report impossible to send by
accident.

### 7.2 Work queue

The home screen. One row per job: report number, patient, tests, received, due, status,
payment state. Filters for Today / Pending / Overdue / All, and a search box covering name,
phone and report number. Overdue rows are red and sort first. Double-click opens the job.

Status bar: jobs today, results pending, overdue count, ready-to-send count, and last backup
time.

### 7.3 Send dialog

Appears after Verify. The PDF is already written to `reports/YYYY-MM/` and already copied to
the Windows clipboard. Shows the filename, the destination number, and the editable message
text.

**Open WhatsApp & send** launches WhatsApp Desktop or Web at that number with the message
pre-filled; the operator presses `Ctrl+V` then `Enter` to attach and send. The other two
buttons are **Print** and **Save only**. There is no email option — it was not asked for and
would need mail account setup the lab does not have.

Because Windows cannot make another application attach a file without automation that breaks
on every WhatsApp update, the last keypress stays with the operator. This is a deliberate
choice: it is reliable, needs no Meta business account, no per-message fee, and no template
approval, and it uses the lab's existing WhatsApp number.

The send path sits behind a single `Sender` interface with one implementation today
(`WhatsAppDesktopSender`). Adding `WhatsAppCloudApiSender` later means writing one class and
changing one setting — no other file is touched.

On success the job is stamped `sent`, with the time and channel, and an audit row is written.

### 7.4 Patient history

Every job for a patient, oldest to newest, with a per-test view showing how a value has moved
over time. Opens from the job screen while entering results, so a wildly different value from
last month is visible at the moment of typing.

### 7.5 Reprint and revision

Search any past report by name, phone, or report number; print or resend it unchanged.

Amending a verified report creates **revision 2** of the same report number rather than
overwriting it. The revision prints marked as such, the original PDF is retained on disk, and
both the change and the reason are written to the audit log. A lab that silently rewrites
issued results has no defence when a result is questioned.

### 7.6 Masters

Editors for tests, reference ranges, panels, referrers, and patients. The Tests editor
includes a formula box with a test-code picker, and validates the formula — syntax,
unknown codes, circular references — at save time, showing a live worked example.

### 7.7 Billing ledger

A list, not a wizard: job, patient, charged, discount, paid, balance, referrer, commission.
Totals for the month, outstanding amount, and commission payable. Filters by date range,
referrer, and unpaid-only. Exports to Excel.

### 7.8 Summaries

- **Day sheet** — patient count, test counts, amount collected, dues raised, jobs pending.
- **Month sheet** — the same by day, plus test-wise volume and a per-referrer commission
  statement suitable for handing to the doctor.

Both print and export to Excel.

### 7.9 Settings

Lab identity and contact lines, logo and header images, both signatories, footer text,
**print header on/off** (for switching between plain paper and preprinted letterhead),
WhatsApp message template, next report number, backup folder.

---

## 8. The report

Rendered from `templates/report.html` — a file the lab can have adjusted without a code
change. Matches the existing printed report:

- Serif typeface throughout
- Letterhead: emblem, lab name, address block, top-right photo
- `Report No` and `Date` on one line; `Name`, `Sex`, `Age` on the next; `Ref. by Dr` below,
  printed only when filled
- Double rule beneath the patient block
- Three columns — **Test Description / Observed Value / Normal Value**
- Units written inline with the value (`105mg/dl`), not in a separate column
- Bold group heading rows (`BIO-CHEMISTRY (Routine)`)
- Centred `-End of Report-` and `- New MITHRA -`
- Large faint circular watermark
- Two signatories pinned to the foot of the page regardless of report length
- Sequential report number continuing from the lab's current series; date only, no time

**Print header on/off** controls whether the letterhead band is drawn. The setting applies to
printing only — the WhatsApp PDF always includes the full header, because a PDF with a blank
top is not a usable document.

Multi-page reports repeat the header and the column titles, number pages as `Page n of m`,
and never split a group heading from its first row.

---

## 9. Preloaded content

The program ships with a pathology test library already defined — the routine panels a small
lab runs, with standard reference ranges, units and group headings, all editable and
deletable. The lab is usable the day it is installed rather than being an empty shell.

An **import** step reads the lab's own test list, rates and normal values from Excel or CSV,
and can import an existing patient list the same way. Import previews what it will do and
reports what it skipped before writing anything.

---

## 10. Error handling

The rule: **never lose typed work, and never print something wrong.**

| Situation | Behaviour |
|---|---|
| Program crashes mid-entry | Results are written to the database as each field is left, not on Save. Reopening the job shows everything typed. |
| Printer missing or offline | PDF is still generated and saved. The error names the printer and offers Save and Retry. |
| WhatsApp not installed | Falls back to WhatsApp Web in the browser. If that fails, the PDF path is shown with a Copy-path button. |
| Bad formula in the Tests master | Rejected at save time with the position of the error. An existing bad formula leaves the derived test blank and shows a warning row rather than a wrong number. |
| No reference range matches | Flag `A`, grey dash on screen, Normal Value column blank on print. Never a guessed range. |
| Database file locked or missing | Clear message naming the path, with a Restore-from-backup button listing the last 30 backups by date. |
| Disk full during PDF write | Write to a temporary file first, then move into place. A half-written PDF is never left behind. |
| Duplicate report number | Numbers are allocated inside the same transaction that creates the job. A gap is acceptable; a duplicate is not. |

Unexpected errors are written to `logs/error.log` with a timestamp, and shown to the operator
as a plain sentence with what to do next — never a Python traceback.

---

## 11. Testing

**Unit tests on `core/`** — the layer where a mistake reaches a patient's report:

- Formula parser: correct results, operator precedence, blank inputs, division by zero,
  unknown codes, circular references, and rejection of anything resembling code execution
- Reference ranges: each of the four rule types at and around its boundaries, age and sex
  selection, overlapping rows, and the no-match case
- Billing: percentage and flat discounts, panel pricing, partial payments, balance,
  commission, and integer-paise rounding
- Turnaround: due time from mixed TAT values

**Golden-file tests on `output/`** — a fixed job renders to HTML that is compared against a
stored reference file. Any accidental change to the report layout fails the test. This is
what stops a small edit from quietly altering every report the lab issues.

**Manual test script** — a written checklist walked through before each release: register a
patient, enter a panel with a derived value, verify, print with the header on and off, send
on WhatsApp, reprint, revise, and restore from a backup.

---

## 12. Build order

Each stage produces something usable, so the lab can start using the program before it is
finished and say what is wrong while changes are still cheap.

1. **Foundation** — database schema, migrations, backup on startup, settings
2. **Masters** — tests, reference ranges, panels, referrers, plus the preloaded library
3. **`core/`** — formula parser, ranges, turnaround, with their unit tests, no UI
4. **Job screen** — registration and result entry in one screen, with live calculation
5. **The report** — HTML template, PDF and print, header on/off, golden-file tests
6. **Send** — clipboard, WhatsApp handoff, sent-status stamping
7. **Work queue** — filters, search, overdue highlighting, status bar
8. **History, reprint, revisions**
9. **Billing ledger, dues, commission**
10. **Summaries and Excel export**
11. **Import from Excel/CSV**
12. **Packaging** — PyInstaller build, desktop shortcut, first-run setup wizard

Stage 6 is the first point at which the program does the lab's real job end to end. Stages 9
to 11 are convenience and can be delivered later without holding up daily use.

---

## 13. Open items

- Logo image, top-right header photo, and optionally a scanned signature, as image files
- The report number to start from, so the lab's series continues unbroken
- The lab's current test list with rates and normal values, for import
