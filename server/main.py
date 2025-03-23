import sys
from pathlib import Path
from flask import Flask, request, send_file, jsonify, make_response, Response
import io
import demucs.api
from datetime import datetime
from werkzeug.utils import secure_filename
from time import perf_counter
import uuid
from checkForDirectories.checkForDirectories import (
    ensure_directories,
    UPLOAD_DIR,
    OUTPUT_DIR
)

app = Flask(__name__)
separator = demucs.api.Separator(model="htdemucs")

@app.route("/separate", methods=['POST'])
def separate_audio():
    request_id = str(uuid.uuid4())
    start_time = perf_counter()
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        ensure_directories()
    except Exception as e:
        return jsonify({"error": f"Failed to create required directories: {str(e)}"}), 500

    mode = request.args.get('mode', '2')
    if mode not in ['2', '4']:
        return jsonify({"error": "Invalid mode. Use '2' for vocals/instrumental or '4' for all stems"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Add Content-Type validation
    if not file.content_type.startswith('audio/'):
        return jsonify({"error": "Invalid file type. Must be audio file"}), 415
    
    safe_filename = secure_filename(file.filename)
    file_path = UPLOAD_DIR / safe_filename

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save upload: {str(e)}"}), 500
    
    try:
        separation_start = perf_counter()
        origin, separated = separator.separate_audio_file(str(file_path))
        separation_time = perf_counter() - separation_start
        
        if mode == '2':
            vocals = separated['vocals']
            instrumental = sum(separated[stem] for stem in ['bass', 'drums', 'other'])
            stems = {
                'vocals': vocals,
                'instrumental': instrumental
            }
        else:
            stems = separated
    except Exception as e:
        return jsonify({"error": f"Separation failed: {str(e)}"}), 500
    
    # Generate download links for each stem
    download_links = {}
    for stem, source in stems.items():
        try:
            output_filename = f"{stem}_{safe_filename}"
            output_path = OUTPUT_DIR / output_filename
            
            # Save the audio file
            demucs.api.save_audio(source, str(output_path), samplerate=separator.samplerate)
            
            # Create download link
            download_url = request.host_url.rstrip('/') + f'/download/{output_filename}'
            download_links[stem] = download_url
            
        except Exception as e:
            return jsonify({"error": f"Failed to process {stem}: {str(e)}"}), 500

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

@app.route("/download/<filename>")
def download_file(filename):
    try:
        return send_file(
            OUTPUT_DIR / filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404

# Optional: Add cleanup route for old files
@app.route("/cleanup", methods=['POST'])
def cleanup_files():
    try:
        for file in OUTPUT_DIR.glob('*'):
            file.unlink()
        return jsonify({"message": "Cleanup successful"}), 200
    except Exception as e:
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8000)