from flask import Flask, render_template, request

app = Flask(__name__)

@app.route ('/', method=["GET", "POST"])
def profile():
    return render_template('profile.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)