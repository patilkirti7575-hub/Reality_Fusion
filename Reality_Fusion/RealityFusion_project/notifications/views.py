from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('actor', 'target_post', 'target_reel', 'target_story').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = self.get_queryset().filter(is_read=False).count()
        return context


class NotificationCountView(LoginRequiredMixin, TemplateView):
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return JsonResponse({'count': count})


class NotificationMarkReadView(LoginRequiredMixin, TemplateView):
    def post(self, request, notification_id):
        Notification.objects.filter(
            id=notification_id, recipient=request.user
        ).update(is_read=True)
        return JsonResponse({'status': 'ok'})


class NotificationMarkAllReadView(LoginRequiredMixin, TemplateView):
    def post(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return JsonResponse({'status': 'ok'})
