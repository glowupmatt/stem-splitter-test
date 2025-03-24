import sys
from pathlib import Path
from flask import Flask, request, send_file, jsonify, make_response, Response
from flask_cors import CORS
import io
sys.path.append(str(Path(__file__).parent.parent))
import demucs.api
from datetime import datetime
from werkzeug.utils import secure_filename
from time import perf_counter
import uuid
# from redis import Redis
# from checkForDirectories.checkForDirectories import (
#     ensure_directories,
#     UPLOAD_DIR,
#     OUTPUT_DIR
# )

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
# redis_client = Redis(host='localhost', port=6379, db=0) 
separator = demucs.api.Separator(model="htdemucs")
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Content-Disposition"]  # Important for downloads
    }
})

@app.route("/separate", methods=['POST'])
def separate_audio():
    request_id = str(uuid.uuid4())
    start_time = perf_counter()
    
    # try:
    #     ensure_directories()
    # except Exception as e:
    #     return jsonify({"error": f"Failed to create directories: {str(e)}"}), 500

    # check if there is a file key in the request
    print(f"====== REQUEST FILES {request.files} REQUEST FILES =======")
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # check if there is a file data isn't empty
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Actual splitting functionality
    try:
        safe_filename = secure_filename(file.filename)
        file_path = UPLOAD_DIR / safe_filename
        file.save(file_path)  # Uncomment and move file saving here
        

        separation_start = perf_counter()
        origin, separated = separator.separate_audio_file(str(file_path))
        separation_time = perf_counter() - separation_start
        
        mode = request.form.get('mode', '2')  # Default to '2' if not provided
        print(mode)
        if mode == '2':
            vocals = separated['vocals']
            instrumental = sum(separated[stem] for stem in ['bass', 'drums', 'other'])
            stems = {
                'vocals': vocals,
                'instrumental': instrumental
            }
        else:
            stems = separated

        # Process stems and create download links
        download_links = {}
        for stem, source in stems.items():
            output_filename = f"{stem}_{safe_filename}"
            output_path = OUTPUT_DIR / output_filename
            print(f"Saving to: {output_path}")  # Debug print
            demucs.api.save_audio(source, str(output_path), samplerate=separator.samplerate)
            # Verify file was created
            if output_path.exists():
                print(f"File successfully created at {output_path}")
            else:
                print(f"Failed to create file at {output_path}")
            download_url = request.host_url.rstrip('/') + f'/outputs/{output_filename}'
            download_links[stem] = download_url

        # Clean up upload file
        try:
            file_path.unlink()
        except Exception as e:
            print(f"[{request_id}] Could not delete upload file: {str(e)}")

        return jsonify({
            "message": "Separation complete",
            "downloads": download_links,
            "processing_time": perf_counter() - start_time,
            "separation_time": separation_time
        })

    except Exception as e:
        # Clean up any partial files
        try:
            if 'file_path' in locals():
                file_path.unlink()
        except OSError as cleanup_error:
            # Log the cleanup error but continue with the main error response
            print(f"Failed to clean up file: {cleanup_error}")
        
        return jsonify({
            "error": f"Separation failed: {str(e)}",
            "details": str(e)
        }), 500

@app.route("/outputs/<filename>")
def download_file(filename):
    try:
        return send_file(
            OUTPUT_DIR / filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404

# # Optional: Add cleanup route for old files
# @app.route("/cleanup", methods=['POST'])
# def cleanup_files():
#     try:
#         for file in OUTPUT_DIR.glob('*'):
#             file.unlink()
#         return jsonify({"message": "Cleanup successful"}), 200
#     except Exception as e:
#         return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8000)