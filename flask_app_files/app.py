import os
import subprocess
import logging
from pathlib import Path
import uuid 
import shutil 
from flask import Flask, request, render_template_string, send_from_directory, flash, redirect, url_for, session
from werkzeug.utils import secure_filename

# Paths are relative to the container's filesystem
FLASK_APP_BASE_DIR = '/app' # Where this Flask app.py script runs
SHARED_DATA_DIR = '/app_data' # Base for uploads and converted files
UPLOAD_FOLDER = os.path.join(SHARED_DATA_DIR, 'uploads')
CONVERTED_FOLDER = os.path.join(SHARED_DATA_DIR, 'converted')

# Path to ThermoRawFileParser.exe inside the container
THERMO_PARSER_EXE_PATH = "/opt/thermorawfileparser/ThermoRawFileParser.exe"

ALLOWED_EXTENSIONS = {'raw'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 示例：5 GB 上传限制 (已注释掉)
app.secret_key = os.urandom(24) # Required for session and flash messages

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['CONVERTED_FOLDER']).mkdir(parents=True, exist_ok=True)
app.logger.info(f"Flask app: Upload folder: {app.config['UPLOAD_FOLDER']}")
app.logger.info(f"Flask app: Converted folder: {app.config['CONVERTED_FOLDER']}")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

