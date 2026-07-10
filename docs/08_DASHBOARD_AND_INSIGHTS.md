# IRIS AI — Dashboard Analytics & Timeline Assembly

This document explains the mathematical formulas and data aggregation rules that power the Dashboard Analytics page.

---

## 1. Document Health Score Formula

The **Document Health Score** measures the completeness of your critical vault profile. We define 8 essential documents that every user should store:
1. Aadhaar Card
2. PAN Card
3. Driving Licence
4. Class 10 Marksheet
5. Class 12 Marksheet
6. Resume / CV
7. Bank Statement
8. Vehicle RC (Registration Certificate)

### Calculation:

$$Health\ Score\ (\%) = \left( \frac{Unique\ Uploaded\ Key\ Doc\ Types}{8} \right) \times 100$$

- If you have uploaded 4 out of these 8 document types, your health score is 50%.
- The dashboard displays a warning banner listing the exact missing key documents to guide you to 100% completeness.

---

## 2. Expiry & Renewal Alert Levels

The system parses expiry dates from documents and categories them into three alert levels based on urgency:

| Remaining Time | Level | UI Color | Action Triggered |
|---|---|---|---|
| < 30 days | **High** | Red | Immediate dashboard warning alert card. |
| 30 to 90 days | **Medium** | Orange | Upcoming task notification card. |
| 90 to 180 days | **Low** | Grey/Slate | Logged in alert drawer. |

---

## 3. Timeline Assembly Heuristics

The timelines are assembled dynamically in `routers/dashboard.py`:

### Academic Timeline:
1. Query completed files in the `Academic Records` category.
2. Parse the `year` integer from the `extracted_json` (e.g., Class 10 year: 2011, Class 12 year: 2013).
3. Sort the entries chronologically by year ascending.

### Career Timeline:
1. Query completed files in `Professional Documents`.
2. Filter file types representing career steps (`Offer Letter`, `Appointment Letter`, `Promotion Letter`).
3. Extract `joining_date` and parse it into a standard DateTime object.
4. Sort and render them sequentially to display your jobs timeline.
