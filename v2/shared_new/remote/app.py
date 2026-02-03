from flask import Flask, request, session, Response, jsonify, send_from_directory, render_template, after_this_request
import time
import os
import requests

# Import photogrammetry processor
from photogrammetry_processor_module import process_photogrammetry

app = Flask(__name__)




@app.route('/')
def browse():
    return """<h1>OK</h1>"""

@app.route('/status')
def status():
    return "OK", 200


@app.route('/upload/', methods=['POST'])
def upload_file():
    file = request.files['files']
    file.save('uploads/' + file.filename)
    proccess_file(file.filename)
    return "OK", 200




@app.route('/downloads/<int:model_id>')
def download(model_id):
    filename = f'{model_id}.zip'
    directory = 'downloads'
    file_path = os.path.join(directory, filename)

    if os.path.exists(file_path):

        @after_this_request
        def remove_file(response):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file: {e}")
            return response

        return send_from_directory(directory, filename, as_attachment=True)
    else:
        return "nonexistent", 400



@app.route('/download_list')
def ready_downloads():
    ready = os.listdir('downloads')
    return jsonify({
        "ready_downloads": ready
    })





def proccess_file(file):
    # Run photogrammetry processing
    process_photogrammetry(file)
    
    


if __name__ == '__main__':
    app.run('0.0.0.0', port=80)