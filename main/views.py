from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    BookForm,
    BorrowRequestForm,
    ExchangeMessageForm,
    StudentLoginForm,
    StudentProfileUpdateForm,
    StudentRegistrationForm,
)
from .models import Book, ExchangeMessage, ExchangeRequest, StudentProfile


def home(request):
    """Clean homepage with quick access to student authentication and exchange overview."""
    return render(request, 'home.html')


def register(request):
    """
    Student registration view.
    Requires every student to register their official University Student ID.
    """
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to Compass Books, {user.first_name or user.username}! Your University ID has been registered.",
            )
            return redirect('profile')
    else:
        form = StudentRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Student sign-in view."""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next') or 'profile'
            return redirect(next_url)
    else:
        form = StudentLoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Student sign-out view."""
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect('home')


@login_required
def profile_view(request):
    """
    Student profile & digital University ID badge view.
    Displays verified campus ID and allows editing contact details.
    """
    profile, _ = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={'student_id': f"U-{request.user.id:05d}"},
    )

    if request.method == 'POST':
        form = StudentProfileUpdateForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile and contact information have been updated.")
            return redirect('profile')
    else:
        form = StudentProfileUpdateForm(instance=profile, user=request.user)

    return render(request, 'profile.html', {
        'profile': profile,
        'form': form,
    })


@login_required
def my_books(request):
    """
    My Books page: displays all textbooks and books owned/listed by the logged-in student.
    Shows inventory metrics, availability status, and direct management actions.
    """
    books = request.user.books.all()
    total_books = books.count()
    available_books = books.filter(status=Book.Status.AVAILABLE).count()
    loaned_books = books.filter(status=Book.Status.BORROWED).count()

    return render(request, 'my_books.html', {
        'books': books,
        'total_books': total_books,
        'available_books': available_books,
        'loaned_books': loaned_books,
    })


@login_required
def add_book(request):
    """
    Add a new book/textbook to the student's exchange library.
    Enforces minimum 2 weeks duration and custom lender rules.
    """
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.owner = request.user
            book.save()
            messages.success(request, f'"{book.title}" was successfully added to your books!')
            return redirect('my_books')
    else:
        form = BookForm()

    return render(request, 'book_form.html', {
        'form': form,
        'action_title': 'Add a Book to Lend',
        'is_edit': False,
    })


