import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from audio_processor import detect_notes, detect_key, transpose_notes

app = Flask(__name__)

# Configuration
UPLOADS_DIR = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Ensure the uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.config['UPLOADS_DIR'] = UPLOADS_DIR

def is_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file part in the request'}), 400

    file = request.files['audio_file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not is_allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    if request.content_length > MAX_FILE_SIZE_BYTES:
        return jsonify({'error': f'File size exceeds the limit of {MAX_FILE_SIZE_MB}MB'}), 413

    if file:
        try:
            filename = secure_filename(file.filename)
            # Ensure the uploads directory exists (it should from app startup, but good to double check)
            os.makedirs(app.config['UPLOADS_DIR'], exist_ok=True) 
            filepath = os.path.join(app.config['UPLOADS_DIR'], filename)
            file.save(filepath)
            return jsonify({'message': 'File uploaded successfully', 'file_id': filename}), 201
        except Exception as e:
            # Log the exception e for debugging
            return jsonify({'error': 'Failed to save file', 'details': str(e)}), 500
    
    return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio_file():
    if not request.is_json:
        return jsonify({'error': 'Invalid request: Content-Type must be application/json'}), 415

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request: No JSON data received'}), 400

    file_id = data.get('file_id')
    target_key = data.get('target_key')

    if not file_id:
        return jsonify({'error': 'Missing file_id in request'}), 400
    if not target_key:
        return jsonify({'error': 'Missing target_key in request'}), 400

    # It's good practice to secure the file_id if it's directly used to form a path,
    # though it should be already secured from the upload. Re-securing can prevent path traversal
    # if the file_id is somehow manipulated by the client after upload.
    secured_file_id = secure_filename(file_id)
    if secured_file_id != file_id:
        # This might indicate an attempt to use a non-standard filename
        return jsonify({'error': 'Invalid file_id format'}), 400
        
    audio_path = os.path.join(app.config['UPLOADS_DIR'], secured_file_id)

    if not os.path.exists(audio_path):
        return jsonify({'error': 'Audio file not found', 'file_id': secured_file_id}), 404

    try:
        original_notes = detect_notes(audio_path)
        if not original_notes: # detect_notes might return empty list on error or no notes
            # Depending on desired behavior, this could be an error or just empty results
            print(f"No original notes detected for {audio_path} or error in detect_notes.")
            # return jsonify({'error': 'No notes detected in the audio file or processing error in note detection'}), 500

        source_key = detect_key(original_notes)
        # Check if source_key indicates an error from detect_key
        if isinstance(source_key, str) and "Could not determine key" in source_key:
             print(f"Source key detection failed for {audio_path}: {source_key}")
             # Optionally, you might want to return an error or proceed without transposition
             # For now, we'll proceed and let transpose_notes handle it if it can't work with the key.

        transposed_notes = transpose_notes(original_notes, source_key, target_key)
        
        # If transpose_notes returns the original notes due to an error (e.g. invalid key),
        # it might be good to reflect this in the response or logs.
        # For now, the requirement is to return the result from transpose_notes.

        response_data = {
            "original_notes": original_notes,
            "detected_source_key": source_key,
            "transposed_notes": transposed_notes,
            "target_key": target_key
        }
        return jsonify(response_data), 200

    except Exception as e:
        # Log the exception e for debugging
        print(f"Error processing audio file {audio_path}: {e}")
        # It's important to log the actual exception e
        return jsonify({'error': 'Failed to process audio file', 'details': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
