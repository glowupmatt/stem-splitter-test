import sys
import os
import io
import time
from dotenv import load_dotenv
from server.utils.upload_to_s3 import upload_to_s3
from pathlib import Path
import tempfile
import boto3
from flask import Blueprint, request, jsonify
sys.path.append(str(Path(__file__).parent.parent))
import demucs.api
from werkzeug.utils import secure_filename
from time import perf_counter
import uuid

load_dotenv()
separate_routes = Blueprint("audio", __name__)
separator = demucs.api.Separator(model="htdemucs")

ALLOWED_EXTENSIONS = {'wav', 'mp3'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
  
@separate_routes.route("/", methods=['POST'])
def separate_audio():
    start_time = perf_counter()
    bucket_name = os.getenv('AWS_BUCKET_NAME')
# ============= Check if file is provided =============
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
# ============= Check if file is provided =============

    try:
# ============= Read file content into memory =============
        file_content = file.read()
# ============= Read file content into memory =============

# ============= Create temporary file =============
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
# ============= Create temporary file =============

# ============= Generate a safe unique filename for the uploaded file =============
        safe_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
# ============= Generate a safe unique filename for the uploaded file =============

# ============= Upload original file to S3 =============
        s3_path = f"originals/{safe_filename}"
        s3_client = boto3.client('s3')
        
        s3_upload_buffer = io.BytesIO(file_content)
        s3_client.upload_fileobj(
            s3_upload_buffer,
            bucket_name,
            s3_path,
            ExtraArgs={
                'ContentType': 'audio/mpeg',
                'ACL': 'public-read'
            }
        )
# ============= Upload original file to S3 =============

# ============= Generate URL for original file =============
        original_url = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"
# ============= Generate URL for original file =============

# ============= Separate audio into stems =============
        try:
            separation_start = perf_counter()
            origin, separated = separator.separate_audio_file(temp_path)
            separation_time = perf_counter() - separation_start
            # Clean up temporary file
            os.unlink(temp_path)
            # Handle separation mode (2-stem or 4-stem)
            mode = request.form.get('mode', '2')
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
# ============= Separate audio into stems =============

# ============= Upload stems to S3 =============
        download_links = {}
        for stem, source in stems.items():
            try:
                # Save the audio to a temporary file
                temp_stem_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{stem}.mp3')
                temp_path = temp_stem_file.name
                temp_stem_file.close() 
                
                demucs.api.save_audio(source, temp_path, samplerate=separator.samplerate)
                
                # Wait before uploading to S3
                time.sleep(0.5)
                # Wait before uploading to S3
                
                # Upload the file to S3
                stem_filename = f"{stem}_{safe_filename}"
                s3_path = f"stems/{stem_filename}"
                retry_count = 0
                max_retries = 5
                # Upload the file to S3
                
                # Retry logic for uploading to S3
                while retry_count < max_retries:
                    try:
                        with open(temp_path, 'rb') as file_data:
                            s3_client.upload_fileobj(
                                file_data,
                                bucket_name,
                                s3_path,
                                ExtraArgs={
                                    'ContentType': 'audio/mpeg',
                                    'ACL': 'public-read'
                                }
                            )
                        break
                    except PermissionError:
                        retry_count += 1
                        if retry_count == max_retries:
                            return jsonify({"error": f"Could not upload {stem} to S3"}), 500
                        time.sleep(1)
                # Retry logic for uploading to S3
                
                # Generate download link
                download_links[stem] = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"
                # Generate download link
                
                # Clean up with retry logic
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        os.unlink(temp_path)
                        break
                    except PermissionError:
                        retry_count += 1
                        if retry_count == max_retries:
                            return jsonify({"error": f"Failed to delete temporary file {retry_count}"}), 500
                        time.sleep(1)
                  # Clean up with retry logic
            except Exception as e:
                return jsonify({"error": f"Error processing {stem}: {str(e)}"}), 500
              
            #Add download link to response
            download_links[stem] = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"
            #Add download link to response
# ============= Upload stems to S3 =============

        return jsonify({
            "message": "Separation complete",
            "downloads": download_links,
            "processing_time": perf_counter() - start_time,
            "separation_time": separation_time,
            "original_file": original_url
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Separation failed: {str(e)}",
            "details": str(e)
        }), 500