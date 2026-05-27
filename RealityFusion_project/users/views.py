from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, TemplateView, UpdateView, ListView, FormView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.db import models as db_models
from django.contrib import messages
from .forms import (
    CustomUserCreationForm, CustomUserLoginForm, ProfileForm,
    PrivacyForm, NotificationSettingsForm, AppearanceForm,
    ChangePasswordCustomForm
)
from .models import (
    Profile, CustomUser, Follow, Block, NotificationSetting,
    LoginActivity, UserSession, RestrictedUser, MutedUser,
    CloseFriend
)
from RealityFusion_project.posts.models import Reel, TaggedItem, SavedPost, SavedReel
from RealityFusion_project.notifications.models import Notification

# ===== AUTH =====

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('feed')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

class CustomLoginView(LoginView):
    form_class = CustomUserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        ip = self.request.META.get('REMOTE_ADDR', '')
        ua = self.request.META.get('HTTP_USER_AGENT', '')
        device = 'Desktop'
        if 'Mobile' in ua or 'Android' in ua or 'iPhone' in ua:
            device = 'Mobile'
        elif 'Tablet' in ua or 'iPad' in ua:
            device = 'Tablet'
        LoginActivity.objects.create(
            user=user, ip_address=ip, user_agent=ua, device_type=device
        )
        return response

class CustomLogoutView(LogoutView):
    template_name = 'users/logout.html'
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        logout(request)
        return render(request, self.template_name)

    def get_next_page(self):
        return reverse_lazy('login')

# ===== PROFILE =====

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = kwargs.get('user_id')
        if user_id:
            context['profile_user'] = CustomUser.objects.get(id=user_id)
        else:
            context['profile_user'] = self.request.user
        if not hasattr(context['profile_user'], 'profile'):
            Profile.objects.create(user=context['profile_user'])
        pu = context['profile_user']
        context['profile'] = pu.profile
        context['is_following'] = Follow.objects.filter(
            from_user=self.request.user, to_user=pu
        ).exists()
        context['followers_count'] = pu.followers.count()
        context['following_count'] = pu.following.count()
        context['posts'] = pu.posts.select_related('user').order_by('-created_at')
        context['posts_count'] = pu.posts.count()
        context['reels'] = Reel.objects.filter(user=pu).select_related('user__profile').order_by('-created_at')
        context['reels_count'] = context['reels'].count()
        context['tagged_items'] = TaggedItem.objects.filter(user=pu).select_related('post', 'reel', 'tagged_by')
        return context

class UserListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = 'users/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        qs = CustomUser.objects.exclude(id=self.request.user.id)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(db_models.Q(email__icontains=q) | db_models.Q(username__icontains=q))
        return qs.annotate(
            post_count=db_models.Count('posts'),
            follower_count=db_models.Count('followers'),
        ).prefetch_related('profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_ids = [u.id for u in context['users']]
        following_ids = set(Follow.objects.filter(
            from_user=self.request.user, to_user_id__in=user_ids
        ).values_list('to_user_id', flat=True))
        context['following_ids'] = following_ids
        return context

class FollowingListView(LoginRequiredMixin, ListView):
    model = Follow
    template_name = 'users/following_list.html'
    context_object_name = 'follows'

    def get_queryset(self):
        return Follow.objects.filter(
            from_user=self.request.user
        ).select_related('to_user__profile').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        following_ids = list(Follow.objects.filter(
            from_user=self.request.user
        ).values_list('to_user_id', flat=True))
        context['following_ids'] = set(following_ids)
        return context


class FollowView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        to_user = get_object_or_404(CustomUser, id=user_id)
        if to_user == request.user:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        _, created = Follow.objects.get_or_create(from_user=request.user, to_user=to_user)
        if created:
            Notification.objects.create(
                recipient=to_user,
                actor=request.user,
                verb=Notification.FOLLOW,
            )
        return JsonResponse({
            'status': 'following',
            'followers_count': to_user.followers.count(),
            'following_count': request.user.following.count(),
        })

class UnfollowView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        to_user = get_object_or_404(CustomUser, id=user_id)
        Follow.objects.filter(from_user=request.user, to_user=to_user).delete()
        return JsonResponse({
            'status': 'not_following',
            'followers_count': to_user.followers.count(),
            'following_count': request.user.following.count(),
        })


class FollowersJSONView(LoginRequiredMixin, TemplateView):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        followers = Follow.objects.filter(to_user=user).select_related('from_user__profile').order_by('-created_at')
        data = []
        for f in followers:
            u = f.from_user
            is_following_back = Follow.objects.filter(from_user=request.user, to_user=u).exists()
            data.append({
                'id': u.id,
                'username': u.username or u.email,
                'email': u.email,
                'profile_pic': u.profile.profile_pic.url if hasattr(u, 'profile') and u.profile.profile_pic else None,
                'bio': u.profile.bio if hasattr(u, 'profile') else '',
                'is_following_back': is_following_back,
            })
        return JsonResponse({'users': data, 'count': len(data)})


class FollowingJSONView(LoginRequiredMixin, TemplateView):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        following = Follow.objects.filter(from_user=user).select_related('to_user__profile').order_by('-created_at')
        data = []
        for f in following:
            u = f.to_user
            is_following_back = Follow.objects.filter(from_user=request.user, to_user=u).exists()
            is_me = u.id == request.user.id
            data.append({
                'id': u.id,
                'username': u.username or u.email,
                'email': u.email,
                'profile_pic': u.profile.profile_pic.url if hasattr(u, 'profile') and u.profile.profile_pic else None,
                'bio': u.profile.bio if hasattr(u, 'profile') else '',
                'is_following_back': is_following_back,
                'is_me': is_me,
            })
        return JsonResponse({'users': data, 'count': len(data)})

class UserSearchJSON(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        users = CustomUser.objects.exclude(id=request.user.id)
        if q:
            users = users.filter(db_models.Q(email__icontains=q) | db_models.Q(username__icontains=q))
        users = users[:10]
        data = [{
            'id': u.id,
            'email': u.email,
            'username': u.username or u.email,
            'profile_pic': u.profile.profile_pic.url if hasattr(u, 'profile') and u.profile.profile_pic else None,
        } for u in users]
        return JsonResponse({'users': data})

# ===== SETTINGS HOME =====

class SettingsHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/settings_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['profile'] = profile
        notif_settings, _ = NotificationSetting.objects.get_or_create(user=self.request.user)
        context['notif_settings'] = notif_settings
        context['saved_posts_count'] = SavedPost.objects.filter(user=self.request.user).count()
        context['blocked_count'] = Block.objects.filter(blocker=self.request.user).count()
        context['restricted_count'] = RestrictedUser.objects.filter(user=self.request.user).count()
        context['close_friends_count'] = CloseFriend.objects.filter(user=self.request.user).count()
        return context


class SettingsProfileEditView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'settings/edit_profile.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self):
        if not hasattr(self.request.user, 'profile'):
            return Profile.objects.create(user=self.request.user)
        return self.request.user.profile

    def get_success_url(self):
        messages.success(self.request, 'Profile updated successfully!')
        return reverse_lazy('settings_profile_edit')

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SettingsChangePasswordView(LoginRequiredMixin, FormView):
    form_class = ChangePasswordCustomForm
    template_name = 'settings/change_password.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, 'Password changed successfully!')
        return redirect('settings_change_password')

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SettingsPrivacyView(LoginRequiredMixin, UpdateView):
    form_class = PrivacyForm
    template_name = 'settings/privacy.html'

    def get_object(self):
        return self.request.user.profile

    def get_success_url(self):
        messages.success(self.request, 'Privacy settings updated!')
        return reverse_lazy('settings_privacy')

    def form_valid(self, form):
        messages.success(self.request, 'Privacy settings updated!')
        return super().form_valid(form)


class SettingsNotificationsView(LoginRequiredMixin, UpdateView):
    form_class = NotificationSettingsForm
    template_name = 'settings/notifications.html'

    def get_object(self):
        obj, _ = NotificationSetting.objects.get_or_create(user=self.request.user)
        return obj

    def get_success_url(self):
        messages.success(self.request, 'Notification settings updated!')
        return reverse_lazy('settings_notifications')

    def form_valid(self, form):
        messages.success(self.request, 'Notification settings updated!')
        return super().form_valid(form)


class SettingsSecurityView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/security.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_activities'] = LoginActivity.objects.filter(user=self.request.user)[:20]
        context['active_sessions'] = UserSession.objects.filter(user=self.request.user)
        return context


class SettingsAppearanceView(LoginRequiredMixin, UpdateView):
    form_class = AppearanceForm
    template_name = 'settings/appearance.html'

    def get_object(self):
        return self.request.user.profile

    def get_success_url(self):
        messages.success(self.request, 'Theme updated!')
        return reverse_lazy('settings_appearance')

    def form_valid(self, form):
        messages.success(self.request, 'Theme updated!')
        return super().form_valid(form)


class SettingsSavedContentView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/saved_content.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['saved_posts'] = SavedPost.objects.filter(user=self.request.user).select_related('post__user__profile').order_by('-saved_at')
        context['saved_reels'] = SavedReel.objects.filter(user=self.request.user).select_related('reel__user__profile').order_by('-saved_at')
        return context


class SettingsBlockedUsersView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/blocked_users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blocked_users'] = Block.objects.filter(blocker=self.request.user).select_related('blocked__profile')
        context['restricted_users'] = RestrictedUser.objects.filter(user=self.request.user).select_related('restricted__profile')
        context['muted_users'] = MutedUser.objects.filter(user=self.request.user).select_related('muted__profile')
        return context


class SettingsStoryView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/story_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['close_friends'] = CloseFriend.objects.filter(user=self.request.user).select_related('friend__profile')
        context['profile'] = self.request.user.profile
        return context


class SettingsMessagingView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/messaging_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context


# ===== SETTINGS ACTIONS (POST-only) =====

class TogglePrivateView(LoginRequiredMixin, TemplateView):
    def post(self, request):
        profile = request.user.profile
        profile.is_private = not profile.is_private
        profile.save()
        return JsonResponse({'is_private': profile.is_private})


class ToggleActiveStatusView(LoginRequiredMixin, TemplateView):
    def post(self, request):
        profile = request.user.profile
        profile.active_status = not profile.active_status
        profile.save()
        return JsonResponse({'active_status': profile.active_status})


class UnblockUserView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        Block.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return JsonResponse({'status': 'unblocked'})


class RemoveRestrictedUserView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        RestrictedUser.objects.filter(user=request.user, restricted_id=user_id).delete()
        return JsonResponse({'status': 'removed'})


class UnmuteUserView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        MutedUser.objects.filter(user=request.user, muted_id=user_id).delete()
        return JsonResponse({'status': 'unmuted'})


class RemoveCloseFriendView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        CloseFriend.objects.filter(user=request.user, friend_id=user_id).delete()
        return JsonResponse({'status': 'removed'})


class AddCloseFriendView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        friend = get_object_or_404(CustomUser, id=user_id)
        CloseFriend.objects.get_or_create(user=request.user, friend=friend)
        return JsonResponse({'status': 'added'})


class LogoutAllDevicesView(LoginRequiredMixin, TemplateView):
    def post(self, request):
        from django.contrib.sessions.models import Session
        sessions = UserSession.objects.filter(user=request.user).exclude(is_current=True)
        for s in sessions:
            try:
                Session.objects.filter(session_key=s.session_key).delete()
            except Exception:
                pass
        sessions.delete()
        messages.success(request, 'Logged out of all other devices.')
        return redirect('settings_security')


class ClearLoginActivityView(LoginRequiredMixin, TemplateView):
    def post(self, request):
        LoginActivity.objects.filter(user=request.user).delete()
        return JsonResponse({'status': 'cleared'})
