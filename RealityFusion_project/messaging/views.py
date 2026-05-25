import json
import requests
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import models
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Message, MessageReaction, DeletedMessage
from users.models import CustomUser
from notifications.models import Notification


class ChatListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'messaging/chat_list.html'
    context_object_name = 'conversations'

    def get_queryset(self):
        users = CustomUser.objects.filter(
            models.Q(sent_messages__receiver=self.request.user) |
            models.Q(received_messages__sender=self.request.user)
        ).distinct()
        return users.exclude(id=self.request.user.id)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for u in ctx['conversations']:
            last = Message.objects.filter(
                models.Q(sender=self.request.user, receiver=u) |
                models.Q(sender=u, receiver=self.request.user),
                is_deleted=False
            ).order_by('-timestamp').first()
            if last:
                if last.image:
                    u.last_msg_content = '[Image]'
                elif last.video:
                    u.last_msg_content = '[Video]'
                else:
                    u.last_msg_content = last.content[:60] if last.content else ('[GIF]' if last.gif_url else '[Shared]')
                u.last_msg_timestamp = last.timestamp
                u.last_msg_is_me = last.sender == self.request.user
            else:
                u.last_msg_content = None
            u.unread_count = Message.objects.filter(
                sender=u, receiver=self.request.user, is_read=False, is_deleted=False
            ).count()
        return ctx


class ChatView(LoginRequiredMixin, TemplateView):
    template_name = 'messaging/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receiver_id = kwargs.get('user_id')
        context['receiver'] = get_object_or_404(CustomUser, id=receiver_id)
        context['messages'] = Message.objects.filter(
            sender__in=[self.request.user, context['receiver']],
            receiver__in=[self.request.user, context['receiver']]
        ).select_related('sender', 'receiver', 'shared_post', 'shared_reel', 'reply_to').prefetch_related(
            'reactions', 'deleted_records'
        ).order_by('timestamp')
        Message.objects.filter(sender=context['receiver'], receiver=self.request.user, is_read=False).update(is_read=True)
        return context


class MessageListView(LoginRequiredMixin, TemplateView):
    def get(self, request, user_id):
        receiver = get_object_or_404(CustomUser, id=user_id)
        messages = Message.objects.filter(
            sender__in=[request.user, receiver],
            receiver__in=[request.user, receiver]
        ).select_related('sender', 'shared_post', 'shared_reel').prefetch_related(
            'reactions__user', 'deleted_records'
        ).order_by('timestamp')

        # Mark as read
        messages.filter(receiver=request.user, is_read=False).update(is_read=True)

        result = []
        for m in messages:
            # Check if deleted for current user
            if m.is_deleted:
                continue
            if DeletedMessage.objects.filter(message=m, user=request.user).exists():
                continue

            # Reactions
            reactions = {}
            for r in m.reactions.all():
                if r.emoji not in reactions:
                    reactions[r.emoji] = {'count': 0, 'users': []}
                reactions[r.emoji]['count'] += 1
                reactions[r.emoji]['users'].append(r.user.email)
            # Check if current user reacted
            user_reacted = m.reactions.filter(user=request.user).first()

            reply_data = None
            if m.reply_to:
                reply_data = {
                    'id': m.reply_to.id,
                    'content': m.reply_to.content[:80] if m.reply_to.content else '',
                    'sender': m.reply_to.sender.email,
                }

            msg_data = {
                'id': m.id,
                'sender': m.sender.email,
                'sender_id': m.sender.id,
                'content': m.content,
                'timestamp': m.timestamp.strftime('%I:%M %p'),
                'is_me': m.sender == request.user,
                'is_read': m.is_read,
                'is_delivered': m.is_delivered,
                'gif_url': m.gif_url,
                'image_url': m.image.url if m.image else None,
                'video_url': m.video.url if m.video else None,
                'reactions': reactions,
                'user_reacted': user_reacted.emoji if user_reacted else None,
                'reply_to': reply_data,
                'shared_post': {
                    'id': m.shared_post.id,
                    'image_url': m.shared_post.image.url if m.shared_post and m.shared_post.image else None,
                    'caption': m.shared_post.content if m.shared_post else '',
                } if m.shared_post else None,
                'shared_reel': {
                    'id': m.shared_reel.id,
                    'video_url': m.shared_reel.video.url if m.shared_reel else None,
                    'caption': m.shared_reel.caption if m.shared_reel else '',
                } if m.shared_reel else None,
            }
            result.append(msg_data)

        return JsonResponse({'messages': result})

    def post(self, request, user_id):
        receiver = get_object_or_404(CustomUser, id=user_id)
        content = request.POST.get('content', '').strip()
        gif_url = request.POST.get('gif_url', '').strip()
        reply_to_id = request.POST.get('reply_to_id')
        image_file = request.FILES.get('image')
        video_file = request.FILES.get('video')

        if not content and not gif_url and not image_file and not video_file:
            return JsonResponse({'status': 'error', 'error': 'Empty message'}, status=400)

        kwargs = {'sender': request.user, 'receiver': receiver}
        if content:
            kwargs['content'] = content
        if gif_url:
            kwargs['gif_url'] = gif_url
        if image_file:
            kwargs['image'] = image_file
        if video_file:
            kwargs['video'] = video_file
        if reply_to_id:
            kwargs['reply_to_id'] = reply_to_id

        Message.objects.create(**kwargs)
        return JsonResponse({'status': 'success'})


