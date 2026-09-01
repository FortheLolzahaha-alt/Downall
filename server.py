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

    # Standard yt-dlp Extraction for non-YouTube links
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
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
