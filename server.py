from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

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

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Extract first video if the URL returns a playlist or entry list
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            # 1. Try standard top-level direct URL
            media_url = info.get('url')
            
            # 2. Check requested downloads dictionary
            if not media_url and info.get('requested_downloads'):
                media_url = info['requested_downloads'][0].get('url')
                
            # 3. Fallback: Parse the formats array for the highest quality stream
            if not media_url and info.get('formats'):
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('url').startswith('http'):
                        media_url = fmt['url']
                        break
            
            if media_url:
                return jsonify({'download_url': media_url})
            
            return jsonify({'message': 'Could not extract direct media URL.'}), 400

    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
