# Compass Books — University Book Exchange Platform

A peer-to-peer book sharing and exchange platform for university students operating on a centralized drop-off and pick-up escrow model via the **Student Council**.

**Design System:** Built on a custom warm editorial identity (`compass.css`) featuring parchment ivory (`#F5ECE0`), rich burgundy (`#741B3E`), Fraunces serif headings, Inter body text, and IBM Plex Mono tabular numbers and Student IDs.

---

## Key Features

1. **Book Listing & Custom Rules:**
   - Students list textbooks and fiction they are willing to lend.
   - Owners specify condition, handling rules (e.g. no highlighting, keep dust cover), and loan duration (**strictly minimum 2 weeks** as required by university rules).

2. **Student Council Escrow Workflow:**
   - Direct student-to-student meetups are replaced by a trusted central desk.
   - The lender drops the book off at the **Student Council**.
   - The borrower picks up the book from the Student Council desk.
   - When the loan period ends, the borrower returns the book to the Student Council for condition audit before the owner reclaims it.

3. **Mandatory University Student ID Verification:**
   - Every student enters their official University Student ID upon registration.
   - The Student Council physically checks each student's University ID card before releasing or accepting any book.

4. **Condition Control & Quality Auditing:**
   - Student Council logs condition notes upon intake and verifies the returned book matches its initial state.

5. **Summer Recess Policy:**
   - Active warning and policy disclaimers: The Student Council does not oversee or take responsibility for exchanges during summer vacation.

---

## Demo Accounts

Pre-seeded with realistic data (`seed_demo.py`):

| Username | Password | Full Name | Role | Student ID | Notes |
|---|---|---|---|---|---|
| `akbar` | `compass-akbar` | Akbar Evatov | Student (Lender & Borrower) | `240418` | Software Engineering (JSE2) |
| `kamola` | `compass-kamola` | Kamola Abdullayeva | Student (Lender & Borrower) | `240592` | Computer Science (JCS1) |
| `council` | `compass-council` | Council Desk Officer | Student Council Staff | `230001` | Manages verification desk |

---

## Setup & Running Locally

1. **Activate virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Seed demo data:**
   ```bash
   python seed_demo.py
   ```

4. **Run unit tests:**
   ```bash
   pytest
   ```

5. **Start dev server:**
   ```bash
   python manage.py runserver
   ```