@method_decorator(csrf_exempt, name='dispatch')
class MessageDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        if message.sender != request.user:
            return JsonResponse({'status': 'error', 'error': 'Not your message'}, status=403)

        mode = request.POST.get('mode', 'me')

        if mode == 'everyone':
            message.is_deleted = True
            message.content = ''
            message.gif_url = ''
            message.image.delete(save=False)
            message.video.delete(save=False)
            message.save(update_fields=['is_deleted', 'content', 'gif_url', 'image', 'video'])
        else:
            DeletedMessage.objects.get_or_create(message=message, user=request.user, defaults={'deleted_for_everyone': False})

        return JsonResponse({'status': 'deleted'})


@method_decorator(csrf_exempt, name='dispatch')
class MessageReactionView(LoginRequiredMixin, TemplateView):
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        emoji = request.POST.get('emoji', '').strip()
        if not emoji:
            return JsonResponse({'status': 'error', 'error': 'Missing emoji'}, status=400)

        existing = MessageReaction.objects.filter(message=message, user=request.user, emoji=emoji).first()
        if existing:
            existing.delete()
            return JsonResponse({'status': 'removed', 'emoji': emoji})
        else:
            MessageReaction.objects.create(message=message, user=request.user, emoji=emoji)
            return JsonResponse({'status': 'added', 'emoji': emoji})


# Hardcoded fallback GIF IDs (from GIPHY CDN) — used when the live API is unavailable
FALLBACK_GIFS = [
    {'id': 'l0HlNQ03J5JxX6lAc', 'title': 'Celebration'},
    {'id': '3o7abKh8O8sdqW7Hle', 'title': 'Happy Dance'},
    {'id': 'l0MYt5jPR6QX5pnqM', 'title': 'Facepalm'},
    {'id': '3oKIPnAiaMCws8nO3y', 'title': 'OMG'},
    {'id': 'xT5LMFvXQ6j5H5ZRK', 'title': 'LOL'},
    {'id': '3o6Zt481isNVuQI1lW', 'title': 'Clapping'},
    {'id': '11sBLVxNs7o6N2', 'title': 'Shrug'},
    {'id': 'wOMZwGjJjRmSZ6L9qF', 'title': 'High Five'},
    {'id': '3o7aTskHEUdgCQAXde', 'title': 'Mind Blown'},
    {'id': '26ufdipQqU2lhNA4g', 'title': 'Happy Birthday'},
    {'id': 'xT9IgzoKnw2iG5G4I', 'title': 'Congratulations'},
    {'id': 'l4FGI8EVGZ6HkcGFi', 'title': 'Thank You'},
    {'id': '3o7TKsQ8n7L6H4QpS', 'title': 'Sorry'},
    {'id': 'l2JegCHJ4A4xQ3FSM', 'title': 'Good Luck'},
    {'id': '3o7btPCzjUYj4G6kOA', 'title': 'Deal With It'},
    {'id': '1B0CQ2wyoAO5G', 'title': 'Party'},
    {'id': 'l2R07bCQvL5gRGwPm', 'title': 'Applause'},
    {'id': '2v1LADv1cdcOo', 'title': 'Yes'},
    {'id': '13HgwGsXF0ai2y', 'title': 'Nope'},
    {'id': 'Qr8VxG7E5C9Zm', 'title': 'Crying'},
    {'id': 'JC9vfnEGuNYMA', 'title': 'Frustrated'},
    {'id': 'l2SpWuxiCKwd7OPeg', 'title': 'Sleepy'},
    {'id': 'ZkYPNjrMU8iJ6', 'title': 'Dancing'},
    {'id': 'fdIiCso28gf3pSFMZr', 'title': 'Cheers'},
    {'id': 'RJA1vjsSCQoNi', 'title': 'Amazing'},
]

