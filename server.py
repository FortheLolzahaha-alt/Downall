from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # Prevents Cross-Origin Request errors between HTML and Python

@app.route('/download', methods=['GET'])
def extract_video():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'message': 'No URL provided'}), 400

    # Configure yt-dlp to extract direct video streams
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Extract direct media stream URL
            media_url = info.get('url') or (info.get('requested_downloads', [{}])[0].get('url'))
            
            if media_url:
                return jsonify({'download_url': media_url})
            
            return jsonify({'message': 'Could not extract direct media URL.'}), 400

    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    # Runs the server on port 5000 matching the HTML fetch request
    app.run(host='127.0.0.1', port=5000, debug=True)