INDEX_THERMO_MERGED_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Thermo Raw File Parser (Flask - Merged)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; color: #333; line-height: 1.6; }
        .container { background-color: #fff; padding: 25px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 900px; margin: 30px auto; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 25px; text-align: center;}
        h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #ecf0f1; padding-bottom: 8px;}
        .flash-messages { padding-left: 0; margin-bottom: 20px; }
        .flash-messages li { list-style: none; padding: 12px 18px; margin-bottom: 12px; border-radius: 6px; font-size: 0.98em; border-left-width: 5px; border-left-style: solid; }
        .flash-success { background-color: #e8f5e9; color: #2e7d32; border-left-color: #4caf50; }
        .flash-error { background-color: #ffebee; color: #c62828; border-left-color: #f44336; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
        input[type="file"], input[type="text"], input[type="submit"], select { 
            padding: 12px; 
            border-radius: 6px; 
            border: 1px solid #ccc; 
            width: calc(100% - 24px); /* Adjusted for padding */
            margin-bottom: 10px;
            box-sizing: border-box;
            font-size: 1em;
        }
        input[type="file"] { background-color: #ecf0f1; }
        input[type="submit"] { 
            background-color: #3498db; 
            color: white; 
            cursor: pointer; 
            border: none;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }
        input[type="submit"]:hover { background-color: #2980b9; }
        .output-container { margin-top: 30px; }
        .output { 
            padding: 15px; 
            background-color: #2c3e50; /* Darker background for code */
            color: #ecf0f1; /* Lighter text for contrast */
            border: 1px solid #34495e; 
            border-radius: 6px; 
            white-space: pre-wrap; 
            word-wrap: break-word; 
            max-height: 400px; 
            overflow-y: auto; 
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
        }
        .download-section ul { list-style: none; padding-left: 0; }
        .download-section li { margin-bottom: 8px; background-color: #f9f9f9; padding: 8px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;}
        .download-link { 
            padding: 8px 15px; 
            background-color: #2ecc71; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            font-size: 0.9em;
            transition: background-color 0.3s ease;
        }
        .download-link:hover { background-color: #27ae60; }
        .help-text { font-size: 0.9em; color: #7f8c8d; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Thermo Raw File Parser</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <ul class="flash-messages">
            {% for category, message in messages %}
              <li class="flash-{{ category }}">{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}

        <h2>1. Upload and Parse File(s)</h2>
        <form method="post" action="{{ url_for('upload_and_parse_file') }}" enctype="multipart/form-data">
          <div class="form-group">
            <label for="files">Select Thermo .raw file(s):</label>
            <input type="file" name="files" id="files" accept=".raw" multiple required>
            <p class="help-text">You can select multiple .raw files for batch processing.</p>
          </div>
          <div class="form-group">
            <label for="output_format">Output Format (-f parameter for ThermoRawFileParser):</label>
            <select name="output_format" id="output_format">
                <option value="1">mzML (default)</option>
                <option value="2">indexed mzML</option>
                <option value="0">None (metadata and scan headers)</option>
                <option value="3">Parquet</option>
                <option value="4">MGF</option>
            </select>
          </div>
           <div class="form-group">
            <label for="additional_args">Additional ThermoRawFileParser.exe parameters (optional):</label>
            <input type="text" name="additional_args" id="additional_args" placeholder="e.g., --noPeakPicking --chro /app_data/converted/batch_X/chro.txt">
             <p class="help-text">Input directory is handled automatically. Output directory will be <code>/app_data/converted/&lt;batch_id&gt;/</code>.</p>
          </div>
          <input type="submit" value="Upload and Start Parsing">
        </form>

        {% if converted_files_list and batch_output_subdir %}
        <div class="output-container download-section">
            <h2>2. Download Results</h2>
            <p>Files processed in batch output directory: <strong>{{ batch_output_subdir }}</strong></p>
            {% if converted_files_list %}
                <ul>
                {% for file_info in converted_files_list %}
                    <li>
                        <span>{{ file_info.name }}</span>
                        <a href="{{ url_for('download_parsed_file', batch_subdir=batch_output_subdir, filename=file_info.name) }}" class="download-link">Download</a>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p>No specific output files were generated or found for this format in the batch directory.</p>
            {% endif %}
        </div>
        {% endif %}

        {% if command_output %}
        <div class="output-container">
            <h2>Command Output (for debugging):</h2>
            <pre class="output">{{ command_output }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/', methods=['GET'])
def index():
    # Clear session data for new visit to index page
    session.pop('converted_files_list', None)
    session.pop('batch_output_subdir', None)
    return render_template_string(INDEX_THERMO_MERGED_HTML)

@app.route('/upload-parse', methods=['POST'])
def upload_and_parse_file():
    # Initialize variables for rendering template
    converted_files_list_for_template = None
    batch_output_subdir_for_template = None
    command_output_display = None
    
    uploaded_files = request.files.getlist("files") 
    output_format_code = request.form.get('output_format', '1')
    additional_args_str = request.form.get('additional_args', '')

    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        flash('No files selected.', 'error')
        return redirect(url_for('index'))

    # Create a unique batch directory for this upload session
    batch_id = str(uuid.uuid4())
    linux_batch_upload_dir = Path(app.config['UPLOAD_FOLDER']) / batch_id
    linux_batch_converted_dir = Path(app.config['CONVERTED_FOLDER']) / f"{batch_id}_out"

    try:
        linux_batch_upload_dir.mkdir(parents=True, exist_ok=True)
        linux_batch_converted_dir.mkdir(parents=True, exist_ok=True)
        app.logger.info(f"Created batch upload directory: {linux_batch_upload_dir}")
        app.logger.info(f"Created batch converted directory: {linux_batch_converted_dir}")

        saved_files_info = [] # Store info about saved files
        first_original_filename = None 
        for file_to_upload in uploaded_files:
            if file_to_upload and allowed_file(file_to_upload.filename):
                original_filename = secure_filename(file_to_upload.filename)
                if not first_original_filename: # Keep track of the first valid original filename
                    first_original_filename = original_filename
                
                linux_input_filepath = linux_batch_upload_dir / original_filename
                file_to_upload.save(linux_input_filepath)
                app.logger.info(f"File '{original_filename}' saved to: {linux_input_filepath}")
                saved_files_info.append({
                    "original_filename": original_filename,
                    "linux_path": linux_input_filepath
                })
            else:
                flash(f"File '{file_to_upload.filename}' has an invalid type and was skipped.", 'error')
        
        if not saved_files_info:
            flash('No valid files were uploaded.', 'error')
            shutil.rmtree(linux_batch_upload_dir, ignore_errors=True)
            shutil.rmtree(linux_batch_converted_dir, ignore_errors=True)
            return redirect(url_for('index'))

        flash(f"{len(saved_files_info)} file(s) uploaded successfully. Starting parsing...", "success")

        # --- Start Conversion ---
        app.logger.info("Starting conversion process...")
            
        parser_args = []
        if len(saved_files_info) == 1:
            single_file_info = saved_files_info[0]
            parser_args.extend(["-i", str(single_file_info["linux_path"])])
            app.logger.info(f"Single file mode: using -i {single_file_info['linux_path']}")
        else:
            parser_args.extend(["-d", str(linux_batch_upload_dir)])
            app.logger.info(f"Batch mode: using -d {linux_batch_upload_dir}")
        
        parser_args.extend([
            "-o", str(linux_batch_converted_dir) + os.sep, 
            "-f", output_format_code,
        ])
        
        if additional_args_str:
            parser_args.extend(additional_args_str.split())

        command_parts = [
            "mono", 
            THERMO_PARSER_EXE_PATH
        ]
        command_parts.extend(parser_args)

        full_command_str_for_log = " ".join([f"'{part}'" if " " in part or ":" in part else part for part in command_parts])
        app.logger.info(f"Preparing to execute command: {full_command_str_for_log}")
        
        result = subprocess.run(command_parts, capture_output=True, text=True, timeout=1800) 
        
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode

        command_output_display = (
            f"Command Executed: {full_command_str_for_log}\n"
            f"Exit Code: {exit_code}\n"
            f"--- STDOUT ---\n{stdout}\n"
            f"--- STDERR ---\n{stderr}"
        )
        app.logger.info(f"Command STDOUT: {stdout}")
        if stderr:
            app.logger.warning(f"Command STDERR: {stderr}")

        processed_files_info_for_session = [] 
        if exit_code == 0:
            flash(f"Processing completed with exit code {exit_code}.", "success")
            for item in linux_batch_converted_dir.iterdir():
                if item.is_file():
                    processed_files_info_for_session.append({"name": item.name})
            
            if processed_files_info_for_session:
                session['converted_files_list'] = processed_files_info_for_session
                session['batch_output_subdir'] = f"{batch_id}_out"
                converted_files_list_for_template = processed_files_info_for_session
                batch_output_subdir_for_template = f"{batch_id}_out"
            elif output_format_code != '0': 
                 flash("Processing complete, but no output files found in the expected directory.", "warning")
                 app.logger.warning("Processing complete, but no output files found.")
            else: 
                flash("Processing complete (output format was 'None'). No files to download.", "success")
                app.logger.info("Processing complete with output format 'None'.")
        else: 
            error_msg = f"Parsing failed. Exit code: {exit_code}."
            flash(error_msg, "error")
            app.logger.error(error_msg)
    
    except subprocess.TimeoutExpired:
        error_msg = "ThermoRawFileParser execution timed out!"
        flash(error_msg, 'error')
        app.logger.error(error_msg)
        command_output_display = error_msg
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        flash(error_msg, 'error')
        app.logger.exception("An error occurred during file processing")
        command_output_display = error_msg
    
    return render_template_string(INDEX_THERMO_MERGED_HTML, 
                                  converted_files_list=converted_files_list_for_template,
                                  batch_output_subdir=batch_output_subdir_for_template,
                                  command_output=command_output_display)

@app.route('/download-parsed/<batch_subdir>/<path:filename>')
def download_parsed_file(batch_subdir, filename):
    safe_batch_subdir = secure_filename(batch_subdir) 
    safe_filename = secure_filename(filename)

    if not safe_filename or not safe_batch_subdir: 
        flash('Invalid filename or batch directory for download.', 'error')
        return redirect(url_for('index'))
    
    directory_to_serve_from = Path(app.config['CONVERTED_FOLDER']) / safe_batch_subdir
    
    try:
        app.logger.info(f"Download request for: {safe_filename} from directory: {directory_to_serve_from}")
        return send_from_directory(str(directory_to_serve_from),
                                   safe_filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found for download.', 'error')
        app.logger.error(f"Download request: File not found {directory_to_serve_from / safe_filename}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error during download: {str(e)}', 'error')
        app.logger.exception(f"Error during download of: {safe_filename} from {safe_batch_subdir}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
