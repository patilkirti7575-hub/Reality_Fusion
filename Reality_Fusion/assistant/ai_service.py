import json
import time
import requests
from django.conf import settings


SYSTEM_PROMPT = (
    "You are RealityAI, an intelligent creative assistant inside RealityFusion — a social media platform. "
    "You help users with content creation, captions, hashtags, reels, stories, engagement tips, "
    "and general social media advice.\n\n"
    "Rules:\n"
    "- Understand the user's question fully and answer it directly.\n"
    "- Be concise but helpful — 2-5 sentences typically.\n"
    "- Use simple language; avoid markdown unless formatting helps.\n"
    "- Respond in the SAME LANGUAGE the user wrote in (English, Hindi, Hinglish, Marathi, etc.).\n"
    "- If the user asks in Hinglish, reply in Hinglish naturally.\n"
    "- If the user asks about something off-topic, politely redirect to social media help.\n"
    "- Use emojis sparingly.\n"
    "- NEVER give generic greetings — answer the actual question."
)


class AIService:

    @staticmethod
    def chat(messages):
        """Full conversation with system prompt + history."""
        full = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for m in messages:
            full.append({'role': m['role'], 'content': m['content']})
        return _call_openai(full)

    @staticmethod
    def generate_captions(topic, language='English', count=5):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Generate {count} engaging social media captions about '{topic}' "
                f"in {language}. Number each one."
            )},
        ])

    @staticmethod
    def generate_hashtags(topic, language='English', count=20):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Generate {count} trending hashtags about '{topic}' in {language}. "
                f"Mix popular and niche tags."
            )},
        ])

    @staticmethod
    def generate_bio(name, vibe, language='English'):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Create 3 profile bio options for '{name}' with a '{vibe}' vibe in {language}. "
                f"Keep each under 150 chars."
            )},
        ])

    @staticmethod
    def generate_comment_reply(comment_text, tone='friendly', language='English'):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Write a {tone} reply to this comment in {language}: '{comment_text}'"
            )},
        ])

    @staticmethod
    def generate_reel_script(topic, language='English'):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Create a viral reel script about '{topic}' in {language}. "
                f"Include: hook, body, CTA. Under 60 seconds."
            )},
        ])

    @staticmethod
    def generate_story_ideas(topic, language='English'):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Generate 5 interactive story ideas about '{topic}' in {language} "
                f"with poll and question suggestions."
            )},
        ])

    @staticmethod
    def translate_content(text, target_language):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f"Translate this to {target_language}: '{text}'"},
        ])

    @staticmethod
    def enhance_caption(caption, language='English'):
        return _call_openai([
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': (
                f"Enhance this {language} caption to be more engaging. "
                f"Keep the original meaning. Caption: '{caption}'"
            )},
        ])


