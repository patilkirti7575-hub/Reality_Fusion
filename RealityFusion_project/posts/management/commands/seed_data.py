from io import BytesIO
import os
import tempfile
import numpy as np
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from RealityFusion_project.posts.models import Post, Comment, Story, StoryView, Reel, ReelComment, StoryMusic, CameraFilter, ReelAudio
from RealityFusion_project.messaging.models import Message
from RealityFusion_project.users.models import CustomUser, Profile, Follow
from PIL import Image, ImageDraw, ImageFont
import random


def generate_placeholder_image(text, width=640, height=640, bg_color=None):
    if bg_color is None:
        bg_color = (random.randint(20, 80), random.randint(20, 80), random.randint(40, 100))
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (width - tw) / 2
    y = (height - th) / 2
    draw.text((x, y), text, fill=(200, 200, 200), font=font)
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    return ContentFile(buffer.getvalue())


def generate_audio(sample_rate=44100, duration=3, theme='default'):
    import struct, math
    n_samples = int(sample_rate * duration)

    theme_notes = {
        'sunset': [262, 330, 392, 523],   # C4 E4 G4 C5
        'nature': [294, 370, 440, 587],   # D4 F#4 A4 D5
        'city': [130, 165, 196, 262],     # C3 E3 G3 C4
        'art': [330, 392, 440, 523],      # E4 G4 A4 C5
        'food': [262, 294, 330, 349],     # C4 D4 E4 F4
        'travel': [220, 262, 330, 392],   # A3 C4 E4 G4
        'fitness': [262, 262, 330, 330],  # C4 C4 E4 E4
        'music': [330, 392, 523, 659],    # E4 G4 C5 E5
        'fashion': [247, 294, 370, 440],  # B3 D4 F#4 A4
        'default': [262, 330, 392, 523],
    }
    notes = theme_notes.get(theme, theme_notes['default'])

    frames = []
    beat_len = int(sample_rate * 0.5)  # 0.5 sec per beat
    beats = int(n_samples / beat_len)

    for b in range(beats):
        note = notes[b % len(notes)]
        for s in range(beat_len):
            t = s / sample_rate
            # Main tone
            val = math.sin(2 * math.pi * note * t)
            # Add harmonics for richness
            val += 0.5 * math.sin(2 * math.pi * note * 2 * t)
            val += 0.25 * math.sin(2 * math.pi * note * 3 * t)
            # Percussive attack at start of each beat
            attack = max(0, 1 - s / (sample_rate * 0.02))
            val *= 0.3 + 0.7 * attack
            # Volume envelope
            val *= 0.15
            # Clamp
            val = max(-1, min(1, val))
            frames.append(val)

    # Pad/trim to exact length
    while len(frames) < n_samples:
        frames.append(0.0)
    frames = frames[:n_samples]

    # Convert to 16-bit PCM
    import array
    pcm = array.array('h', (int(f * 32767) for f in frames))
    return pcm, sample_rate


