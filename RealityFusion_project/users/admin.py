from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile, Follow

class CustomUserAdmin(UserAdmin):
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'username', 'password1', 'password2')}),)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    list_display = ('email', 'username', 'is_staff')
    ordering = ('created_at',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile)
admin.site.register(Follow)