def _call_openai(messages, model=None, temperature=0.7, max_tokens=1024):
    """Core OpenAI caller — falls back to smart mock if no API key."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    api_key = api_key.strip()

    if api_key:
        model = model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        try:
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                choice = data['choices'][0]['message']
                return choice['content']
            else:
                error_detail = resp.text[:300]
                return _smart_mock(messages, f"API error {resp.status_code}: {error_detail}")
        except requests.exceptions.Timeout:
            return _smart_mock(messages, "Timeout: OpenAI took too long to respond.")
        except Exception as e:
            return _smart_mock(messages, f"Connection error: {str(e)[:100]}")

    return _smart_mock(messages)


def _smart_mock(messages, debug_note=None):
    """
    Smart fallback that actually reads the user's question and responds contextually.
    Supports English, Hindi, Hinglish, Marathi.
    """
    # Extract user messages, ignoring system prompts
    user_msgs = [m['content'] for m in messages if m['role'] == 'user']
    if not user_msgs:
        return _greeting()

    query = user_msgs[-1].strip()
    q_lower = query.lower()

    # ── Detect Hinglish / Hindi ──
    hinglish_keywords = ['kaise', 'kya', 'kyu', 'mera', 'meri', 'hoga', 'hai', 'ho', 'reels',
                         'viral', 'caption', 'hashtag', 'followers', 'likes', 'engagement',
                         'profile', 'bio', 'post', 'story', 'account', 'insta']
    is_hinglish = any(kw in q_lower for kw in hinglish_keywords) and not all(
        c in 'abcdefghijklmnopqrstuvwxyz0123456789 .,!?;:-\'"' for c in q_lower
    )

    # ── Extract intent ──
    intent = _detect_intent(q_lower)

    if intent == 'caption':
        topic = _extract_topic(query)
        return _generate_captions_mock(topic, is_hinglish)

    if intent == 'hashtag':
        topic = _extract_topic(query)
        return _generate_hashtags_mock(topic, is_hinglish)

    if intent == 'bio':
        return _generate_bio_mock(is_hinglish)

    if intent == 'reel':
        return _reel_help(is_hinglish)

    if intent == 'story':
        return _story_help(is_hinglish)

    if intent == 'viral':
        return _viral_tips(is_hinglish)

    if intent == 'followers':
        return _follower_tips(is_hinglish)

    if intent == 'translate':
        return _translate_help(is_hinglish)

    if intent == 'engagement':
        return _engagement_tips(is_hinglish)

    if intent == 'greeting':
        return _greeting()

    if intent == 'idea':
        return _idea_suggestions(is_hinglish)

    # ── General answer ──
    return _general_answer(query, is_hinglish)


# ===== DETECTION =====
def _detect_intent(q):
    patterns = {
        'caption': ['caption', 'captions', 'caption likho', 'caption batao', 'caption do',
                    'write a caption', 'caption for', 'caption idea', 'caption dedo',
                    'caption chahiye', 'caption banaye'],
        'hashtag': ['hashtag', 'hashtags', 'hash tag', 'hash tags', 'tags', '#', 'tags do',
                    'hashtag suggest', 'hashtag batao', 'hashtag likho'],
        'bio': ['bio', 'bios', 'bio suggest', 'bio idea', 'about me', 'bio likho',
                'bio batao', 'bio banaye', 'profile bio', 'bio chahiye'],
        'reel': ['reel', 'reels', 'reel script', 'reel idea', 'reel hook', 'reel topic',
                 'reel banaye', 'reel banao', 'how to make reel', 'reel viral', 'reel kaise'],
        'story': ['story', 'stories', 'story idea', 'story suggest', 'story captions',
                  'story banaye', 'story banao', 'insta story'],
        'viral': ['viral', 'viral kaise', 'viral karo', 'trending', 'go viral',
                  'viral hoga', 'popular kaise'],
        'followers': ['follower', 'followers', 'followers badhaye', 'follower kaise',
                      'more followers', 'follower batao', 'follower kese', 'gain followers'],
        'translate': ['translate', 'translation', 'translate karo', 'anuvad', 'translate kar do',
                      'language', 'hindi me', 'marathi me', 'english me translate'],
        'engagement': ['engagement', 'likes', 'comments', 'more likes', 'more comments',
                       'engagement badhaye', 'like kaise', 'comment kaise'],
        'greeting': ['hi', 'hello', 'hey', 'namaste', 'namaskar', 'good morning',
                     'good evening', 'good afternoon', 'whats up', 'wasup', 'hii', 'heyy'],
        'idea': ['idea', 'ideas', 'content idea', 'post idea', 'suggest', 'suggestion',
                 'kya post karu', 'kya dalo', 'kya share karu', 'content suggest'],
    }
    for intent, keywords in patterns.items():
        for kw in keywords:
            if kw in q:
                return intent
    if q.endswith('?'):
        return 'question'
    return 'general'


def _extract_topic(text):
    """Extract the topic/subject from a user query."""
    # Remove common prefixes
    prefixes = [
        'caption for', 'caption about', 'caption on', 'captions for', 'captions about',
        'hashtag for', 'hashtags for', 'write a caption for', 'write caption for',
        'generate caption for', 'suggest caption for', 'caption likho', 'caption batao',
        'hashtag batao', 'hashtag likho', 'hashtag suggest for',
    ]
    t = text.lower()
    for p in prefixes:
        if t.startswith(p):
            result = text[len(p):].strip().strip('"\'').strip()
            if result:
                return result
    # Try to find main noun phrase
    for kw in ['about', 'for', 'on', 'like', 'such as']:
        if f' {kw} ' in t:
            idx = t.index(f' {kw} ') + len(kw) + 1
            result = text[idx:].strip().strip('"\'').strip()
            if result:
                return result
    return text[:80]


# ===== RESPONSE GENERATORS =====
def _generate_captions_mock(topic, hinglish):
    if not topic or topic in ['caption', 'captions', 'write']:
        topic = 'your post'
    if hinglish:
        return (
            f"Yeh rahe kuch caption ideas '{topic}' ke liye:\n\n"
            f"1. \"{topic.title()} - Living my best life\"\n"
            f"2. \"{topic.title()} vibes only\"\n"
            f"3. \"Good energy, good {topic}, good life\"\n"
            f"4. \"This {topic} moment hits different\"\n"
            f"5. \"{topic.title()} season never ends\"\n\n"
            f"Aur chahiye to batao!"
        )
    return (
        f"Here are 5 caption ideas for '{topic}':\n\n"
        f"1. \"Living my best {topic} life\"\n"
        f"2. \"{topic.title()} vibes only\"\n"
        f"3. \"Good energy, good {topic}, good life\"\n"
        f"4. \"This {topic} moment hits different\"\n"
        f"5. \"{topic.title()} season never ends\"\n\n"
        f"Want more? Just ask!"
    )


def _generate_hashtags_mock(topic, hinglish):
    if not topic or topic in ['hashtag', 'hashtags']:
        topic = 'vibes'
    if hinglish:
        return (
            f"Yeh rahe hashtags '{topic}' ke liye:\n\n"
            f"#{topic} #{topic}vibes #{topic}lover #{topic}gram "
            f"#{topic}life #{topic}daily #{topic}style #{topic}goals "
            f"#{topic}time #{topic}mood #{topic}community #{topic}world "
            f"#{topic}addict #{topic}fun #{topic}photography #{topic}love "
            f"#{topic}beauty #{topic}inspiration #{topic}care #{topic}magic"
        )
    return (
        f"Hashtags for '{topic}':\n\n"
        f"#{topic} #{topic}vibes #{topic}lover #{topic}gram "
        f"#{topic}life #{topic}daily #{topic}style #{topic}goals "
        f"#{topic}time #{topic}mood #{topic}community #{topic}world "
        f"#{topic}addict #{topic}fun #{topic}photography #{topic}love "
        f"#{topic}beauty #{topic}inspiration #{topic}care #{topic}magic"
    )


def _generate_bio_mock(hinglish):
    if hinglish:
        return (
            "Yeh rahe 3 bio options:\n\n"
            "1. Dreamer | Creator | RealityFusion | Living life ek frame at a time\n"
            "2. Busy chasing dreams and sunsets | RealityFusion pe active\n"
            "3. Just a person with a camera and lots of dreams | DM for collab\n\n"
            "Koi specific vibe chahiye to batao!"
        )
    return (
        "Here are 3 bio ideas:\n\n"
        "1. Dreamer | Creator | RealityFusion | Living life one frame at a time\n"
        "2. Chasing sunsets and dreams | Active on RealityFusion\n"
        "3. Just a person with a camera and too many thoughts | DM for collab\n\n"
        "Want a specific vibe? Just ask!"
    )


def _reel_help(hinglish):
    if hinglish:
        return (
            "Reel banane ke liye kuch trending hooks:\n\n"
            '1. "Stop scrolling - yeh dekhna zaroori hai"\n'
            '2. "POV: Tumhe yeh secret mil gaya"\n'
            '3. "3 cheezein jo main jaldi seekh leta"\n'
            '4. "Tum bhi yeh try karo"\n\n'
            "Kya topic pe reel banani hai?"
        )
    return (
        "Trending reel hooks you can use:\n\n"
        '1. "Stop scrolling - this is important"\n'
        '2. "POV: You just unlocked the secret"\n'
        '3. "3 things I wish I knew sooner"\n'
        '4. "Try this and thank me later"\n\n'
        "What topic do you want to make a reel on?"
    )


def _story_help(hinglish):
    if hinglish:
        return (
            "Story ideas:\n\n"
            "1. Behind the scenes dikhao\n"
            "2. Day in your life vlog\n"
            "3. Q&A session - followers se questions pucho\n"
            "4. This or That challenge with stickers\n"
            "5. Mood meter - apna mood share karo\n\n"
            "Aur ideas chahiye?"
        )
    return (
        "Interactive story ideas:\n\n"
        "1. Behind the scenes content\n"
        "2. A day in your life\n"
        "3. Q&A session with followers\n"
        "4. This or That challenge with poll stickers\n"
        "5. Mood meter - share your daily vibe\n\n"
        "Want more specific ideas?"
    )


def _viral_tips(hinglish):
    if hinglish:
        return (
            "Viral hone ke liye tips:\n\n"
            "1. Trending audio use karo - yeh sabse zaroori hai\n"
            "2. Pehle 3 seconds mein attention catch karo\n"
            "3. Hook use karo like 'Stop scrolling' ya 'Wait for it'\n"
            "4. Hashtags lagao - 10-15 relevant tags\n"
            "5. Consistent raho - regularly post karo\n"
            "6. Engagement badhao - comments ka reply do\n\n"
            "Koi specific help chahiye?"
        )
    return (
        "Tips to go viral:\n\n"
        "1. Use trending audio - most important factor\n"
        "2. Hook viewers in the first 3 seconds\n"
        "3. Use hooks like 'Stop scrolling' or 'Watch till the end'\n"
        "4. Use 10-15 relevant hashtags\n"
        "5. Be consistent - post regularly\n"
        "6. Engage back - reply to comments\n\n"
        "Need help with something specific?"
    )


def _follower_tips(hinglish):
    if hinglish:
        return (
            "Followers badhane ke tips:\n\n"
            "1. Quality content do - logo ko value chahiye\n"
            "2. Hashtags strategically use karo\n"
            "3. Dusre accounts ke saath engage karo\n"
            "4. Stories regularly daalo\n"
            "5. Trending topics pe content banao\n"
            "6. Apne followers ke comments ka reply do\n\n"
            "Shuru se start karna hai ya already followers hai?"
        )
    return (
        "Tips to grow followers:\n\n"
        "1. Post quality content that provides value\n"
        "2. Use hashtags strategically\n"
        "3. Engage with other accounts in your niche\n"
        "4. Post stories regularly to stay visible\n"
        "5. Create content around trending topics\n"
        "6. Reply to comments to build community\n\n"
        "Are you just starting out or already have some followers?"
    )


def _translate_help(hinglish):
    if hinglish:
        return (
            "Translate feature:\n\n"
            "Mujhe koi bhi text do aur main language batao - main translate kar dunga.\n"
            "Jaise: 'Translate 'Good morning' to Hindi'\n\n"
            "Available languages: English, Hindi, Marathi, Tamil, Telugu, Punjabi, Korean"
        )
    return (
        "Translation is available for:\n\n"
        "- English, Hindi, Marathi, Tamil, Telugu, Punjabi, Korean\n\n"
        "Just say: 'Translate [text] to [language]' and I'll do it!"
    )


def _engagement_tips(hinglish):
    if hinglish:
        return (
            "Engagement badhane ke tips:\n\n"
            "1. Caption mein question pucho - log comment karenge\n"
            "2. Poll stickers use karo stories mein\n"
            "3. Comments ka reply jaldi do\n"
            "4. Call to action do - 'Double tap if...' ya 'Comment your...'\n"
            "5. Consistent posting schedule rakho\n"
            "6. Trending topics pe timely content banao\n\n"
            "Aur koi help?"
        )
    return (
        "Engagement tips:\n\n"
        "1. Ask questions in captions to spark comments\n"
        "2. Use poll stickers in stories\n"
        "3. Reply to comments quickly\n"
        "4. Add CTAs like 'Double tap if...' or 'Comment your...'\n"
        "5. Maintain a consistent posting schedule\n"
        "6. Create timely content around trending topics\n\n"
        "Anything else?"
    )


def _idea_suggestions(hinglish):
    if hinglish:
        return (
            "Content ideas:\n\n"
            "1. Behind the scenes - apni routine dikhao\n"
            "2. Before and After - transformation dikhao\n"
            "3. Day in the life - poora din vlog karo\n"
            "4. Tutorial - kuch sikhao apne followers ko\n"
            "5. Q&A - followers ke questions answer karo\n"
            "6. Challenges - trending challenges join karo\n\n"
            "Kaunsa type chahiye? Batao main specific ideas dunga!"
        )
    return (
        "Content ideas that work well:\n\n"
        "1. Behind the scenes of your routine\n"
        "2. Before and after transformations\n"
        "3. Day in the life vlogs\n"
        "4. Tutorials - teach something to your audience\n"
        "5. Q&A sessions answering follower questions\n"
        "6. Join trending challenges\n\n"
        "What type of content do you create? I can give specific ideas!"
    )


def _greeting():
    return (
        "Hey! I'm RealityAI. I can help you with:\n"
        "- Captions & Hashtags\n"
        "- Reel scripts & hooks\n"
        "- Story ideas\n"
        "- Profile bio suggestions\n"
        "- Growth tips (followers, engagement, viral)\n"
        "- Translation\n\n"
        "What do you need help with today?"
    )


def _general_answer(query, hinglish):
    """Fallback that actually references the user's question."""
    q = query[:100]
    if hinglish:
        return (
            f"Main samajh gaya! Aapne pucha: '{q}'\n\n"
            f"Yeh topic hai social media growth ka. Kya aap specifically yeh janna chahte hain:\n"
            f"- Caption ya hashtag suggestions?\n"
            f"- Reels ya stories ke tips?\n"
            f"- Followers badhane ke tareeke?\n"
            f"- Content ideas?\n\n"
            f"Mujhe batao, main help karunga!"
        )
    return (
        f"I understand you're asking about: '{q}'\n\n"
        f"Here's what I can help you with:\n"
        f"- Caption & hashtag generation\n"
        f"- Reel scripts & hooks\n"
        f"- Story ideas\n"
        f"- Profile bio suggestions\n"
        f"- Growth tips (followers, engagement, viral strategies)\n"
        f"- Translation & content enhancement\n\n"
        f"What specific help do you need? I'm here for you!"
    )
