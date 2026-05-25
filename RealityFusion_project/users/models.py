from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Profile(models.Model):
    GENDER_CHOICES = [
        ('', 'Prefer not to say'),
        ('male', 'Male'),
        ('female', 'Female'),
        ('non-binary', 'Non-binary'),
        ('other', 'Other'),
    ]
    THEME_CHOICES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
        ('neon', 'Neon'),
        ('ocean', 'Ocean'),
    ]
    STORY_PRIVACY_CHOICES = [
        ('everyone', 'Everyone'),
        ('close_friends', 'Close Friends'),
        ('off', 'Off'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='', blank=True)
    is_verified = models.BooleanField(default=False)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    is_private = models.BooleanField(default=False)
    hide_activity_status = models.BooleanField(default=False)
    hide_like_counts = models.BooleanField(default=False)
    story_privacy = models.CharField(max_length=20, choices=STORY_PRIVACY_CHOICES, default='everyone')
    message_privacy = models.CharField(max_length=20, choices=[('everyone', 'Everyone'), ('followers', 'People You Follow'), ('off', 'Off')], default='everyone')
    active_status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"

class Follow(models.Model):
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.email} follows {self.to_user.email}"

class Block(models.Model):
    blocker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.email} blocked {self.blocked.email}"


class NotificationSetting(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_settings')
    likes = models.BooleanField(default=True)
    comments = models.BooleanField(default=True)
    follows = models.BooleanField(default=True)
    messages = models.BooleanField(default=True)
    story_replies = models.BooleanField(default=True)
    reel_likes = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    email_likes = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_follows = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification settings for {self.user.email}"


class LoginActivity(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='login_activities')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    is_active_session = models.BooleanField(default=True)

    class Meta:
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.email} logged in at {self.login_time}"


class UserSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=100)
    device_name = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"Session for {self.user.email}"


class RestrictedUser(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='restricted_users')
    restricted = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='restricted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'restricted')

    def __str__(self):
        return f"{self.user.email} restricted {self.restricted.email}"


class MutedUser(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='muted_users')
    muted = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='muted_by')
    mute_stories = models.BooleanField(default=True)
    mute_posts = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'muted')

    def __str__(self):
        return f"{self.user.email} muted {self.muted.email}"


class CloseFriend(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='close_friends')
    friend = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friend_of')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend')

    def __str__(self):
        return f"{self.user.email}'s close friend {self.friend.email}"


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        NotificationSetting.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
