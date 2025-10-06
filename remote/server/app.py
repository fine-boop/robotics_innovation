from flask import Flask, request, send_from_directory
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'



def convert_to_3d_model(input_folder):
    pass



def download_folder():
    os.makedirs('downloads', exist_ok=True)
    DOWNLOAD_FOLDER = download_folder()
    return 'downloads/'


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

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)