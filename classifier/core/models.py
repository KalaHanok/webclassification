import uuid
import hashlib
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.utils.text import slugify

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, device_id=None, **extra_fields):
        if not username:
            raise ValueError('The Username must be set')
        user = self.model(username=username, device_id=device_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    """Custom user model with enhanced security features"""
    device_id = models.CharField(
        max_length=36,
        unique=True,
        null=False,  # Temporarily allow null for migration
        blank=False
    )
    
    # Remove default fields we don't need
    first_name = None
    last_name = None
    
    # Primary identifier (public)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    
    # Hashed device identifier (private)
    hashed_mac = models.CharField(
        max_length=64,
        validators=[MinLengthValidator(64)],
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )
    
    # Security flags
    requires_device_auth = models.BooleanField(
        default=False,
        help_text="Whether this device requires hardware verification"
    )
    
    # Device metadata
    device_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores device characteristics for fingerprinting"
    )
    
    # Security timestamps
    identifiers_rotated_at = models.DateTimeField(
        null=True,
        blank=True
    )
    last_auth_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['hashed_mac']),
        ]

    def __str__(self):
        return f"{self.username} ({self.uuid})"

    @classmethod
    def hash_identifier(cls, raw_value: str) -> str:
        """Secure one-way hash using site-specific salt"""
        if not raw_value:
            return None
        salted = f"{raw_value}:{settings.SECRET_KEY}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def rotate_identifiers(self):
        """Regenerate all security identifiers"""
        self.uuid = uuid.uuid4()
        if self.hashed_mac:
            # Re-hash the original MAC (first 12 chars) with new salt
            self.hashed_mac = self.hash_identifier(self.hashed_mac[:12])
        self.identifiers_rotated_at = timezone.now()
        self.save()

    def update_device_metadata(self, request=None):
        """Update device fingerprint data"""
        if not request:
            return
            
        self.device_metadata = {
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'ip': request.META.get('REMOTE_ADDR'),
            'screen': {
                'width': request.POST.get('screen_width'),
                'height': request.POST.get('screen_height'),
                'color_depth': request.POST.get('color_depth')
            },
            'platform': request.POST.get('platform'),
            'timezone': request.POST.get('timezone'),
            'touch_support': request.POST.get('touch_support'),
            'last_updated': timezone.now().isoformat()
        }
        self.save()

class WebCategory(models.Model):
    """Categories for website classification"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Social Media', 'News')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this category"
    )
    slug = models.SlugField(
        max_length=110,
        unique=True,
        blank=True,
        help_text="URL-friendly version of the name"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Whether this is a system-created category"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Web Category"
        verbose_name_plural = "Web Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class UserAllowedCategory(models.Model):
    """Categories a specific user is allowed to access"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='allowed_categories'
    )
    category = models.ForeignKey(
        WebCategory,
        on_delete=models.CASCADE,
        related_name='allowed_users'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this permission should automatically expire"
    )

    class Meta:
        unique_together = ('user', 'category')
        verbose_name = "User Allowed Category"
        verbose_name_plural = "User Allowed Categories"
        ordering = ['user', 'category__name']

    def __str__(self):
        return f"{self.user.username} can access {self.category.name}"

    @property
    def is_active(self):
        """Check if the permission is still valid"""
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True

class BlockedDomain(models.Model):
    """Domains blocked for specific users"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_domains'
    )
    domain = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Blocked domain name"
    )
    original_category = models.ForeignKey(
        WebCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Category that caused this block"
    )
    blocked_at = models.DateTimeField(
        auto_now_add=True
    )
    is_manual = models.BooleanField(
        default=False,
        help_text="Whether this was manually blocked by an admin"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional context about this block"
    )

    class Meta:
        unique_together = ('user', 'domain')
        verbose_name = "Blocked Domain"
        verbose_name_plural = "Blocked Domains"
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['-blocked_at']),
        ]

    def __str__(self):
        return f"{self.domain} blocked for {self.user.username}"

    def save(self, *args, **kwargs):
        """Clean domain before saving"""
        self.domain = self.domain.lower().strip()
        super().save(*args, **kwargs)



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        from rest_framework.authtoken.models import Token
        Token.objects.create(user=instance)