@login_required
def edit_book(request, pk):
    """Edit an existing book owned by the student."""
    book = get_object_or_404(Book, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{book.title}" has been updated.')
            return redirect('my_books')
    else:
        form = BookForm(instance=book)

    return render(request, 'book_form.html', {
        'form': form,
        'book': book,
        'action_title': f'Edit "{book.title}"',
        'is_edit': True,
    })


@login_required
def delete_book(request, pk):
    """Delete a book owned by the student."""
    book = get_object_or_404(Book, pk=pk, owner=request.user)

    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.info(request, f'"{title}" has been removed from your books.')
        return redirect('my_books')

    return render(request, 'confirm_delete_book.html', {
        'book': book,
    })


@login_required
def exchanges_view(request):
    """
    Direct Book Exchanges page: displays all books the student has borrowed or lent.
    Features direct peer coordination, in-platform chat, Telegram contacts, and loan status.
    """
    # 1. Books borrowed by this student
    borrowed_exchanges = (
        request.user.borrowed_exchanges
        .select_related('book', 'book__owner', 'book__owner__profile')
        .prefetch_related('messages', 'messages__sender', 'messages__sender__profile')
        .order_by('-created_at')
    )

    # 2. Lending requests for books owned by this student
    lending_exchanges = (
        ExchangeRequest.objects
        .filter(book__owner=request.user)
        .select_related('book', 'borrower', 'borrower__profile')
        .prefetch_related('messages', 'messages__sender', 'messages__sender__profile')
        .order_by('-created_at')
    )

    # Metrics
    active_loans_count = borrowed_exchanges.filter(status=ExchangeRequest.Status.ACTIVE_BORROWED).count()
    coordinating_count = (
        borrowed_exchanges.filter(status__in=[ExchangeRequest.Status.AWAITING_DROPOFF, ExchangeRequest.Status.AT_COUNCIL]).count() +
        lending_exchanges.filter(status__in=[ExchangeRequest.Status.AWAITING_DROPOFF, ExchangeRequest.Status.AT_COUNCIL]).count()
    )
    incoming_requests_count = lending_exchanges.filter(status=ExchangeRequest.Status.PENDING_APPROVAL).count()

    message_form = ExchangeMessageForm()

    return render(request, 'exchanges.html', {
        'borrowed_exchanges': borrowed_exchanges,
        'lending_exchanges': lending_exchanges,
        'active_loans_count': active_loans_count,
        'coordinating_count': coordinating_count,
        'incoming_requests_count': incoming_requests_count,
        'message_form': message_form,
    })


@login_required
def send_exchange_message(request, pk):
    """
    Direct in-platform chat between lender and borrower.
    Enables coordinating where and when to meet on campus.
    """
    exchange = get_object_or_404(ExchangeRequest, pk=pk)

    if request.user != exchange.borrower and request.user != exchange.book.owner:
        messages.error(request, "You are not authorized to message on this exchange.")
        return redirect('exchanges')

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if msg_text:
            ExchangeMessage.objects.create(
                exchange=exchange,
                sender=request.user,
                message=msg_text,
            )
            messages.success(request, "Message sent.")
        else:
            messages.warning(request, "Cannot send an empty message.")

    return redirect(f"{reverse('exchanges')}#exchange-{exchange.pk}")


@login_required
def confirm_handover(request, pk):
    """
    Lender or borrower confirms physical book handover on campus.
    Activates the loan, sets the due date, and updates book status to BORROWED.
    """
    exchange = get_object_or_404(ExchangeRequest, pk=pk)

    if request.user != exchange.borrower and request.user != exchange.book.owner:
        messages.error(request, "You are not authorized to confirm this exchange.")
        return redirect('exchanges')

    if exchange.status in [ExchangeRequest.Status.AWAITING_DROPOFF, ExchangeRequest.Status.AT_COUNCIL, ExchangeRequest.Status.PENDING_APPROVAL]:
        exchange.status = ExchangeRequest.Status.ACTIVE_BORROWED
        exchange.picked_up_at = timezone.now()
        exchange.due_date = timezone.now().date() + timedelta(weeks=exchange.requested_duration_weeks)
        exchange.save()

        exchange.book.status = Book.Status.BORROWED
        exchange.book.save()

        messages.success(
            request,
            f"Handover confirmed! Active loan started for \"{exchange.book.title}\". Due date: {exchange.due_date.strftime('%b %d, %Y')}.",
        )
    else:
        messages.warning(request, "Exchange is not currently awaiting handover.")

    return redirect(f"{reverse('exchanges')}#exchange-{exchange.pk}")


@login_required
def confirm_return(request, pk):
    """
    Lender confirms that the borrower has returned the book in person.
    Marks exchange as completed and makes the book available for loan again.
    """
    exchange = get_object_or_404(ExchangeRequest, pk=pk, book__owner=request.user)

    if exchange.status == ExchangeRequest.Status.ACTIVE_BORROWED:
        exchange.status = ExchangeRequest.Status.COMPLETED
        exchange.returned_at = timezone.now()
        exchange.completed_at = timezone.now()
        exchange.save()

        exchange.book.status = Book.Status.AVAILABLE
        exchange.book.save()

        messages.success(
            request,
            f"Return confirmed! \"{exchange.book.title}\" has been returned and is available again in your library.",
        )
    else:
        messages.warning(request, "Only active loans can be confirmed as returned.")

    return redirect(f"{reverse('exchanges')}#exchange-{exchange.pk}")


@login_required
def borrow_book(request, pk):
    """
    Submit a borrow request for a peer's book.
    Enforces minimum 2 weeks loan rules set by the lender.
    """
    book = get_object_or_404(Book, pk=pk)

    if book.owner == request.user:
        messages.warning(request, "You cannot borrow your own book.")
        return redirect('my_books')

    if not book.is_available:
        messages.warning(request, f'"{book.title}" is currently not available for borrowing.')
        return redirect('exchanges')

    if request.method == 'POST':
        form = BorrowRequestForm(request.POST, book=book)
        if form.is_valid():
            exchange = form.save(commit=False)
            exchange.book = book
            exchange.borrower = request.user
            exchange.status = ExchangeRequest.Status.PENDING_APPROVAL
            exchange.save()

            other_name = book.owner.get_full_name() or book.owner.username
            messages.success(
                request,
                f"Borrow request for \"{book.title}\" sent to {other_name}! Once approved, you can coordinate direct handover via in-platform chat or Telegram.",
            )
            return redirect('exchanges')
    else:
        form = BorrowRequestForm(book=book)

    return render(request, 'borrow_request.html', {
        'book': book,
        'form': form,
    })


@login_required
def cancel_exchange(request, pk):
    """Cancel a pending borrow request."""
    exchange = get_object_or_404(ExchangeRequest, pk=pk, borrower=request.user)

    if exchange.status == ExchangeRequest.Status.PENDING_APPROVAL:
        exchange.status = ExchangeRequest.Status.CANCELLED
        exchange.save()
        messages.info(request, f"Borrow request for \"{exchange.book.title}\" was cancelled.")
    else:
        messages.warning(request, "Only pending requests can be cancelled.")

    return redirect('exchanges')


@login_required
def respond_exchange(request, pk, action):
    """
    Lender responds to an incoming borrow request (approve or reject).
    On approval, status changes to accepted and students can coordinate meeting.
    """
    exchange = get_object_or_404(ExchangeRequest, pk=pk, book__owner=request.user)

    if exchange.status != ExchangeRequest.Status.PENDING_APPROVAL:
        messages.warning(request, "This request has already been processed.")
        return redirect('exchanges')

    if action == 'approve':
        exchange.status = ExchangeRequest.Status.AWAITING_DROPOFF
        exchange.approved_at = timezone.now()
        exchange.save()

        exchange.book.status = Book.Status.RESERVED
        exchange.book.save()

        borrower_profile = getattr(exchange.borrower, 'profile', None)
        tg_info = f" (@{borrower_profile.telegram_clean})" if borrower_profile and borrower_profile.telegram_clean else ""
        messages.success(
            request,
            f"You approved the request for \"{exchange.book.title}\"! You can now chat below or message on Telegram{tg_info} to arrange when and where to meet on campus.",
        )
    elif action == 'reject':
        exchange.status = ExchangeRequest.Status.REJECTED
        exchange.save()
        messages.info(request, f"You declined the request for \"{exchange.book.title}\".")

    return redirect('exchanges')


def exchange_catalog(request):
    """
    Exchange page where users browse all available books across campus to borrow.
    Provides search by title, author, course code, category, and condition.
    Students can select any available book and submit a borrow request directly.
    """
    books = (
        Book.objects
        .select_related('owner', 'owner__profile')
        .order_by('-created_at')
    )

    # Search keyword
    query = request.GET.get('q', '').strip()
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(course_code__icontains=query) |
            Q(isbn__icontains=query)
        )

    # Category filter
    category = request.GET.get('category', '').strip()
    if category:
        books = books.filter(category=category)

    # Condition filter
    condition = request.GET.get('condition', '').strip()
    if condition:
        books = books.filter(condition=condition)

    # Status filter (default: available only)
    status_filter = request.GET.get('status', 'available').strip()
    if status_filter == 'available':
        books = books.filter(status=Book.Status.AVAILABLE)

    total_available = Book.objects.filter(status=Book.Status.AVAILABLE).count()

    return render(request, 'exchange_catalog.html', {
        'books': books,
        'query': query,
        'selected_category': category,
        'selected_condition': condition,
        'status_filter': status_filter,
        'categories': Book.Category.choices,
        'conditions': Book.Condition.choices,
        'total_available': total_available,
    })