def generate_placeholder_video(text, theme='default', duration=3, fps=15):
    width, height = 480, 854
    total_frames = duration * fps

    theme_colors = {
        'sunset': [(255, 100, 50), (200, 60, 100), (255, 160, 60)],
        'nature': [(30, 120, 50), (60, 180, 80), (20, 80, 40)],
        'city': [(60, 60, 80), (100, 100, 140), (40, 40, 60)],
        'art': [(140, 60, 120), (200, 100, 160), (100, 40, 100)],
        'food': [(200, 100, 40), (240, 180, 80), (160, 80, 30)],
        'travel': [(40, 120, 180), (80, 180, 220), (30, 80, 140)],
        'fitness': [(180, 40, 40), (220, 80, 60), (140, 30, 30)],
        'music': [(60, 40, 120), (100, 60, 180), (40, 20, 100)],
        'fashion': [(180, 60, 140), (220, 100, 180), (140, 40, 100)],
        'default': [(80, 80, 120), (120, 120, 180), (60, 60, 100)],
    }
    palette = theme_colors.get(theme, theme_colors['default'])

    import cv2
    import subprocess
    import wave
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    tmp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    tmp_video_path = tmp_video.name
    tmp_video.close()
    tmp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp_audio_path = tmp_audio.name
    tmp_audio.close()
    tmp_output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    tmp_output_path = tmp_output.name
    tmp_output.close()

    try:
        # ── Generate video frames ──
        out = cv2.VideoWriter(tmp_video_path, fourcc, fps, (width, height))
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 1.2
        thickness = 2

        for f in range(total_frames):
            progress = f / total_frames
            idx = int(progress * (len(palette) - 1))
            next_idx = min(idx + 1, len(palette) - 1)
            t = (progress * (len(palette) - 1)) - idx
            c1, c2 = palette[idx], palette[next_idx]
            bg = (
                int(c1[0] + (c2[0] - c1[0]) * t),
                int(c1[1] + (c2[1] - c1[1]) * t),
                int(c1[2] + (c2[2] - c1[2]) * t),
            )
            frame = np.full((height, width, 3), bg, dtype=np.uint8)
            bar_x = int(width * (0.1 + 0.8 * (0.5 + 0.5 * np.sin(progress * 4 * np.pi))))
            cv2.rectangle(frame, (bar_x - 4, 0), (bar_x + 4, height), (255, 255, 255, 60), -1)
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            tx = (width - text_size[0]) // 2
            ty = (height + text_size[1]) // 2
            cv2.putText(frame, text, (tx + 2, ty + 2), font, font_scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
            cv2.putText(frame, text, (tx, ty), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            wm = 'RealityFusion'
            wm_size = cv2.getTextSize(wm, font, 0.6, 1)[0]
            cv2.putText(frame, wm, (width - wm_size[0] - 16, height - 16), font, 0.6, (255, 255, 255, 100), 1, cv2.LINE_AA)
            out.write(frame)
        out.release()

        # ── Generate audio ──
        pcm, sample_rate = generate_audio(44100, duration, theme)
        with wave.open(tmp_audio_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

        # ── Mux video + audio with ffmpeg ──
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
        subprocess.run([
            ffmpeg, '-y',
            '-i', tmp_video_path,
            '-i', tmp_audio_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-c:a', 'aac',
            '-b:a', '96k',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            tmp_output_path
        ], capture_output=True, timeout=30)

        with open(tmp_output_path, 'rb') as f:
            data = f.read()
        return ContentFile(data)
    finally:
        for p in [tmp_video_path, tmp_audio_path, tmp_output_path]:
            if os.path.exists(p):
                os.unlink(p)


USERS_DATA = [
    {'email': 'alice@example.com', 'username': 'alice_wonder', 'password': 'password123', 'bio': 'Digital artist & photographer 📸'},
    {'email': 'bob@example.com', 'username': 'bob_nature', 'password': 'password123', 'bio': 'Nature lover | Landscape photography 🌲'},
    {'email': 'charlie@example.com', 'username': 'charlie_codes', 'password': 'password123', 'bio': 'Software dev by day, chef by night 🍝'},
    {'email': 'diana@example.com', 'username': 'diana_views', 'password': 'password123', 'bio': 'Travel blogger | 20 countries and counting ✈️'},
    {'email': 'eva@example.com', 'username': 'eva_art', 'password': 'password123', 'bio': 'Digital illustrations & concept art 🎨'},
    {'email': 'frank@example.com', 'username': 'frank_fitness', 'password': 'password123', 'bio': 'Fitness coach | Healthy living 💪'},
    {'email': 'grace@example.com', 'username': 'grace_music', 'password': 'password123', 'bio': 'Musician | Singer-songwriter 🎵'},
    {'email': 'henry@example.com', 'username': 'henry_fashion', 'password': 'password123', 'bio': 'Fashion designer | Style icon 👔'},
]

REELS_DATA = [
    {'email': 'alice@example.com', 'caption': 'Golden hour vibes', 'theme': 'sunset'},
    {'email': 'bob@example.com', 'caption': 'Deep forest meditation', 'theme': 'nature'},
    {'email': 'charlie@example.com', 'caption': 'Pasta from scratch!', 'theme': 'food'},
    {'email': 'diana@example.com', 'caption': 'Tokyo nights never sleep', 'theme': 'city'},
    {'email': 'eva@example.com', 'caption': 'Speed sketch timelapse', 'theme': 'art'},
    {'email': 'frank@example.com', 'caption': 'Morning routine grind', 'theme': 'fitness'},
    {'email': 'grace@example.com', 'caption': 'New song preview!', 'theme': 'music'},
    {'email': 'henry@example.com', 'caption': 'Street style fit check', 'theme': 'fashion'},
    {'email': 'alice@example.com', 'caption': 'Beach painting process', 'theme': 'art'},
    {'email': 'bob@example.com', 'caption': 'Mountain summit view', 'theme': 'nature'},
    {'email': 'diana@example.com', 'caption': 'Bali sunrise', 'theme': 'sunset'},
    {'email': 'charlie@example.com', 'caption': 'Best ramen in town', 'theme': 'food'},
    {'email': 'eva@example.com', 'caption': 'Character design reel', 'theme': 'art'},
    {'email': 'frank@example.com', 'caption': 'HIIT workout challenge', 'theme': 'fitness'},
    {'email': 'grace@example.com', 'caption': 'Guitar cover acoustic', 'theme': 'music'},
    {'email': 'henry@example.com', 'caption': 'Summer collection sneak peek', 'theme': 'fashion'},
    {'email': 'alice@example.com', 'caption': 'Neon light photography', 'theme': 'city'},
    {'email': 'bob@example.com', 'caption': 'Wildlife close-up', 'theme': 'nature'},
    {'email': 'diana@example.com', 'caption': 'Street food tour', 'theme': 'food'},
    {'email': 'grace@example.com', 'caption': 'Studio session behind the scenes', 'theme': 'music'},
    {'email': 'frank@example.com', 'caption': 'Protein smoothie recipe', 'theme': 'fitness'},
    {'email': 'henry@example.com', 'caption': 'Vintage style lookbook', 'theme': 'fashion'},
    {'email': 'eva@example.com', 'caption': 'Procreate speed paint', 'theme': 'art'},
    {'email': 'charlie@example.com', 'caption': 'Coding setup tour', 'theme': 'city'},
    # Motivational reels
    {'email': 'frank@example.com', 'caption': 'Never give up on your dreams', 'theme': 'fitness'},
    {'email': 'alice@example.com', 'caption': 'Trust the process', 'theme': 'sunset'},
    {'email': 'eva@example.com', 'caption': 'Create every single day', 'theme': 'art'},
    {'email': 'frank@example.com', 'caption': 'Grind now shine later', 'theme': 'fitness'},
    {'email': 'grace@example.com', 'caption': 'Music heals the soul', 'theme': 'music'},
    {'email': 'bob@example.com', 'caption': 'Nature is the best therapy', 'theme': 'nature'},
    {'email': 'diana@example.com', 'caption': 'Travel more worry less', 'theme': 'travel'},
    {'email': 'henry@example.com', 'caption': 'Dress like you are already famous', 'theme': 'fashion'},
    {'email': 'charlie@example.com', 'caption': 'Code and coffee all day', 'theme': 'city'},
    {'email': 'alice@example.com', 'caption': 'Sunset chaser forever', 'theme': 'sunset'},
    # Funny reels
    {'email': 'charlie@example.com', 'caption': 'When the code finally works', 'theme': 'city'},
    {'email': 'frank@example.com', 'caption': 'Me after leg day', 'theme': 'fitness'},
    {'email': 'eva@example.com', 'caption': 'My cat walked across my keyboard', 'theme': 'art'},
    {'email': 'henry@example.com', 'caption': 'Trying to look cool for the gram', 'theme': 'fashion'},
    {'email': 'diana@example.com', 'caption': 'Lost in translation adventures', 'theme': 'travel'},
    {'email': 'bob@example.com', 'caption': 'When the hike is harder than expected', 'theme': 'nature'},
    {'email': 'grace@example.com', 'caption': 'Singing in the shower hits different', 'theme': 'music'},
    {'email': 'alice@example.com', 'caption': 'POV you forgot to save the file', 'theme': 'art'},
]

REEL_COMMENTS_DATA = [
    '🔥🔥🔥', 'This is amazing!', 'Love the vibes!', 'So creative!',
    'How did you do this?', 'Goals!', 'Incredible work!',
    'I need to try this!', 'Beautiful!', 'Youre so talented!',
    'Wow! Just wow!', 'Keep it up!', 'My favorite reel!',
    'This deserves more views!', 'Perfection!',
    'LMAO 🤣', 'I cant breathe 😂', 'Me everyday fr',
    'This is too relatable', 'Stop calling me out 😭',
    'Need this energy today', 'Lets goooo 🔥',
    'Motivation unlocked', 'Needed to hear this',
    'Saved for later 💯', 'This is gold',
]


class Command(BaseCommand):
    help = 'Seed the database with example users, posts, comments, messages, and reels'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # ── Users ──
        created_users = {}
        for user_data in USERS_DATA:
            user, created = CustomUser.objects.get_or_create(
                email=user_data['email'],
                defaults={'username': user_data['username']}
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                profile = Profile.objects.get(user=user)
                profile.bio = user_data['bio']
                avatar_colors = [(180, 60, 60), (60, 120, 180), (60, 180, 90), (180, 160, 50), (140, 70, 180), (200, 80, 40), (80, 60, 160), (180, 100, 60)]
                c = avatar_colors[len(created_users) % len(avatar_colors)]
                avatar = generate_placeholder_image(user.username[0].upper() if user.username else '?', 200, 200, c)
                profile.profile_pic.save(f'avatar_{user.id}.jpg', avatar, save=True)
                self.stdout.write(f'  Created user: {user.email}')
            else:
                self.stdout.write(f'  User exists: {user.email}')
            created_users[user_data['email']] = user

        user_list = list(created_users.values())
        for i, u1 in enumerate(user_list):
            for u2 in user_list[i + 1:]:
                Follow.objects.get_or_create(from_user=u1, to_user=u2)
                Follow.objects.get_or_create(from_user=u2, to_user=u1)

        # ── Posts ──
        POSTS_DATA = [
            {'email': 'alice@example.com', 'content': 'Golden hour magic at the beach today!', 'img_text': 'Sunset Beach'},
            {'email': 'bob@example.com', 'content': 'Morning hike through the misty forest trails', 'img_text': 'Forest Trail'},
            {'email': 'charlie@example.com', 'content': 'Homemade pasta from scratch! Recipe in bio', 'img_text': 'Fresh Pasta'},
            {'email': 'diana@example.com', 'content': 'Streets of Tokyo never sleep', 'img_text': 'Tokyo Nights'},
            {'email': 'eva@example.com', 'content': 'New character design for my upcoming graphic novel', 'img_text': 'Character Art'},
        ]
        COMMENTS_DATA = [
            {'post_index': 0, 'email': 'bob@example.com', 'content': 'Stunning shot!'},
            {'post_index': 0, 'email': 'charlie@example.com', 'content': 'Where is this beach?'},
            {'post_index': 1, 'email': 'alice@example.com', 'content': 'So peaceful! Love it'},
            {'post_index': 1, 'email': 'diana@example.com', 'content': 'Which trail is this?'},
            {'post_index': 2, 'email': 'eva@example.com', 'content': 'Looks delicious!'},
            {'post_index': 2, 'email': 'alice@example.com', 'content': 'Can I get the recipe?'},
            {'post_index': 3, 'email': 'eva@example.com', 'content': 'I want to visit Japan so bad!'},
            {'post_index': 4, 'email': 'bob@example.com', 'content': 'Amazing talent!'},
            {'post_index': 4, 'email': 'charlie@example.com', 'content': 'Love the style'},
        ]

        created_posts = []
        for i, post_data in enumerate(POSTS_DATA):
            user = created_users[post_data['email']]
            post, created = Post.objects.get_or_create(
                user=user,
                content=post_data['content'],
                defaults={'image': None}
            )
            if created:
                img_file = generate_placeholder_image(
                    post_data['img_text'],
                    width=640,
                    height=random.choice([640, 800, 480]),
                    bg_color=(random.randint(30, 90), random.randint(30, 90), random.randint(40, 110))
                )
                post.image.save(f'seed_post_{i}.jpg', img_file, save=True)
                self.stdout.write(f'  Created post: {post.content[:40]}...')
            else:
                self.stdout.write(f'  Post exists: {post.content[:40]}...')
            created_posts.append(post)

        for comment_data in COMMENTS_DATA:
            post = created_posts[comment_data['post_index']]
            user = created_users[comment_data['email']]
            Comment.objects.get_or_create(
                post=post,
                user=user,
                content=comment_data['content']
            )
        self.stdout.write(f'  Created {len(COMMENTS_DATA)} comments')

        # ── Stories ──
        story_creators = ['alice@example.com', 'bob@example.com', 'diana@example.com']
        story_texts = ['Good morning!', 'Nature vibes', 'Travel mode on', 'Coffee time', 'Sunset chaser', 'Weekend mood']
        for i, email in enumerate(story_creators):
            user = created_users[email]
            for j in range(2):
                story = Story(user=user, caption=random.choice(story_texts))
                img_file = generate_placeholder_image(
                    f"{user.username}'s story",
                    width=400,
                    height=700,
                    bg_color=(random.randint(40, 100), random.randint(30, 90), random.randint(50, 110))
                )
                story.image.save(f'seed_story_{i}_{j}.jpg', img_file, save=True)
                self.stdout.write(f'  Created story by {user.email}')
        self.stdout.write('  Created example stories')

        # ── Messages ──
        CONVERSATIONS = [
            {'from': 'alice@example.com', 'to': 'bob@example.com',
             'messages': [
                 'Hey Bob! Love your nature photos!',
                 'Thanks Alice! Your beach shots are amazing too!',
                 'We should do a photoshoot together sometime!',
                 'That would be awesome!',
             ]},
            {'from': 'charlie@example.com', 'to': 'diana@example.com',
             'messages': [
                 'Hey Diana! How was your trip to Tokyo?',
                 'It was incredible! You have to go!',
                 'Any restaurant recommendations?',
                 'Yes! Ramen at Ichiran is a must!',
             ]},
            {'from': 'eva@example.com', 'to': 'alice@example.com',
             'messages': [
                 'Love your art style Alice!',
                 'Thank you Eva! Yours is amazing too!',
                 'Would you be interested in collaborating?',
                 'Absolutely! Let me know your idea!',
             ]},
            {'from': 'bob@example.com', 'to': 'diana@example.com',
             'messages': [
                 'Your travel photos are goals!',
                 'Thanks Bob! Your nature photography is stunning!',
                 'Maybe you can join my next trip?',
                 'Id love that! count me in!',
             ]},
            {'from': 'charlie@example.com', 'to': 'eva@example.com',
             'messages': [
                 'Your character designs are incredible!',
                 'Thanks Charlie! Your coding projects are impressive!',
                 'We should create a game together sometime!',
                 'That would be a dream collaboration!',
             ]},
        ]
        for conv in CONVERSATIONS:
            users_conv = [created_users[conv['from']], created_users[conv['to']]]
            for i, msg_content in enumerate(conv['messages']):
                sender = users_conv[i % 2]
                receiver = users_conv[(i + 1) % 2]
                Message.objects.get_or_create(
                    sender=sender,
                    receiver=receiver,
                    content=msg_content,
                )
        self.stdout.write('  Created conversations with messages')

        # ── Story Music ──
        self.stdout.write('  Seeding story music...')
        MUSIC_TRACKS = [
            {'title': 'Sunset Dreams', 'artist': 'Reality Beats', 'language': 'English', 'duration': 30,
             'theme': 'sunset', 'lyrics': 'Walking through the sunset dreams\nEvery moment feels so right\nGolden light upon my skin\nDancing through the endless night'},
            {'title': 'Mountain High', 'artist': 'Nature Sounds', 'language': 'English', 'duration': 30,
             'theme': 'nature', 'lyrics': 'Climbing mountains touching sky\nFree as birds we learn to fly\nNature calls us deep inside\nIn her arms we confide'},
            {'title': 'City Lights', 'artist': 'Urban Vibes', 'language': 'English', 'duration': 30,
             'theme': 'city', 'lyrics': 'Neon lights they guide my way\nThrough the city night and day\nBright lights big city dreams\nNothing is what it seems'},
            {'title': 'Creative Flow', 'artist': 'Art Zone', 'language': 'English', 'duration': 30,
             'theme': 'art', 'lyrics': 'Colors dancing in my mind\nCreating art of every kind\nBrush strokes tell a story true\nEvery shade of me and you'},
            {'title': 'Tasty Vibes', 'artist': 'Chef Beats', 'language': 'English', 'duration': 30,
             'theme': 'food', 'lyrics': 'Sizzling sounds and tasty treats\nEvery flavor that we meet\nCooking up a storm tonight\nEverything will be alright'},
            {'title': 'Workout Mode', 'artist': 'Fitness Flow', 'language': 'English', 'duration': 30,
             'theme': 'fitness', 'lyrics': 'Push it harder reach the sky\nNever stop and never cry\nStronger now with every beat\nFeel the fire burning heat'},
            {'title': 'Melody of Love', 'artist': 'Grace Notes', 'language': 'English', 'duration': 30,
             'theme': 'music', 'lyrics': 'Music flowing like a stream\nLiving out a beautiful dream\nEvery note a memory\nPlaying our sweet symphony'},
            {'title': 'Style Statement', 'artist': 'Fashion Beats', 'language': 'English', 'duration': 30,
             'theme': 'fashion', 'lyrics': 'Walk the runway own the night\nDressed in dreams looking bright\nStyle is more than what you wear\nIts the confidence you share'},
            {'title': 'Dil Ki Baat', 'artist': 'Riya Sharma', 'language': 'Hindi', 'duration': 30,
             'theme': 'sunset', 'lyrics': 'Dil ki baat hai yeh\nPyar ki raat hai yeh\nTumse milke humne\nKhwabon ki baat ki yeh'},
            {'title': 'Mann Bawara', 'artist': 'Aditya Kumar', 'language': 'Hindi', 'duration': 30,
             'theme': 'nature', 'lyrics': 'Mann bawara hai\nTanha saara hai\nTujhse milne ko\nHar ghadi pyara hai'},
            {'title': 'Punjabi Swag', 'artist': 'Gurpreet Singh', 'language': 'Punjabi', 'duration': 30,
             'theme': 'city', 'lyrics': 'Punjabi swag hai\nDuniya jag hai\nNachdi phire aashiq\nPyaar di ag hai'},
            {'title': 'Kannazuki', 'artist': 'Yuki Tanaka', 'language': 'Korean', 'duration': 30,
             'theme': 'city', 'lyrics': 'Kannazuki no yoru ni\nKimi wo omoidasu\nHoshizora no shita de\nFutari de aimashou'},
            {'title': 'Azhagiya Kanneer', 'artist': 'Priya Rajan', 'language': 'Tamil', 'duration': 30,
             'theme': 'sunset', 'lyrics': 'Azhagiya kanneer nee\nEn uyiril theeyai nee\nKadhal vaanam pookkalai\nEn nenjil nee'},
            {'title': 'Manmadhuda', 'artist': 'Arjun Reddy', 'language': 'Telugu', 'duration': 30,
             'theme': 'fitness', 'lyrics': 'Manmadhuda nee maaya\nChusthunte naa prema\nNee navvu nee matalu\nNaa gundelo geethalu'},
            {'title': 'Majha Navra', 'artist': 'Sneha Joshi', 'language': 'Marathi', 'duration': 30,
             'theme': 'music', 'lyrics': 'Majha navra tu\nTuzya sangach mi\nPrem karate tula\nJeevan bhar mi'},
        ]

        for music_data in MUSIC_TRACKS:
            track, created = StoryMusic.objects.get_or_create(
                title=music_data['title'],
                artist=music_data['artist'],
                defaults={
                    'language': music_data['language'],
                    'duration': music_data['duration'],
                    'lyrics': music_data['lyrics'],
                    'audio_file': None,  # Will be generated
                }
            )
            if created and not track.audio_file:
                pcm, sr = generate_audio(44100, 5, music_data['theme'])
                import wave, tempfile
                tmp_path = os.path.join(tempfile.gettempdir(), f'music_{track.id}.wav')
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(pcm.tobytes())
                with open(tmp_path, 'rb') as f:
                    track.audio_file.save(f'music_{track.id}.wav', ContentFile(f.read()), save=True)
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                self.stdout.write(f'  Created music: {track.title} - {track.artist} ({track.language})')
            else:
                self.stdout.write(f'  Music exists: {track.title}')

        # ── Camera Filters ──
        self.stdout.write('  Seeding camera filters...')
        FILTERS_DATA = [
            {'name': 'Normal', 'css_filter': '', 'order': 0},
            {'name': 'Vintage', 'css_filter': 'sepia(80%) contrast(90%) saturate(70%)', 'order': 1},
            {'name': 'Noir', 'css_filter': 'grayscale(100%) contrast(120%)', 'order': 2},
            {'name': 'Cinematic', 'css_filter': 'contrast(110%) brightness(95%) saturate(130%)', 'order': 3},
            {'name': 'Warm', 'css_filter': 'sepia(30%) brightness(105%) saturate(120%)', 'order': 4},
            {'name': 'Cool', 'css_filter': 'hue-rotate(180deg) saturate(80%) brightness(105%)', 'order': 5},
            {'name': 'Drama', 'css_filter': 'contrast(150%) brightness(90%) saturate(110%)', 'order': 6},
            {'name': 'Fade', 'css_filter': 'opacity(85%) contrast(85%) saturate(80%)', 'order': 7},
            {'name': 'Neon', 'css_filter': 'hue-rotate(60deg) saturate(200%) brightness(110%)', 'order': 8},
            {'name': 'B&W', 'css_filter': 'grayscale(100%) brightness(105%)', 'order': 9},
            {'name': 'Sunset', 'css_filter': 'sepia(50%) saturate(150%) brightness(105%) hue-rotate(-10deg)', 'order': 10},
            {'name': 'Pastel', 'css_filter': 'saturate(60%) brightness(110%) contrast(90%)', 'order': 11},
            {'name': 'Vibrant', 'css_filter': 'saturate(200%) contrast(110%)', 'order': 12},
            {'name': 'Glow', 'css_filter': 'brightness(110%) saturate(150%) drop-shadow(0 0 8px rgba(255,255,255,0.3))', 'order': 13},
        ]

        for filter_data in FILTERS_DATA:
            CameraFilter.objects.get_or_create(
                name=filter_data['name'],
                defaults={
                    'css_filter': filter_data['css_filter'],
                    'order': filter_data['order'],
                    'is_active': True,
                }
            )
        self.stdout.write(f'  Created {len(FILTERS_DATA)} camera filters')

        # ── Also seed ReelAudio tracks ──
        self.stdout.write('  Seeding reel audio...')
        for music_data in MUSIC_TRACKS[:8]:  # Reuse first 8 tracks
            track, created = ReelAudio.objects.get_or_create(
                title=music_data['title'],
                artist=music_data['artist'],
                defaults={'duration': music_data['duration']}
            )
            if created and not track.audio_file:
                pcm, sr = generate_audio(44100, 5, music_data['theme'])
                import wave, tempfile
                tmp_path = os.path.join(tempfile.gettempdir(), f'reel_audio_{track.id}.wav')
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(pcm.tobytes())
                with open(tmp_path, 'rb') as f:
                    track.audio_file.save(f'reel_audio_{track.id}.wav', ContentFile(f.read()), save=True)
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                self.stdout.write(f'  Created reel audio: {track.title}')
            else:
                self.stdout.write(f'  Reel audio exists: {track.title}')

        # ── Demo user ──
        sample_user, _ = CustomUser.objects.get_or_create(
            email='demo@realityfusion.com',
            defaults={'username': 'demo_user'}
        )
        if _:
            sample_user.set_password('demo123')
            sample_user.save()
            Profile.objects.filter(user=sample_user).update(bio='Demo user exploring RealityFusion!')
            self.stdout.write(f'  Created demo user: demo@realityfusion.com / demo123')

        for u in user_list:
            Follow.objects.get_or_create(from_user=sample_user, to_user=u)

        # ════════════════════════════════════════════
        #  REELS
        # ════════════════════════════════════════════
        self.stdout.write('  Seeding reels...')

        reels_dir = os.path.join(settings.MEDIA_ROOT, 'reels')
        os.makedirs(reels_dir, exist_ok=True)

        existing_reel_count = Reel.objects.count()
        if existing_reel_count >= len(REELS_DATA):
            self.stdout.write(f'  {existing_reel_count} reels already exist, skipping reel creation')
        else:
            for idx, reel_data in enumerate(REELS_DATA):
                user = created_users[reel_data['email']]
                caption = reel_data['caption']
                theme = reel_data.get('theme', 'default')

                reel, created = Reel.objects.get_or_create(
                    user=user,
                    caption=caption,
                    defaults={'views': 0}
                )
                if created:
                    safe_cap = caption.encode('ascii', 'replace').decode('ascii')
                    self.stdout.write(f'    Generating video {idx+1}/{len(REELS_DATA)}: "{safe_cap[:30]}"...')
                    video_file = generate_placeholder_video(
                        caption.split(' ')[0] + ' #reels',
                        theme=theme,
                        duration=3,
                        fps=15
                    )
                    reel.video.save(f'seed_reel_{idx}.mp4', video_file, save=True)
                    reel.views = random.randint(500, 50000)
                    reel.save(update_fields=['views'])

                    # Random likes (2-7 users like each reel)
                    likers = random.sample(user_list, min(random.randint(2, len(user_list)), len(user_list)))
                    reel.likes.add(*likers)

                    # Random comments (1-4 per reel)
                    num_comments = random.randint(1, 4)
                    for _ in range(num_comments):
                        commenter = random.choice(user_list)
                        comment_text = random.choice(REEL_COMMENTS_DATA)
                        ReelComment.objects.get_or_create(
                            reel=reel,
                            user=commenter,
                            content=comment_text,
                        )

                    safe_user = user.username.encode('ascii', 'replace').decode('ascii') if user.username else '?'
                    self.stdout.write(f'      Created reel by {safe_user} | {reel.views} views | {reel.likes.count()} likes | {reel.comment_count} comments')
                else:
                    safe_cap = caption.encode('ascii', 'replace').decode('ascii')
                    # Check if existing reel has a valid video file on disk
                    if not reel.video_exists:
                        self.stdout.write(f'    Reel exists but missing video file: regenerating for "{safe_cap[:30]}"...')
                        video_file = generate_placeholder_video(
                            caption.split(' ')[0] + ' #reels',
                            theme=theme,
                            duration=3,
                            fps=15
                        )
                        reel.video.save(f'seed_reel_{idx}.mp4', video_file, save=True)
                        self.stdout.write(f'      Regenerated video for reel by {user.email}')
                    else:
                        self.stdout.write(f'    Reel exists: "{safe_cap[:30]}"')

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write('Users:')
        for u in USERS_DATA:
            self.stdout.write(f'  {u["email"]} / {u["password"]}')
        self.stdout.write(f'  demo@realityfusion.com / demo123')
