# Student Compass — Book Exchange Platform
## Project Plan & Requirements Specification

*Direct Peer-to-Peer Campus Book Exchange with In-Platform Chat & Telegram Integration.*

---

## 1. Specification & Peer-to-Peer Architecture

### Direct Peer Exchange Model
Students exchange textbooks directly without requiring third-party intermediaries or manual desk staff:
1. **Listing Books:** Every student lists the textbooks they are willing to lend out to peers, with photos, category, and minimum 2-week loan rules.
2. **Borrow Requests:** Any student can browse the catalog and submit a borrow request with their desired loan duration.
3. **Approval & Direct Coordination:**  
   Once the lender approves the request, the platform unlocks:
   - **In-Platform Direct Chat:** Real-time message thread on the exchange card to coordinate meeting spots (e.g., campus library, cafeteria).
   - **Telegram Integration:** Direct link to the student's Telegram profile (`https://t.me/username`) so students can communicate on Telegram if preferred.
4. **Handover Confirmation:**  
   When students meet on campus and hand over the book, either party clicks **"Confirm Handover"** to activate the loan and start the due date countdown.
5. **Direct Return:**  
   When the borrower returns the textbook to the owner, the lender clicks **"Confirm Book Returned"** to complete the exchange and restore the book to Available status.
6. **University Student ID:**  
   Every student registers their official University Student ID, which is displayed on their digital card and exchange records for mutual trust.

---

## 2. Core Workflow: Direct Peer Exchange

```
[1. Lender Lists Book] ──> Sets rules (Min 2 wks, Max duration, Care notes)
         │
[2. Borrower Requests] ──> Submits loan duration & study note
         │
[3. Lender Approves]   ──> Unlocks In-Platform Chat & Telegram Contact
         │
[4. Direct Coordination] ──> Chat on platform or Telegram to choose meetup spot
         │
[5. Physical Handover] ──> Students meet on campus, hand over book
         │
[6. Confirm Handover]  ──> Active loan started; due date countdown begins
         │
[7. Direct Return]     ──> Borrower hands book back to owner; owner confirms return
         │
[8. Book Available]    ──> Book is returned to active circulation
```

---

## 3. Data Architecture

### `StudentProfile`
- `user`: OneToOneField(User)
- `student_id`: CharField (Unique University Student ID)
- `telegram_username`: CharField (Telegram @username for direct peer messaging)
- `phone_number`: CharField (Direct contact)

### `ExchangeMessage`
- `exchange`: ForeignKey(ExchangeRequest, related_name='messages')
- `sender`: ForeignKey(User)
- `message`: TextField
- `created_at`: DateTimeField(auto_now_add=True)

### `Book`
- `owner`: ForeignKey(User)
- `title`, `author`, `isbn`: Book details
- `category`: Choices (Computer Science, Engineering, Mathematics, Business, Literature, etc.)
- `course_code`: Optional link to university courses (e.g. CS310, MATH221)
- `condition`: Choices (Like New, Very Good, Good, Fair)
- `min_duration_weeks`: PositiveIntegerField (Minimum constraint >= 2)
- `max_duration_weeks`: PositiveIntegerField
- `lender_requirements`: TextField (Care instructions, e.g. "No highlighter markings")
- `status`: Available, Requested, In Transit to Council, At Council, Borrowed, Completed

### `ExchangeRequest`
- `book`: ForeignKey(Book)
- `borrower`: ForeignKey(User)
- `requested_duration_weeks`: PositiveIntegerField
- `status`:
  - `pending_approval`
  - `accepted_awaiting_dropoff`
  - `at_council_ready_for_pickup`
  - `active_borrowed`
  - `returned_to_council`
  - `completed`
  - `rejected` / `cancelled`
- `dropoff_verified_by`: ForeignKey(User, Council staff)
- `dropoff_condition_notes`: TextField
- `pickup_verified_by`: ForeignKey(User, Council staff)
- `return_verified_by`: ForeignKey(User, Council staff)
- `return_condition_notes`: TextField
- `due_date`: DateField

---

## 4. Design & UI System

Retain the established warm editorial identity in `static/css/compass.css`:
- **Palette:** Warm ivory/parchment background (`#F5ECE0`), crisp card backgrounds (`#FFFFFF`), deep rich burgundy (`#741B3E`, `#4A0E25`), contrast ink (`#1B0C15`), delicate hairlines.
- **Typography:** Fraunces for display headings, Inter for interface, IBM Plex Mono for Student IDs, dates, and book codes.
- **Components:** Topbar navigation, metric cards, status pills, table views, empty state illustrations, and modal/stepper for exchange lifecycles.

---

## 5. Roadmap

- **Phase 1: Core Exchange Engine** — Data models, book catalogue, lending constraints (min 2 weeks), borrow request flow.
- **Phase 2: Student Council Verification Desk** — Interface for Student Council staff to scan/check Student IDs, inspect book conditions, and log physical handoffs.
- **Phase 3: Summer Policy & Notifications** — Recess alert banner, due-date calculation, automated reminders.
- **Phase 4: Bot Integration (Optional Extension)** — Telegram bot connecting students and notifying them of pickup readiness.
