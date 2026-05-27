"""
Forms for users app - Registration, Login, Profile, Settings
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import password_validation
from .models import CustomUser, Profile, NotificationSetting

class CustomUserCreationForm(forms.ModelForm):
    """Form for user registration"""
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    class Meta:
        model = CustomUser
        fields = ['email', 'username']

    def clean_password2(self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data['password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class CustomUserLoginForm(AuthenticationForm):
    """Login form with email field"""
    username = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

class ProfileForm(forms.ModelForm):
    """Form for editing user profile (full settings version)"""
    email = forms.EmailField(required=True, label='Email')
    username = forms.CharField(max_length=50, required=False, label='Username')

    class Meta:
        model = Profile
        fields = ['profile_pic', 'bio', 'website', 'phone_number', 'gender']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Bio'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Website URL'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email
            self.fields['username'].initial = self.user.username

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.email = self.cleaned_data['email']
            self.user.username = self.cleaned_data['username']
            if commit:
                self.user.save()
                profile.save()
        return profile


class PrivacyForm(forms.ModelForm):
    """Form for privacy settings"""
    class Meta:
        model = Profile
        fields = ['is_private', 'hide_activity_status', 'hide_like_counts', 'story_privacy', 'message_privacy']
        widgets = {
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hide_activity_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hide_like_counts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'story_privacy': forms.Select(attrs={'class': 'form-control'}),
            'message_privacy': forms.Select(attrs={'class': 'form-control'}),
        }


class NotificationSettingsForm(forms.ModelForm):
    """Form for notification settings"""
    class Meta:
        model = NotificationSetting
        fields = [
            'likes', 'comments', 'follows', 'messages',
            'story_replies', 'reel_likes',
            'email_notifications', 'email_likes', 'email_comments',
            'email_follows', 'email_messages',
        ]
        widgets = {field: forms.CheckboxInput(attrs={'class': 'form-check-input'})
                   for field in ['likes', 'comments', 'follows', 'messages',
                                 'story_replies', 'reel_likes',
                                 'email_notifications', 'email_likes', 'email_comments',
                                 'email_follows', 'email_messages']}


class AppearanceForm(forms.ModelForm):
    """Form for appearance/theme settings"""
    class Meta:
        model = Profile
        fields = ['theme']
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-control'}),
        }


class ChangePasswordCustomForm(PasswordChangeForm):
    """Custom password change form with Instagram styling"""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'}),
        label='Current Password'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        label='New Password',
        help_text=password_validation.password_validators_help_text_html()
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label='Confirm New Password'
    )
