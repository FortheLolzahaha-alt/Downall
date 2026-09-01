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

@app.route('/download', methods=['GET'])
def extract_video():
    video_url = request.args.get('url')

    if not video_url:
        return jsonify({'message': 'No URL provided'}), 400

    # Redirect YouTube links directly to external downloader
    if 'youtube.com' in video_url or 'youtu.be' in video_url:
        return jsonify({
            'download_url': 'https://app.ytdown.to/en38/',
            'original_url': video_url
        })

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best', 
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            media_url = info.get('url')
            # Extract exact HTTP headers yt-dlp used to authenticate with CDN
            extracted_headers = info.get('http_headers', {})

            if media_url:
                return jsonify({
                    'download_url': media_url,
                    'original_url': video_url,
                    'headers': extracted_headers
                })

            return jsonify({'message': 'Could not extract direct media URL.'}), 400

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/proxy', methods=['GET', 'POST'])
def proxy_stream():
    if request.method == 'POST':
        data = request.get_json() or {}
        media_url = data.get('media_url')
        custom_headers = data.get('headers', {})
    else:
        media_url = request.args.get('media_url')
        custom_headers = {}

    if not media_url:
        return "Missing media URL", 400

    # Fallback default headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.tiktok.com/' if 'tiktok.com' in media_url else request.args.get('original_url', '')
    }

    # Merge yt-dlp extracted headers to bypass 403 blocks
    headers.update(custom_headers)

    # Ensure TikTok referer is always explicitly formatted
    if 'tiktok.com' in media_url:
        headers['Referer'] = 'https://www.tiktok.com/'

    try:
        req = requests.get(media_url, headers=headers, stream=True)
        req.raise_for_status()

        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': 'attachment; filename="video.mp4"'
            }
        )
    except requests.exceptions.RequestException as e:
        return f"Proxy stream error: {str(e)}", 500
    except Exception as e:
        return f"Proxy stream error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
