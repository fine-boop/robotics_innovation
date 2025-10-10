from flask import Flask, request, send_from_directory, abort
import os
from datetime import datetime

app = Flask(__name__)

KEY = os.environ.get('KEY', 'onfewio4fu3i4gberiuvb4rievbeiruf3eiuferiugferi')
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)




def check_key():
    provided = request.args.get('key') or request.headers.get('X-API-Key')
    return provided == KEY



@app.route('/uploads/', methods=['POST'])
def upload_file():
    if not check_key():
        abort(403)

    if 'file' not in request.files:
        abort(400)

    f = request.files['file']
    filename = f"photos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    dest = os.path.join(UPLOAD_FOLDER, filename)
    f.save(dest)
    print(dest)
    print(f"Saved uploaded zip file to {dest}")
    os.system(f'sudo cp {dest} archives/ && mv {dest} photogrammetry/photos/ && cd photogrammetry/photos && unzip {filename} && rm {filename}')
    with open('upload_log.txt', 'a') as log:
        log.write(f"{datetime.now().isoformat()} - {filename}\n")   
    return 'File uploaded', 200
    




@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    if not check_key():
        abort(403)
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 1337)), debug=(os.environ.get('DEBUG') == '1'))
