# IRIS AI — Universal Document Taxonomy

This document lists the complete taxonomy of supported documents in IRIS AI. It details the categories, document types, and the exact structured JSON schema fields extracted by the AI Engine.

---

## 1. Identity & Government Documents
**Base Category:** `Identity Documents`

### Aadhaar Card
- **Fields Extracted:**
  - `name`: Full name of the holder.
  - `dob`: Date of Birth (DD/MM/YYYY).
  - `gender`: Male / Female / Transgender.
  - `aadhaar_number`: 12-digit number (masked on display).
  - `address`: Full address string.
  - `has_qr`: Boolean (if QR code is detected).

### PAN Card
- **Fields Extracted:**
  - `name`: Full name of the cardholder.
  - `father_name`: Father's name.
  - `dob`: Date of Birth.
  - `pan_number`: 10-character alphanumeric PAN.

### Driving Licence
- **Fields Extracted:**
  - `name`: Full name of the licence holder.
  - `dob`: Date of Birth.
  - `issue_date`: Date of licence issue.
  - `expiry_date`: Expiry date (powers the Expiry Alerts).
  - `dl_number`: Driving Licence registration number.
  - `vehicle_classes`: List of authorized classes (e.g. MCWG, LMV).
  - `state_rto`: Issuing state RTO authority.

### Passport
- **Fields Extracted:**
  - `surname`: Surname.
  - `given_name`: Given names.
  - `nationality`: Country code (e.g. IND).
  - `dob`: Date of Birth.
  - `issue_date`: Date of passport issue.
  - `expiry_date`: Expiry date.
  - `passport_number`: 8-character code.
  - `place_of_issue`: City/State of issue.
  - `mrz_line`: The Machine-Readable Zone lines at the bottom.

### Voter ID
- **Fields Extracted:**
  - `name`: Full name.
  - `father_husband_name`: Father's or Husband's name.
  - `epic_number`: Alphanumeric Voter Card ID.
  - `part_number`: Constituency part number.
  - `address`: Registered address.
  - `constituency`: Legislative assembly constituency name.

### Domicile / Income / Birth / Caste / Ration Cards
- We extract relevant names, certificate IDs, issuing authorities, addresses, dates, and amounts (e.g. annual income in Income Certificates).

---

## 2. Academic & Educational Records
**Base Category:** `Academic Records`

### School Marksheet (Class 10 / Class 12)
- **Fields Extracted:**
  - `student_name`: Name of the student.
  - `roll_number`: Roll number/seat number.
  - `school_name`: Name of school.
  - `board`: CBSE, ICSE, or State Board.
  - `year`: Year of passing.
  - `subjects`: Array of subject marks:
    - `subject_name`: Name of subject (e.g. English, Mathematics).
    - `marks_obtained`: Numeric mark.
    - `max_marks`: Out of mark (usually 100).
    - `grade`: Alphabetical grade.
  - `total_marks`: Total sum of marks.
  - `percentage`: Computed overall percentage.
  - `result_status`: Pass / Fail / Compartment.

### Higher Education Marksheets (UG / PG)
- **Fields Extracted:**
  - Same as school + `semester_number`, `gpa_cgpa`, `branch_stream`, `university_name`.

### Transfer & Provisional Certificates / Degrees
- **Fields Extracted:**
  - Names, degree titles, specializations, graduation years, distinctions, and institutes.

---

## 3. Professional & Employment Documents
**Base Category:** `Professional Documents`

### Resume / CV
- **Fields Extracted:**
  - `name`: Full name.
  - `contact_info`: Email, phone, LinkedIn, city.
  - `education_timeline`: List of degrees, schools, years.
  - `experience`: Array of jobs:
    - `company`: Company name.
    - `role`: Job title.
    - `duration`: Dates or duration.
  - `skills`: List of competencies (e.g. Python, SQL).
  - `certifications`: Professional courses.

### Offer Letters / Appointment Letters
- **Fields Extracted:**
  - `name`: Recipient candidate name.
  - `designation`: Target job title.
  - `ctc`: Gross compensation package value.
  - `joining_date`: Official start date.
  - `company`: Hiring organization.
  - `location`: Office location.

### Pay Slips
- **Fields Extracted:**
  - `employee_name`, `employee_id`, `pay_month_year`, `basic_pay`, `hra`, `allowances`, `deductions`, `net_pay`, `bank_details`.

---

## 4. Financial & Banking Documents
**Base Category:** `Financial Documents`

### Bank Statements
- **Fields Extracted:**
  - `account_holder`: Primary name on account.
  - `account_number`: Masked digits + last 4.
  - `ifsc`: IFSC code.
  - `bank_name`, `branch_name`.
  - `transactions`: Array of:
    - `date`: Transaction posting date.
    - `description`: Transaction remarks.
    - `debit`: Amount debited (0 if credit).
    - `credit`: Amount credited (0 if debit).
    - `balance`: Ledger balance.

### Cheques / FDs / Loans / Insurance Policies / Taxes (Form 16, ITR, GST)
- Extract numbers, payees, monetary amounts, interest rates, tenures, premium deadlines, and tax-paid summaries.

---

## 5. Medical & Health Records
**Base Category:** `Medical Records`

### Prescription
- **Fields Extracted:**
  - `patient_name`: Patient name.
  - `doctor_name`: Physician.
  - `date`: Checkup date.
  - `medicines`: Array of:
    - `name`: Drug name.
    - `dosage`: Amount (e.g., 500mg).
    - `frequency`: When to take (e.g., 1-0-1 or twice daily).
    - `duration`: Days count.
  - `diagnosis`: Medical diagnosis note.
  - `clinic_hospital`: Name of clinical facility.

### Lab Reports / Discharge Summaries / Vaccination Cards
- Extract patient details, lab tests + values + reference ranges, admission/discharge dates, post-discharge follow-up actions, and vaccine dates.

---

## 6. Property, Legal, Vehicle & Bills
- We map **RCs, Vehicle Insurance, and PUCs** (extracting registration numbers, models, engine/chassis codes, policy periods, and emission thresholds).
- We map **Electricity, Water, and Rent agreements** (extracting meter IDs, consumers, monthly rents, deposits, billing periods, and due dates).
