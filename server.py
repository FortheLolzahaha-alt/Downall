import os
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API Backend is up and running!"

def fetch_youtube_api(video_url):
    """Attempts to fetch YouTube stream via multi-instance external APIs."""
    instances = [
        "https://api.cobalt.tools/",
        "https://cobalt-api.kwiatek.xyz/",
        "https://api.co.wuk.sh/"
    ]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    payload = {
        "url": video_url,
        "videoQuality": "720"
    }

    for instance in instances:
        try:
            res = requests.post(instance, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get("url"):
                    return data["url"]
                elif data.get("picker") and len(data["picker"]) > 0:
                    return data["picker"][0]["url"]
        except Exception as e:
            print(f"Error fetching from {instance}: {e}")
            continue

    return None

@app.route('/download', methods=['GET'])
def extract_video():
    video_url = request.args.get('url')

    if not video_url:
        return jsonify({'message': 'No URL provided'}), 400

    # 1. Attempt YouTube API Bypass
    if 'youtube.com' in video_url or 'youtu.be' in video_url:
        yt_stream_url = fetch_youtube_api(video_url)
        if yt_stream_url:
            return jsonify({
                'download_url': yt_stream_url,
                'original_url': video_url
            })

    # 2. Standard yt-dlp Extraction (with format fallback)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # IMPORTANT: force a single combined (progressive) stream.
        # Without this, yt-dlp's default selector tries to grab a
        # separate best-video + best-audio pair meant for ffmpeg
        # merging, which fails with "Requested format is not
        # available" whenever the chosen client only exposes
        # DASH/adaptive-only streams. Since this endpoint needs to
        # hand back ONE direct URL, we must restrict to formats that
        # already contain both audio and video.
        'format': 'best[ext=mp4]/best',
        'extractor_args': {
            'youtube': {
                # Try clients in order of current reliability. tv_embedded
                # and tv have had better luck avoiding YouTube's bot
                # checks recently; the rest are fallbacks.
                'player_client': ['tv_embedded', 'tv', 'web_creator', 'android', 'ios', 'mweb']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            media_url = info.get('url')

            # Find combined (video + audio) progressive stream
            if not media_url and info.get('formats'):
                progressive_formats = [
                    f for f in info['formats']
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none'
                ]
                if progressive_formats:
                    media_url = progressive_formats[-1]['url']
                else:
                    for fmt in reversed(info['formats']):
                        if fmt.get('url') and fmt.get('url').startswith('http'):
                            media_url = fmt['url']
                            break

            if media_url:
                return jsonify({
                    'download_url': media_url,
                    'original_url': video_url
                })

            return jsonify({'message': 'Could not extract direct media URL.'}), 400

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/proxy', methods=['GET'])
def proxy_stream():
    media_url = request.args.get('media_url')
    original_url = request.args.get('original_url', '')

    if not media_url:
        return "Missing media URL", 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': original_url
    }

    try:
        req = requests.get(media_url, headers=headers, stream=True)
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': 'attachment; filename="video.mp4"'
            }
        )
    except Exception as e:
        return f"Proxy stream error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
