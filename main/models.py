from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class StudentProfile(models.Model):
    """
    University student profile extension.
    Every student registers their official University Student ID, which is verified
    in-person by the Student Council when handing over or picking up books.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(
        max_length=30,
        unique=True,
        help_text="University Student ID (e.g., 240418) verified in person.",
    )
    phone_number = models.CharField(
        max_length=25,
        blank=True,
        help_text="Phone number for direct student contact.",
    )
    telegram_username = models.CharField(
        max_length=64,
        blank=True,
        help_text="Telegram username (e.g. @akbarevatov) for direct peer exchange coordination.",
    )
    is_council_member = models.BooleanField(
        default=False,
        help_text="Designates whether this student is an authorized staff member.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def telegram_clean(self):
        if not self.telegram_username:
            return ""
        return self.telegram_username.strip().lstrip('@')

    @property
    def telegram_url(self):
        clean = self.telegram_clean
        return f"https://t.me/{clean}" if clean else ""

    class Meta:
        ordering = ['student_id']
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} (ID: {self.student_id})"


class Book(models.Model):
    """
    Book listed by a student for peer exchange.
    Enforces the platform rule: minimum loan duration must be at least 2 weeks.
    Lenders can set custom care instructions and conditions.
    """
    class Condition(models.TextChoices):
        LIKE_NEW = 'LIKE_NEW', 'Like New'
        VERY_GOOD = 'VERY_GOOD', 'Very Good'
        GOOD = 'GOOD', 'Good'
        FAIR = 'FAIR', 'Fair'

    class Category(models.TextChoices):
        COMPUTER_SCIENCE = 'CS', 'Computer Science & IT'
        MATHEMATICS = 'MATH', 'Mathematics & Statistics'
        ENGINEERING = 'ENG', 'Engineering & Physics'
        BUSINESS = 'BUS', 'Business & Economics'
        NATURAL_SCIENCES = 'SCI', 'Natural & Life Sciences'
        HUMANITIES = 'HUM', 'Humanities & Social Sciences'
        LITERATURE = 'LIT', 'Literature & Fiction'
        LANGUAGES = 'LANG', 'Languages & Linguistics'
        OTHER = 'OTHER', 'Other Academic'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        RESERVED = 'RESERVED', 'Reserved'
        BORROWED = 'BORROWED', 'Currently Loaned'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=200, help_text="Full title of the textbook or book.")
    author = models.CharField(max_length=150, help_text="Author or primary editor.")
    isbn = models.CharField(max_length=20, blank=True, help_text="Optional ISBN (10 or 13 digits).")
    cover_image = models.ImageField(
        upload_to='book_covers/',
        blank=True,
        null=True,
        help_text="Upload a clear photo of the book cover showing its physical condition.",
    )
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.COMPUTER_SCIENCE,
    )
    course_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g., CS310, MATH221 (optional course tag).",
    )
    condition = models.CharField(
        max_length=15,
        choices=Condition.choices,
        default=Condition.VERY_GOOD,
    )
    min_duration_weeks = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(2)],
        help_text="Minimum loan duration in weeks (strictly >= 2 weeks).",
    )
    max_duration_weeks = models.PositiveIntegerField(
        default=4,
        validators=[MinValueValidator(2)],
        help_text="Maximum loan duration in weeks.",
    )
    lender_requirements = models.TextField(
        blank=True,
        help_text="Your rules for the borrower (e.g., 'No highlighter markings', 'Return with dust jacket').",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Book'
        verbose_name_plural = 'Books'

    def clean(self):
        super().clean()
        if self.min_duration_weeks is not None and self.min_duration_weeks < 2:
            raise ValidationError({
                'min_duration_weeks': 'Minimum loan duration must be at least 2 weeks.'
            })
        if self.min_duration_weeks is not None and self.max_duration_weeks is not None:
            if self.max_duration_weeks < self.min_duration_weeks:
                raise ValidationError({
                    'max_duration_weeks': f'Maximum loan duration cannot be less than minimum loan duration ({self.min_duration_weeks} weeks).'
                })

    def __str__(self):
        return f"{self.title} by {self.author} ({self.owner.username})"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE


class ExchangeRequest(models.Model):
    """
    Peer-to-peer book exchange loan lifecycle managed through the Student Council desk.
    """
    class Status(models.TextChoices):
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Lender Approval'
        AWAITING_DROPOFF = 'AWAITING_DROPOFF', 'Accepted — Coordinating Handover'
        ACTIVE_BORROWED = 'ACTIVE_BORROWED', 'Active Loan'
        COMPLETED = 'COMPLETED', 'Completed & Returned'
        REJECTED = 'REJECTED', 'Declined'
        CANCELLED = 'CANCELLED', 'Cancelled'
        AT_COUNCIL = 'AT_COUNCIL', 'Coordinating Handover'
        RETURNED_TO_COUNCIL = 'RETURNED_TO_COUNCIL', 'Returned'

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='exchanges')
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_exchanges')
    requested_duration_weeks = models.PositiveIntegerField(
        default=2,
        help_text="Requested duration in weeks (strictly >= book's minimum).",
    )
    borrower_note = models.TextField(
        blank=True,
        help_text="Note to lender regarding study purpose or course requirement.",
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING_APPROVAL,
    )

    # Lifecycle timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    dropped_off_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional peer exchange meeting notes
    dropoff_condition_notes = models.TextField(
        blank=True,
        help_text="Meeting / handover notes between students.",
    )
    return_condition_notes = models.TextField(
        blank=True,
        help_text="Return condition notes.",
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Book Exchange'
        verbose_name_plural = 'Book Exchanges'

    def clean(self):
        super().clean()
        if hasattr(self, 'book') and hasattr(self, 'borrower') and self.book_id and self.borrower_id:
            if self.book.owner_id == self.borrower_id:
                raise ValidationError("You cannot borrow your own book.")
            if self.requested_duration_weeks:
                if self.requested_duration_weeks < self.book.min_duration_weeks:
                    raise ValidationError({
                        'requested_duration_weeks': f"Requested duration must be at least {self.book.min_duration_weeks} weeks."
                    })
                if self.requested_duration_weeks > self.book.max_duration_weeks:
                    raise ValidationError({
                        'requested_duration_weeks': f"Requested duration cannot exceed {self.book.max_duration_weeks} weeks."
                    })

    @property
    def is_overdue(self):
        if self.status == self.Status.ACTIVE_BORROWED and self.due_date:
            return self.due_date < timezone.now().date()
        return False

    @property
    def days_remaining(self):
        if self.status == self.Status.ACTIVE_BORROWED and self.due_date:
            return (self.due_date - timezone.now().date()).days
        return None

    def __str__(self):
        return f"{self.borrower.username} borrowed {self.book.title} ({self.get_status_display()})"


class ExchangeMessage(models.Model):
    """
    Direct in-platform chat messages between lender and borrower to coordinate
    meeting location and time on campus.
    """
    exchange = models.ForeignKey(ExchangeRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_exchange_messages')
    message = models.TextField(help_text="Message text for meeting coordination.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Exchange Message'
        verbose_name_plural = 'Exchange Messages'

    def __str__(self):
        return f"{self.sender.username} on #{self.exchange_id} ({self.created_at:%b %d, %H:%M})"

