import sys
from pathlib import Path
# Add the root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from flask import Flask, request, send_file, jsonify, make_response, Response
import io
import zipfile
import demucs.api
import os
from pathlib import Path
import shutil

app = Flask(__name__)

# Initialize the separator
separator = demucs.api.Separator(model="htdemucs")

# Create output directory
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path.home() / "Downloads" / "OTGU_Splitter"

def ensure_directories():
    """Ensure all required directories exist and are writable"""
    # Create uploads directory
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        print(f"Upload dir: {UPLOAD_DIR} (exists: {UPLOAD_DIR.exists()})")
    except Exception as e:
        print(f"Warning: Could not create upload directory: {str(e)}")
    
    # Create Downloads directory if it doesn't exist
    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
        print(f"Downloads dir: {downloads_dir} (exists: {downloads_dir.exists()})")
    except Exception as e:
        print(f"Warning: Could not create Downloads directory: {str(e)}")
    
    # Create OTGU_Splitter directory
    try:
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        print(f"Output dir: {OUTPUT_DIR} (exists: {OUTPUT_DIR.exists()})")
    except Exception as e:
        print(f"Warning: Could not create OTGU_Splitter directory: {str(e)}")
    
    print(f"Directory check complete")
    return True

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route("/separate", methods=['POST'])
def separate_audio():
    # Debug: Print absolute paths
    print(f"Current working directory: {os.getcwd()}")
    print(f"Absolute UPLOAD_DIR: {UPLOAD_DIR.absolute()}")
    print(f"Absolute OUTPUT_DIR: {OUTPUT_DIR.absolute()}")
    
    # Ensure directories exist before processing
    ensure_directories()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    file_path = UPLOAD_DIR / file.filename
    
    # Debug: Print file information
    print(f"Received file: {file.filename}")
    print(f"Saving upload to: {file_path.absolute()}")
    
    try:
        file.save(file_path)
        print(f"File saved successfully to upload directory")
    except Exception as e:
        print(f"Error saving uploaded file: {str(e)}")
        return jsonify({"error": f"Failed to save upload: {str(e)}"}), 500
    
    # Separate audio
    try:
        print("Starting audio separation...")
        origin, separated = separator.separate_audio_file(str(file_path))
        print("Audio separation completed")
    except Exception as e:
        print(f"Error during separation: {str(e)}")
        return jsonify({"error": f"Separation failed: {str(e)}"}), 500
    
    # Create zip file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for stem, source in separated.items():
            try:
                output_filename = f"{stem}_{file.filename}"
                output_path = OUTPUT_DIR / output_filename
                print(f"Saving {stem} to: {output_path.absolute()}")
                
                # Save the audio file
                demucs.api.save_audio(source, str(output_path), samplerate=separator.samplerate)
                print(f"Successfully saved {stem}")
                
                # Add to zip file
                zf.write(output_path, output_filename)
                
            except Exception as e:
                print(f"Error processing {stem}: {str(e)}")
                return jsonify({"error": f"Failed to process {stem}: {str(e)}"}), 500

    # Clean up upload file
    try:
        file_path.unlink()
    except Exception as e:
        print(f"Warning: Could not delete upload file: {str(e)}")

    # # Clean up separated files after adding to zip
    # for stem in separated.keys():
    #     try:
    #         output_path = OUTPUT_DIR / f"{stem}_{file.filename}"
    #         output_path.unlink()
    #     except Exception as e:
    #         print(f"Warning: Could not delete separated file {stem}: {str(e)}")

    # Prepare zip file for download
    memory_file.seek(0)
    response = make_response(memory_file.getvalue())
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = f'attachment; filename=separated_tracks_{file.filename}.zip'
    
    return response
  
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8000)