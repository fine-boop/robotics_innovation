from flask import Flask, request
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'

def new_uploads_folder():
    os.system("rm -rf uploads/*")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/uploads/', methods=['POST'])
def upload_file():
    new_uploads_folder()
    file = request.files['file']
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    print("Trying to unzip files")
    os.system("cd uploads && ls && unzip photos.zip && rm photos.zip && cd ..")
    return 'File uploaded successfully   ', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)