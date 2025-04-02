from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, WebCategory, UserAllowedCategory, BlockedDomain
from django.utils.translation import gettext_lazy as _

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Security info'), {
            'fields': ('uuid', 'hashed_mac', 'requires_device_auth'),
            'classes': ('collapse',),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'uuid', 'is_staff', 'requires_device_auth')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'requires_device_auth')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'uuid')
    readonly_fields = ('uuid',)

class WebCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}  # Add slug field if needed

class UserAllowedCategoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('user__username', 'category__name')
    raw_id_fields = ('user',)

class BlockedDomainAdmin(admin.ModelAdmin):
    list_display = ('user', 'domain', 'original_category', 'blocked_at')
    list_filter = ('original_category', 'blocked_at')
    search_fields = ('user__username', 'domain', 'original_category__name')
    raw_id_fields = ('user',)
    date_hierarchy = 'blocked_at'

# Register your models here
admin.site.register(User, CustomUserAdmin)
admin.site.register(WebCategory, WebCategoryAdmin)
admin.site.register(UserAllowedCategory, UserAllowedCategoryAdmin)
admin.site.register(BlockedDomain, BlockedDomainAdmin)

# Optional: Customize admin site header
admin.site.site_header = "Website Classifier Administration"
admin.site.site_title = "Website Classifier Admin Portal"
admin.site.index_title = "Welcome to Website Classifier Admin"