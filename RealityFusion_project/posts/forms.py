"""
Forms for posts app
"""
from django import forms
from .models import Post, Story, Reel

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What\'s on your mind?'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('image'):
            raise forms.ValidationError("Please select an image for your post.")
        return cleaned

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['image', 'video', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Add a caption...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }

    def clean(self):
        cleaned = super().clean()
        image = cleaned.get('image')
        video = cleaned.get('video')
        if not image and not video:
            raise forms.ValidationError("Upload an image or video for your story.")
        return cleaned


class ReelForm(forms.ModelForm):
    class Meta:
        model = Reel
        fields = ['video', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Add a caption...'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if not video:
            raise forms.ValidationError("Please select a video for your reel.")
        ext = video.name.split('.')[-1].lower()
        valid_exts = ['mp4', 'mov', 'avi', 'webm', 'mkv', 'wmv', 'flv', 'm4v']
        if ext not in valid_exts:
            raise forms.ValidationError("Invalid file type. Please upload a video file (mp4, mov, webm, avi, etc).")
        if video.size > 52428800:
            raise forms.ValidationError("Video too large. Maximum size is 50MB.")
        return video
