import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import AIChat, AIChatMessage, AIContent, AIHistory
from .ai_service import AIService


class AIAssistantView(LoginRequiredMixin, TemplateView):
    template_name = 'assistant/ai_chat.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['chats'] = AIChat.objects.filter(user=self.request.user)[:20]
        ctx['recent_content'] = AIContent.objects.filter(user=self.request.user)[:10]
        return ctx


@method_decorator(csrf_exempt, name='dispatch')
class AIChatSendView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)

        message = data.get('message', '').strip()
        chat_id = data.get('chat_id')
        language = data.get('language', 'English')

        if not message:
            return JsonResponse({'status': 'error', 'error': 'Empty message'}, status=400)

        # Get or create chat
        if chat_id:
            try:
                chat = AIChat.objects.get(id=chat_id, user=request.user)
            except AIChat.DoesNotExist:
                return JsonResponse({'status': 'error', 'error': 'Chat not found'}, status=404)
        else:
            title = message[:60] + ('...' if len(message) > 60 else '')
            chat = AIChat.objects.create(user=request.user, title=title)

        # Save user message
        AIChatMessage.objects.create(chat=chat, role='user', content=message)

        # Build conversation history (last 20 messages for context)
        history = AIChatMessage.objects.filter(chat=chat).order_by('-created_at')[:20]
        history_list = [{'role': h.role, 'content': h.content} for h in reversed(history)]

        # Inject language preference into last user message
        if language and language != 'English':
            history_list[-1]['content'] += f'\n(Please respond in {language})'

        # Get AI response
        try:
            response = AIService.chat(history_list)
            if not response or not response.strip():
                response = "I'm sorry, I couldn't generate a response. Could you please rephrase your question?"
        except Exception as e:
            response = f"I encountered an error. Please try again in a moment."

        # Save AI response
        AIChatMessage.objects.create(chat=chat, role='assistant', content=response)

        # Log to history
        AIHistory.objects.create(
            user=request.user, action='chat',
            prompt=message, result=response[:300],
        )

        return JsonResponse({
            'status': 'success',
            'response': response,
            'chat_id': chat.id,
            'chat_title': chat.title,
        })


@method_decorator(csrf_exempt, name='dispatch')
class AIChatHistoryView(LoginRequiredMixin, TemplateView):
    def get(self, request, chat_id):
        try:
            chat = AIChat.objects.get(id=chat_id, user=request.user)
        except AIChat.DoesNotExist:
            return JsonResponse({'error': 'Chat not found'}, status=404)
        messages = AIChatMessage.objects.filter(chat=chat).values(
            'role', 'content', 'created_at'
        )
        return JsonResponse({
            'chat_id': chat.id,
            'chat_title': chat.title,
            'messages': list(messages),
        })


@method_decorator(csrf_exempt, name='dispatch')
class AIChatDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, chat_id):
        AIChat.objects.filter(id=chat_id, user=request.user).delete()
        return JsonResponse({'status': 'deleted'})


@method_decorator(csrf_exempt, name='dispatch')
class AIGenerateView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)

        content_type = data.get('type', 'caption')
        topic = data.get('topic', '').strip()
        language = data.get('language', 'English')

        service = AIService()
        try:
            if content_type == 'caption':
                result = service.generate_captions(topic, language)
            elif content_type == 'hashtag':
                result = service.generate_hashtags(topic, language)
            elif content_type == 'bio':
                vibe = data.get('vibe', 'cool')
                name = data.get('name', request.user.username)
                result = service.generate_bio(name, vibe, language)
            elif content_type == 'comment':
                comment = data.get('comment_text', '')
                tone = data.get('tone', 'friendly')
                result = service.generate_comment_reply(comment, tone, language)
            elif content_type == 'reel_script':
                result = service.generate_reel_script(topic, language)
            elif content_type == 'story_idea':
                result = service.generate_story_ideas(topic, language)
            elif content_type == 'translate':
                text = data.get('text', '')
                target = data.get('target_language', 'Hindi')
                result = service.translate_content(text, target)
            elif content_type == 'enhance':
                caption = data.get('caption', '')
                result = service.enhance_caption(caption, language)
            else:
                result = "Unknown content type. Try: caption, hashtag, bio, comment, reel_script, story_idea, translate, enhance."
        except Exception as e:
            result = f"Sorry, I couldn't generate that. Please try again."

        if not result or not result.strip():
            result = "I couldn't generate anything. Please try different input."

        # Save to AIContent
        prompt_text = topic or data.get('text', '') or data.get('caption', '') or data.get('comment_text', '')
        AIContent.objects.create(
            user=request.user, content_type=content_type,
            prompt=prompt_text, result=result, language=language,
        )

        return JsonResponse({'status': 'success', 'result': result})


@method_decorator(csrf_exempt, name='dispatch')
class AIHistoryView(LoginRequiredMixin, TemplateView):
    def get(self, request):
        history = AIContent.objects.filter(user=request.user)[:30]
        data = [{
            'id': h.id,
            'type': h.content_type,
            'prompt': h.prompt,
            'result': h.result,
            'language': h.language,
            'created_at': h.created_at.strftime('%b %d, %Y %I:%M %p'),
        } for h in history]
        return JsonResponse({'history': data})


@method_decorator(csrf_exempt, name='dispatch')
class AIChatsListView(LoginRequiredMixin, TemplateView):
    def get(self, request):
        chats = AIChat.objects.filter(user=request.user)[:20]
        data = [{
            'id': c.id,
            'title': c.title,
            'updated_at': c.updated_at.strftime('%b %d, %I:%M %p'),
        } for c in chats]
        return JsonResponse({'chats': data})
