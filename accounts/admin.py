from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'email', 'role', 'is_staff', 'date_joined')
    list_filter   = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    fieldsets     = BaseUserAdmin.fieldsets + (
        ('Medical Info', {'fields': ('role', 'phone', 'date_of_birth', 'gender')}),
    )