from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Book, ExchangeRequest, StudentProfile


class StudentRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=60,
        required=True,
        label="First Name",
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Akbar'}),
    )
    last_name = forms.CharField(
        max_length=60,
        required=True,
        label="Last Name",
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Evatov'}),
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={'placeholder': 'Choose a unique username'}),
        help_text="Used to log in to Compass Books.",
    )
    email = forms.EmailField(
        required=True,
        label="University Email",
        widget=forms.EmailInput(attrs={'placeholder': 'student@univ.edu'}),
    )
    student_id = forms.CharField(
        max_length=30,
        required=True,
        label="University Student ID",
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 240418'}),
        help_text="Your official campus ID number.",
    )
    telegram_username = forms.CharField(
        max_length=64,
        required=False,
        label="Telegram Username (optional)",
        widget=forms.TextInput(attrs={'placeholder': '@username'}),
        help_text="Allows fellow students to message you on Telegram to arrange book handovers.",
    )
    phone_number = forms.CharField(
        max_length=25,
        required=False,
        label="Phone Number (optional)",
        widget=forms.TextInput(attrs={'placeholder': '+998 90 123 45 67'}),
        help_text="For direct contact if needed.",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'At least 8 characters'}),
        label="Password",
        min_length=8,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Re-enter your password'}),
        label="Confirm Password",
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id'].strip().upper()
        if len(student_id) < 3:
            raise ValidationError("Please provide a valid University Student ID.")
        if StudentProfile.objects.filter(student_id__iexact=student_id).exists():
            raise ValidationError("This University Student ID is already registered.")
        return student_id

    def clean_telegram_username(self):
        tg = self.cleaned_data.get('telegram_username', '').strip()
        if tg:
            return tg.lstrip('@')
        return ''

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        user = User.objects.create_user(
            username=cleaned_data['username'],
            email=cleaned_data['email'],
            password=cleaned_data['password'],
            first_name=cleaned_data['first_name'],
            last_name=cleaned_data['last_name'],
        )
        profile = StudentProfile.objects.create(
            user=user,
            student_id=cleaned_data['student_id'],
            telegram_username=cleaned_data.get('telegram_username', '').strip(),
            phone_number=cleaned_data.get('phone_number', '').strip(),
        )
        return user


class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Your username', 'autofocus': True}),
        label="Username",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Your password'}),
        label="Password",
    )


class StudentProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=60, required=True, label="First Name")
    last_name = forms.CharField(max_length=60, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email Address")

    class Meta:
        model = StudentProfile
        fields = ['student_id', 'telegram_username', 'phone_number']
        labels = {
            'student_id': 'University Student ID',
            'telegram_username': 'Telegram Username',
            'phone_number': 'Phone Number',
        }
        widgets = {
            'telegram_username': forms.TextInput(attrs={'placeholder': '@username'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '+998 90 123 45 67'}),
        }
        help_texts = {
            'student_id': 'Your official campus student ID.',
            'telegram_username': 'Enables peers to contact you on Telegram to arrange book exchanges.',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id'].strip().upper()
        # Ensure uniqueness excluding this profile
        qs = StudentProfile.objects.filter(student_id__iexact=student_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This University Student ID is already linked to another student.")
        return student_id

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if self.user:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk)
            if qs.exists():
                raise ValidationError("This email is already in use by another account.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'cover_image',
            'category',
            'course_code',
            'isbn',
            'condition',
            'min_duration_weeks',
            'max_duration_weeks',
            'lender_requirements',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Operating System Concepts'}),
            'author': forms.TextInput(attrs={'placeholder': 'e.g., Abraham Silberschatz'}),
            'cover_image': forms.FileInput(attrs={'accept': 'image/*'}),
            'course_code': forms.TextInput(attrs={'placeholder': 'e.g., CS310 (optional)'}),
            'isbn': forms.TextInput(attrs={'placeholder': 'e.g., 978-1118063330 (optional)'}),
            'min_duration_weeks': forms.NumberInput(attrs={'min': 2, 'placeholder': '2'}),
            'max_duration_weeks': forms.NumberInput(attrs={'min': 2, 'placeholder': '4'}),
            'lender_requirements': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Any care rules for the borrower (e.g., 'Please do not highlight or write in margins. Keep dust jacket on.').",
            }),
        }
        labels = {
            'cover_image': 'Book Cover Photo (Optional)',
            'min_duration_weeks': 'Minimum Loan Duration (Weeks)',
            'max_duration_weeks': 'Maximum Loan Duration (Weeks)',
            'lender_requirements': 'Lender Rules & Care Instructions',
            'course_code': 'Course Code (Optional)',
            'isbn': 'ISBN (Optional)',
        }
        help_texts = {
            'cover_image': 'Upload a photo of the book showing its cover and current physical condition.',
            'min_duration_weeks': 'Platform policy: strictly at least 2 weeks.',
            'max_duration_weeks': 'Must be greater than or equal to minimum weeks.',
            'lender_requirements': 'The Student Council inspects condition upon drop-off and pickup based on your rules.',
        }

    def clean_min_duration_weeks(self):
        weeks = self.cleaned_data.get('min_duration_weeks')
        if weeks is not None and weeks < 2:
            raise ValidationError("Minimum loan duration must be at least 2 weeks.")
        return weeks

    def clean(self):
        cleaned_data = super().clean()
        min_w = cleaned_data.get('min_duration_weeks')
        max_w = cleaned_data.get('max_duration_weeks')
        if min_w is not None and max_w is not None and max_w < min_w:
            self.add_error('max_duration_weeks', f"Maximum duration cannot be less than minimum duration ({min_w} weeks).")
        return cleaned_data


class BorrowRequestForm(forms.ModelForm):
    class Meta:
        model = ExchangeRequest
        fields = ['requested_duration_weeks', 'borrower_note']
        widgets = {
            'requested_duration_weeks': forms.NumberInput(attrs={'min': 2}),
            'borrower_note': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "State your study goal or course requirement (e.g., 'Need for CS310 midterm study').",
            }),
        }
        labels = {
            'requested_duration_weeks': 'Borrow Duration (Weeks)',
            'borrower_note': 'Note to Lender (Optional)',
        }

    def __init__(self, *args, **kwargs):
        self.book = kwargs.pop('book', None)
        super().__init__(*args, **kwargs)
        if self.book:
            min_w = self.book.min_duration_weeks
            max_w = self.book.max_duration_weeks
            self.fields['requested_duration_weeks'].initial = min_w
            self.fields['requested_duration_weeks'].widget.attrs.update({
                'min': min_w,
                'max': max_w,
            })
            self.fields['requested_duration_weeks'].help_text = f"Allowed window for this book: {min_w} to {max_w} weeks."

    def clean_requested_duration_weeks(self):
        weeks = self.cleaned_data.get('requested_duration_weeks')
        if self.book and weeks is not None:
            if weeks < self.book.min_duration_weeks:
                raise ValidationError(f"Requested duration must be at least {self.book.min_duration_weeks} weeks for this book.")
            if weeks > self.book.max_duration_weeks:
                raise ValidationError(f"Requested duration cannot exceed {self.book.max_duration_weeks} weeks for this book.")
        return weeks


class ExchangeMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Type a message to coordinate where and when to meet on campus...',
            'style': 'flex:1;padding:var(--s2) var(--s3);border-radius:var(--radius-sm);border:1px solid var(--border);font-family:var(--font-sans);font-size:var(--t-small)',
            'autocomplete': 'off',
            'required': True,
        }),
        label='',
    )