def build_gif_response(gif_list, cdn_base='https://media2.giphy.com/media'):
    """Convert a list of GIPHY gif dicts (with id/title) into full response format."""
    result = []
    for g in gif_list:
        gid = g['id']
        result.append({
            'id': gid,
            'url': f'{cdn_base}/{gid}/giphy.gif',
            'preview': f'{cdn_base}/{gid}/200.gif',
            'width': '200',
            'height': '200',
            'title': g.get('title', ''),
        })
    return result

class GifSearchView(LoginRequiredMixin, TemplateView):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        api_key = getattr(settings, 'GIPHY_API_KEY', 'dc6zaTOxFJmzC')
        limit = 20

        # Try GIPHY API first
        if query:
            url = f'https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={query}&limit={limit}&rating=g'
        else:
            url = f'https://api.giphy.com/v1/gifs/trending?api_key={api_key}&limit={limit}&rating=g'

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                api_gifs = data.get('data', [])
                if api_gifs:
                    gifs = [{
                        'id': g['id'],
                        'url': g['images']['original']['url'],
                        'preview': g['images']['fixed_height_small']['url'] if 'fixed_height_small' in g['images'] else g['images']['fixed_height']['url'],
                        'width': g['images']['fixed_height']['width'],
                        'height': g['images']['fixed_height']['height'],
                        'title': g.get('title', ''),
                    } for g in api_gifs]
                    return JsonResponse({'gifs': gifs})
        except Exception:
            pass

        # Fallback: serve hardcoded GIFs from GIPHY CDN
        gifs = build_gif_response(FALLBACK_GIFS)
        return JsonResponse({'gifs': gifs})


class SharePostView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        post_id = request.POST.get('post_id')
        reel_id = request.POST.get('reel_id')
        user_id = request.POST.get('user_id')
        if not user_id:
            return JsonResponse({'status': 'error', 'error': 'Missing user_id'}, status=400)
        receiver = get_object_or_404(CustomUser, id=user_id)
        if receiver == request.user:
            return JsonResponse({'status': 'error', 'error': 'Cannot share with yourself'}, status=400)
        from posts.models import Post, Reel
        if post_id:
            post = get_object_or_404(Post, id=post_id)
            content = ''
            Message.objects.create(sender=request.user, receiver=receiver, content=content, shared_post=post)
            Notification.objects.get_or_create(
                recipient=receiver,
                actor=request.user,
                verb=Notification.SHARE,
                target_post=post,
            )
        elif reel_id:
            reel = get_object_or_404(Reel, id=reel_id)
            content = ''
            Message.objects.create(sender=request.user, receiver=receiver, content=content, shared_reel=reel)
            reel.views += 1
            reel.save(update_fields=['views'])
            if reel.user != request.user:
                Notification.objects.get_or_create(
                    recipient=reel.user,
                    actor=request.user,
                    verb=Notification.REEL_SHARE,
                    target_reel=reel,
                )
        else:
            return JsonResponse({'status': 'error', 'error': 'Missing post_id or reel_id'}, status=400)
        return JsonResponse({'status': 'success'})


class TypingStatusView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        is_typing = request.POST.get('typing') == 'true'
        # Store in session or cache (simple approach: session)
        key = f'typing_{request.user.id}_{user_id}'
        if is_typing:
            request.session[key] = True
        else:
            request.session.pop(key, None)
        return JsonResponse({'status': 'ok'})

    def get(self, request, user_id):
        key = f'typing_{user_id}_{request.user.id}'
        is_typing = request.session.get(key, False)
        return JsonResponse({'typing': is_typing})
