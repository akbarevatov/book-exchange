from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Book, ExchangeMessage, ExchangeRequest, StudentProfile


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'


class UserAdmin(BaseUserAdmin):
    inlines = [StudentProfileInline]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'get_full_name', 'get_username', 'telegram_username', 'phone_number', 'created_at')
    search_fields = ('student_id', 'telegram_username', 'user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('created_at',)

    def get_full_name(self, obj):
        return obj.user.get_full_name() or '—'
    get_full_name.short_description = 'Full Name'

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'owner', 'category', 'condition', 'min_duration_weeks', 'max_duration_weeks', 'status', 'created_at')
    list_filter = ('category', 'condition', 'status', 'created_at')
    search_fields = ('title', 'author', 'course_code', 'isbn', 'owner__username', 'owner__first_name', 'owner__last_name')


class ExchangeMessageInline(admin.TabularInline):
    model = ExchangeMessage
    extra = 0
    readonly_fields = ('sender', 'message', 'created_at')


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ('book', 'borrower', 'requested_duration_weeks', 'status', 'due_date', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('book__title', 'book__author', 'borrower__username', 'borrower__first_name', 'borrower__last_name')
    inlines = [ExchangeMessageInline]


@admin.register(ExchangeMessage)
class ExchangeMessageAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'sender', 'message', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('exchange__book__title', 'sender__username', 'message')


# Re-register UserAdmin with the inline profile
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
