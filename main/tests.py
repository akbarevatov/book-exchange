from datetime import date, timedelta
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from main.models import Book, ExchangeRequest, StudentProfile



@pytest.mark.django_db
def test_homepage_loads(client):
    """Verify that the homepage renders correctly and contains authentication actions."""
    response = client.get(reverse('home'))
    assert response.status_code == 200
    assert b'Compass Books' in response.content
    assert b'Register with University ID' in response.content
    assert b'Sign in' in response.content


@pytest.mark.django_db
def test_student_registration_creates_user_and_profile(client):
    """Registering a new student must create a User and an associated StudentProfile with their University ID."""
    reg_data = {
        'first_name': 'Akbar',
        'last_name': 'Evatov',
        'username': 'akbar_r',
        'email': 'akbar@univ.edu',
        'student_id': '240418',
        'phone_number': '+998901234567',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!',
    }
    response = client.post(reverse('register'), data=reg_data)
    # Successful registration redirects to profile
    assert response.status_code == 302
    assert response.url == reverse('profile')

    user = User.objects.get(username='akbar_r')
    assert user.first_name == 'Akbar'
    assert user.last_name == 'Evatov'
    assert user.email == 'akbar@univ.edu'

    profile = StudentProfile.objects.get(user=user)
    assert profile.student_id == '240418'
    assert profile.phone_number == '+998901234567'
    assert profile.is_council_member is False


@pytest.mark.django_db
def test_registration_rejects_duplicate_student_id(client):
    """University Student IDs must be unique across the platform."""
    # Pre-create student with ID 240418
    existing_user = User.objects.create_user(username='first_student', email='first@univ.edu', password='Password123!')
    StudentProfile.objects.create(user=existing_user, student_id='240418')

    # Attempt to register a second account with the same ID
    reg_data = {
        'first_name': 'Different',
        'last_name': 'Student',
        'username': 'second_student',
        'email': 'second@univ.edu',
        'student_id': '240418',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
    }
    response = client.post(reverse('register'), data=reg_data)
    assert response.status_code == 200
    assert b'This University Student ID is already registered' in response.content
    assert not User.objects.filter(username='second_student').exists()


@pytest.mark.django_db
def test_registration_requires_matching_passwords(client):
    """Mismatched passwords should fail form validation."""
    reg_data = {
        'first_name': 'Kamola',
        'last_name': 'Abdullayeva',
        'username': 'kamola',
        'email': 'kamola@univ.edu',
        'student_id': '240592',
        'password': 'PasswordOne1!',
        'confirm_password': 'PasswordMismatch2!',
    }
    response = client.post(reverse('register'), data=reg_data)
    assert response.status_code == 200
    assert b'Passwords do not match' in response.content


@pytest.mark.django_db
def test_login_and_logout(client):
    """Students can log in with username/password and log out successfully."""
    user = User.objects.create_user(username='student_login_test', password='TestPassword123!')
    StudentProfile.objects.create(user=user, student_id='240777')

    # Log in
    login_resp = client.post(reverse('login'), data={
        'username': 'student_login_test',
        'password': 'TestPassword123!',
    })
    assert login_resp.status_code == 302
    assert login_resp.url == reverse('profile')

    # View profile as logged-in user
    profile_resp = client.get(reverse('profile'))
    assert profile_resp.status_code == 200
    assert b'240777' in profile_resp.content

    # Log out
    logout_resp = client.get(reverse('logout'))
    assert logout_resp.status_code == 302
    assert logout_resp.url == reverse('home')


@pytest.mark.django_db
def test_profile_requires_login(client):
    """Unauthenticated users attempting to view /profile/ must be redirected to login."""
    response = client.get(reverse('profile'))
    assert response.status_code == 302
    assert reverse('login') in response.url


