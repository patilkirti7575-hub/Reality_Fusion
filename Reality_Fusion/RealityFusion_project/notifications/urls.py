from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notifications'),
    path('count/', views.NotificationCountView.as_view(), name='notification_count'),
    path('<int:notification_id>/read/', views.NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('read-all/', views.NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
]
