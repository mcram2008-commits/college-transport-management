from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'HELLO FLASK'

if __name__ == '__main__':
    print("STARTING TEST SERVER")
    app.run(port=5000)