@pytest.mark.django_db
def test_profile_update(client):
    """Students can update their contact details and profile."""
    user = User.objects.create_user(username='kamola_edit', password='Password123!')
    profile = StudentProfile.objects.create(user=user, student_id='240999', phone_number='+998901112233')
    client.force_login(user)

    update_data = {
        'first_name': 'Kamola',
        'last_name': 'Abdullayeva',
        'email': 'kamola.new@univ.edu',
        'student_id': '240999',
        'phone_number': '+998909998877',
    }
    response = client.post(reverse('profile'), data=update_data)
    assert response.status_code == 302
    assert response.url == reverse('profile')

    user.refresh_from_db()
    profile.refresh_from_db()
    assert user.first_name == 'Kamola'
    assert user.last_name == 'Abdullayeva'
    assert user.email == 'kamola.new@univ.edu'
    assert profile.phone_number == '+998909998877'


@pytest.mark.django_db
def test_my_books_requires_login(client):
    """Accessing /my-books/ requires authentication."""
    response = client.get(reverse('my_books'))
    assert response.status_code == 302
    assert reverse('login') in response.url


@pytest.mark.django_db
def test_my_books_lists_only_current_user_books(client):
    """My Books must only display books listed by the authenticated student."""
    akbar = User.objects.create_user(username='akbar_lender', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')

    kamola = User.objects.create_user(username='kamola_lender', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    # Akbar's book
    b1 = Book.objects.create(
        owner=akbar,
        title='Computer Networks',
        author='Tanenbaum',
        category=Book.Category.COMPUTER_SCIENCE,
        course_code='CS320',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )
    # Kamola's book
    b2 = Book.objects.create(
        owner=kamola,
        title='Calculus: Early Transcendentals',
        author='James Stewart',
        category=Book.Category.MATHEMATICS,
        course_code='MATH101',
        min_duration_weeks=3,
        max_duration_weeks=6,
    )

    client.force_login(akbar)
    response = client.get(reverse('my_books'))
    assert response.status_code == 200
    assert b'Computer Networks' in response.content
    assert b'Calculus: Early Transcendentals' not in response.content
    assert response.context['total_books'] == 1


@pytest.mark.django_db
def test_add_book_success(client):
    """Student can add a new book with valid loan constraints."""
    user = User.objects.create_user(username='book_adder', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240111')
    client.force_login(user)

    book_data = {
        'title': 'Artificial Intelligence: A Modern Approach',
        'author': 'Stuart Russell & Peter Norvig',
        'category': 'CS',
        'course_code': 'CS440',
        'isbn': '978-0134610993',
        'condition': 'LIKE_NEW',
        'min_duration_weeks': 2,
        'max_duration_weeks': 5,
        'lender_requirements': 'Do not highlight. Keep clean.',
    }
    response = client.post(reverse('add_book'), data=book_data)
    assert response.status_code == 302
    assert response.url == reverse('my_books')

    book = Book.objects.get(title='Artificial Intelligence: A Modern Approach')
    assert book.owner == user
    assert book.min_duration_weeks == 2
    assert book.max_duration_weeks == 5
    assert book.condition == 'LIKE_NEW'
    assert book.status == Book.Status.AVAILABLE


@pytest.mark.django_db
def test_add_book_enforces_minimum_two_weeks(client):
    """Platform policy strictly rejects any book with min duration < 2 weeks."""
    user = User.objects.create_user(username='book_adder_invalid', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240222')
    client.force_login(user)

    book_data = {
        'title': 'Short Term Book',
        'author': 'Some Author',
        'category': 'CS',
        'condition': 'GOOD',
        'min_duration_weeks': 1,  # INVALID: must be >= 2
        'max_duration_weeks': 4,
    }
    response = client.post(reverse('add_book'), data=book_data)
    assert response.status_code == 200
    assert b'Minimum loan duration must be at least 2 weeks' in response.content
    assert not Book.objects.filter(title='Short Term Book').exists()


@pytest.mark.django_db
def test_add_book_max_duration_must_be_ge_min(client):
    """Max duration cannot be less than minimum duration."""
    user = User.objects.create_user(username='book_adder_mismatch', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240333')
    client.force_login(user)

    book_data = {
        'title': 'Mismatch Book',
        'author': 'Author',
        'category': 'CS',
        'condition': 'GOOD',
        'min_duration_weeks': 4,
        'max_duration_weeks': 2,  # INVALID: 2 < 4
    }
    response = client.post(reverse('add_book'), data=book_data)
    assert response.status_code == 200
    assert b'Maximum duration cannot be less than minimum duration' in response.content


@pytest.mark.django_db
def test_edit_book_owner_only(client):
    """Only the owner can edit their book."""
    akbar = User.objects.create_user(username='akbar_owner', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')
    kamola = User.objects.create_user(username='kamola_other', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=akbar,
        title='Algorithms',
        author='Sedgewick',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )

    # Kamola cannot edit Akbar's book
    client.force_login(kamola)
    kamola_resp = client.get(reverse('edit_book', kwargs={'pk': book.pk}))
    assert kamola_resp.status_code == 404

    # Akbar can edit his book
    client.force_login(akbar)
    akbar_resp = client.post(reverse('edit_book', kwargs={'pk': book.pk}), data={
        'title': 'Algorithms (4th Edition)',
        'author': 'Robert Sedgewick',
        'category': 'CS',
        'condition': 'LIKE_NEW',
        'min_duration_weeks': 3,
        'max_duration_weeks': 6,
    })
    assert akbar_resp.status_code == 302
    book.refresh_from_db()
    assert book.title == 'Algorithms (4th Edition)'
    assert book.min_duration_weeks == 3


@pytest.mark.django_db
def test_delete_book_owner_only(client):
    """Only the owner can delete their book."""
    akbar = User.objects.create_user(username='akbar_del_owner', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')
    kamola = User.objects.create_user(username='kamola_del_other', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=akbar,
        title='Temporary Book',
        author='Temp Author',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )

    # Kamola cannot delete Akbar's book
    client.force_login(kamola)
    kamola_del = client.post(reverse('delete_book', kwargs={'pk': book.pk}))
    assert kamola_del.status_code == 404
    assert Book.objects.filter(pk=book.pk).exists()

    # Akbar deletes his book
    client.force_login(akbar)
    akbar_del = client.post(reverse('delete_book', kwargs={'pk': book.pk}))
    assert akbar_del.status_code == 302
    assert not Book.objects.filter(pk=book.pk).exists()


@pytest.mark.django_db
def test_exchanges_requires_login(client):
    """Accessing /exchanges/ requires authentication."""
    response = client.get(reverse('exchanges'))
    assert response.status_code == 302
    assert reverse('login') in response.url


@pytest.mark.django_db
def test_exchanges_lists_borrowed_books(client):
    """The exchanges page must list all books borrowed by the user with status, lender info, and due date."""
    akbar = User.objects.create_user(username='akbar_borrower', password='Password123!', first_name='Akbar', last_name='Evatov')
    StudentProfile.objects.create(user=akbar, student_id='240418')

    kamola = User.objects.create_user(username='kamola_owner', password='Password123!', first_name='Kamola', last_name='Abdullayeva')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=kamola,
        title='Discrete Mathematics and Its Applications',
        author='Kenneth Rosen',
        category=Book.Category.MATHEMATICS,
        course_code='MATH210',
        min_duration_weeks=2,
        max_duration_weeks=6,
    )

    # Akbar is borrowing this book from Kamola
    ExchangeRequest.objects.create(
        book=book,
        borrower=akbar,
        requested_duration_weeks=3,
        status=ExchangeRequest.Status.ACTIVE_BORROWED,
        due_date=timezone.now().date() + timedelta(days=21),
    )

    client.force_login(akbar)
    response = client.get(reverse('exchanges'))
    assert response.status_code == 200
    assert b'Discrete Mathematics and Its Applications' in response.content
    assert b'Kamola' in response.content
    assert b'240592' in response.content  # Lender's University ID
    assert b'Active Loan' in response.content
    assert response.context['active_loans_count'] == 1


@pytest.mark.django_db
def test_borrow_book_success(client):
    """Borrower submits a request for a book within the allowed loan duration window."""
    akbar = User.objects.create_user(username='akbar_submitting', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')

    kamola = User.objects.create_user(username='kamola_lender2', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=kamola,
        title='Computer Organization and Design',
        author='Patterson & Hennessy',
        category=Book.Category.COMPUTER_SCIENCE,
        min_duration_weeks=2,
        max_duration_weeks=4,
    )

    client.force_login(akbar)
    response = client.post(reverse('borrow_book', kwargs={'pk': book.pk}), data={
        'requested_duration_weeks': 3,
        'borrower_note': 'For hardware exam prep',
    })
    assert response.status_code == 302
    assert response.url == reverse('exchanges')

    exchange = ExchangeRequest.objects.get(book=book, borrower=akbar)
    assert exchange.status == ExchangeRequest.Status.PENDING_APPROVAL
    assert exchange.requested_duration_weeks == 3
    assert exchange.borrower_note == 'For hardware exam prep'


@pytest.mark.django_db
def test_cannot_borrow_own_book(client):
    """A user cannot borrow a book they listed themselves."""
    akbar = User.objects.create_user(username='akbar_self', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')

    book = Book.objects.create(
        owner=akbar,
        title='Self Book',
        author='Self Author',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )

    client.force_login(akbar)
    response = client.get(reverse('borrow_book', kwargs={'pk': book.pk}))
    # Redirects back with warning
    assert response.status_code == 302
    assert not ExchangeRequest.objects.filter(book=book).exists()


@pytest.mark.django_db
def test_cancel_borrow_request(client):
    """Borrower can cancel their pending request."""
    akbar = User.objects.create_user(username='akbar_cancelling', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')
    kamola = User.objects.create_user(username='kamola_cancellee', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=kamola,
        title='Python Crash Course',
        author='Eric Matthes',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )
    req = ExchangeRequest.objects.create(
        book=book,
        borrower=akbar,
        requested_duration_weeks=2,
        status=ExchangeRequest.Status.PENDING_APPROVAL,
    )

    client.force_login(akbar)
    response = client.post(reverse('cancel_exchange', kwargs={'pk': req.pk}))
    assert response.status_code == 302
    assert response.url == reverse('exchanges')

    req.refresh_from_db()
    assert req.status == ExchangeRequest.Status.CANCELLED


@pytest.mark.django_db
def test_lender_approves_borrow_request(client):
    """Lender approves borrow request -> awaiting drop-off at Student Council."""
    akbar = User.objects.create_user(username='akbar_req', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')
    kamola = User.objects.create_user(username='kamola_approver', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    book = Book.objects.create(
        owner=kamola,
        title='Database System Concepts',
        author='Silberschatz',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )
    req = ExchangeRequest.objects.create(
        book=book,
        borrower=akbar,
        requested_duration_weeks=2,
        status=ExchangeRequest.Status.PENDING_APPROVAL,
    )

    client.force_login(kamola)
    response = client.post(reverse('respond_exchange', kwargs={'pk': req.pk, 'action': 'approve'}))
    assert response.status_code == 302
    assert response.url == reverse('exchanges')

    req.refresh_from_db()
    book.refresh_from_db()
    assert req.status == ExchangeRequest.Status.AWAITING_DROPOFF
    assert req.approved_at is not None
    assert book.status == Book.Status.RESERVED


@pytest.mark.django_db
def test_exchange_catalog_loads(client):
    """Catalog page loads and displays available books."""
    user = User.objects.create_user(username='book_seller', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240999')
    Book.objects.create(
        owner=user,
        title='Clean Code',
        author='Robert C. Martin',
        category=Book.Category.COMPUTER_SCIENCE,
        min_duration_weeks=2,
        max_duration_weeks=4,
    )

    response = client.get(reverse('exchange'))
    assert response.status_code == 200
    assert b'Clean Code' in response.content
    assert b'Exchange Catalog' in response.content


@pytest.mark.django_db
def test_exchange_catalog_search(client):
    """Searching catalog filters by title, author, or course code."""
    user = User.objects.create_user(username='book_owner_search', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240888')

    Book.objects.create(owner=user, title='Linear Algebra Done Right', author='Sheldon Axler', category='MATH', course_code='MATH250')
    Book.objects.create(owner=user, title='Computer Networks', author='Andrew Tanenbaum', category='CS', course_code='CS320')

    # Search for 'Linear'
    resp = client.get(reverse('exchange'), {'q': 'Linear'})
    assert b'Linear Algebra Done Right' in resp.content
    assert b'Computer Networks' not in resp.content

    # Search by course code 'CS320'
    resp = client.get(reverse('exchange'), {'q': 'CS320'})
    assert b'Computer Networks' in resp.content
    assert b'Linear Algebra Done Right' not in resp.content


@pytest.mark.django_db
def test_exchange_catalog_category_filter(client):
    """Filtering by category shows only matching books."""
    user = User.objects.create_user(username='cat_owner', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240777')

    Book.objects.create(owner=user, title='Physics for Scientists', author='Tipler', category='ENG')
    Book.objects.create(owner=user, title='Economics', author='Mankiw', category='BUS')

    resp = client.get(reverse('exchange'), {'category': 'ENG'})
    assert b'Physics for Scientists' in resp.content
    assert b'Mankiw' not in resp.content


@pytest.mark.django_db
def test_exchange_catalog_owner_distinction(client):
    """Authenticated student sees 'Your Listed Book' for their own book and 'Request to Borrow' for others."""
    akbar = User.objects.create_user(username='akbar_cat', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240418')
    kamola = User.objects.create_user(username='kamola_cat', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240592')

    akbar_book = Book.objects.create(owner=akbar, title='Akbar Book', author='Author A', category='CS')
    kamola_book = Book.objects.create(owner=kamola, title='Kamola Book', author='Author K', category='MATH')

    client.force_login(akbar)
    resp = client.get(reverse('exchange'))
    assert resp.status_code == 200
    assert b'Your Listed Book' in resp.content
    assert b'Request to Borrow' in resp.content


@pytest.mark.django_db
def test_add_book_with_cover_image(client):
    """Uploading a book with a cover photo saves the image correctly."""
    user = User.objects.create_user(username='photo_lender', password='Password123!')
    StudentProfile.objects.create(user=user, student_id='240321')
    client.force_login(user)

    # 1x1 valid GIF image
    tiny_gif = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
        b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
        b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    )
    image_file = SimpleUploadedFile('cover.gif', tiny_gif, content_type='image/gif')

    book_data = {
        'title': 'Design Patterns',
        'author': 'Gang of Four',
        'category': 'CS',
        'condition': 'VERY_GOOD',
        'min_duration_weeks': 2,
        'max_duration_weeks': 4,
        'cover_image': image_file,
    }
    response = client.post(reverse('add_book'), data=book_data)
    assert response.status_code == 302
    assert response.url == reverse('my_books')

    book = Book.objects.get(title='Design Patterns')
    assert book.cover_image is not None
    assert 'cover' in book.cover_image.name

    # Check that image appears in My Books and Exchange Catalog
    my_books_resp = client.get(reverse('my_books'))
    assert book.cover_image.url.encode() in my_books_resp.content

    catalog_resp = client.get(reverse('exchange'))
    assert book.cover_image.url.encode() in catalog_resp.content


@pytest.mark.django_db
def test_student_registration_with_telegram_username(client):
    """Students can supply an optional Telegram username upon registration."""
    reg_data = {
        'first_name': 'Akbar',
        'last_name': 'Evatov',
        'username': 'akbar_tg',
        'email': 'akbar_tg@univ.edu',
        'student_id': '240419',
        'telegram_username': '@akbarevatov',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!',
    }
    response = client.post(reverse('register'), data=reg_data)
    assert response.status_code == 302

    profile = StudentProfile.objects.get(student_id='240419')
    assert profile.telegram_clean == 'akbarevatov'
    assert profile.telegram_url == 'https://t.me/akbarevatov'


@pytest.mark.django_db
def test_direct_exchange_chat_messaging(client):
    """Lender and borrower can send direct messages to coordinate meeting spots."""
    akbar = User.objects.create_user(username='akbar_chat', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240420', telegram_username='akbar_chat')
    kamola = User.objects.create_user(username='kamola_chat', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240593', telegram_username='kamola_chat')

    book = Book.objects.create(
        owner=kamola,
        title='Computer Architecture',
        author='Patterson & Hennessy',
        min_duration_weeks=2,
        max_duration_weeks=4,
    )
    exchange = ExchangeRequest.objects.create(
        book=book,
        borrower=akbar,
        requested_duration_weeks=2,
        status=ExchangeRequest.Status.AWAITING_DROPOFF,
    )

    # Akbar sends a message
    client.force_login(akbar)
    resp = client.post(reverse('send_exchange_message', kwargs={'pk': exchange.pk}), data={
        'message': "Hi Kamola! Can we meet at the campus library lobby at 2 PM?",
    })
    assert resp.status_code == 302
    assert exchange.messages.count() == 1
    msg = exchange.messages.first()
    assert msg.sender == akbar
    assert "library lobby" in msg.message

    # Kamola views the exchange page and sees the message and Akbar's Telegram button
    client.force_login(kamola)
    view_resp = client.get(reverse('exchanges'))
    assert view_resp.status_code == 200
    assert b"library lobby" in view_resp.content
    assert b"akbar_chat" in view_resp.content


@pytest.mark.django_db
def test_unauthorized_user_cannot_send_exchange_message(client):
    """Third-party students cannot send messages on someone else's exchange."""
    akbar = User.objects.create_user(username='akbar_party_a', password='Password123!')
    StudentProfile.objects.create(user=akbar, student_id='240421')
    kamola = User.objects.create_user(username='kamola_party_b', password='Password123!')
    StudentProfile.objects.create(user=kamola, student_id='240594')
    stranger = User.objects.create_user(username='stranger_party_c', password='Password123!')
    StudentProfile.objects.create(user=stranger, student_id='240998')

    book = Book.objects.create(owner=kamola, title='Physics I', author='Halliday', min_duration_weeks=2)
    exchange = ExchangeRequest.objects.create(book=book, borrower=akbar, requested_duration_weeks=2)

    client.force_login(stranger)
    resp = client.post(reverse('send_exchange_message', kwargs={'pk': exchange.pk}), data={'message': "Hacking!"})
    assert resp.status_code == 302
    assert exchange.messages.count() == 0


@pytest.mark.django_db
def test_direct_book_handover_starts_active_loan(client):
    """Confirming direct physical handover transitions the exchange to ACTIVE_BORROWED and sets the due date."""
    borrower = User.objects.create_user(username='handover_borrower', password='Password123!')
    StudentProfile.objects.create(user=borrower, student_id='240422')
    lender = User.objects.create_user(username='handover_lender', password='Password123!')
    StudentProfile.objects.create(user=lender, student_id='240595')

    book = Book.objects.create(owner=lender, title='Algorithms', author='Sedgewick', min_duration_weeks=2, max_duration_weeks=6)
    exchange = ExchangeRequest.objects.create(
        book=book,
        borrower=borrower,
        requested_duration_weeks=3,
        status=ExchangeRequest.Status.AWAITING_DROPOFF,
    )

    client.force_login(lender)
    resp = client.post(reverse('confirm_handover', kwargs={'pk': exchange.pk}))
    assert resp.status_code == 302

    exchange.refresh_from_db()
    book.refresh_from_db()
    assert exchange.status == ExchangeRequest.Status.ACTIVE_BORROWED
    assert exchange.due_date == timezone.now().date() + timedelta(weeks=3)
    assert book.status == Book.Status.BORROWED


@pytest.mark.django_db
def test_direct_book_return_completes_exchange(client):
    """When the borrower returns the book directly, lender confirms and book is marked AVAILABLE."""
    borrower = User.objects.create_user(username='return_borrower', password='Password123!')
    StudentProfile.objects.create(user=borrower, student_id='240423')
    lender = User.objects.create_user(username='return_lender', password='Password123!')
    StudentProfile.objects.create(user=lender, student_id='240596')

    book = Book.objects.create(
        owner=lender,
        title='Linear Algebra',
        author='Strang',
        min_duration_weeks=2,
        status=Book.Status.BORROWED,
    )
    exchange = ExchangeRequest.objects.create(
        book=book,
        borrower=borrower,
        requested_duration_weeks=2,
        status=ExchangeRequest.Status.ACTIVE_BORROWED,
        due_date=timezone.now().date() + timedelta(weeks=2),
    )

    client.force_login(lender)
    resp = client.post(reverse('confirm_return', kwargs={'pk': exchange.pk}))
    assert resp.status_code == 302

    exchange.refresh_from_db()
    book.refresh_from_db()
    assert exchange.status == ExchangeRequest.Status.COMPLETED
    assert exchange.completed_at is not None
    assert book.status == Book.Status.AVAILABLE
