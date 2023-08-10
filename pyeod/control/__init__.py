from flask import Flask
import multiprocessing
from pyeod import config

app = Flask(__name__)

@app.route("/")
def index():
    return """
    Bot is running<br>Refresh this page to update<br>
    <a href='/stop'>Stop</a> <a href='/restart'>Restart</a>
    """

@app.route("/stop")
def stop():
    open(config.stopfile, "w+").close()
    return "Bot stopped"

@app.route("/restart")
def restart():
    open(config.restartfile, "w+").close()
    return "Bot restarted"

def run_webserver():
    proc = multiprocessing.Process(
        target=app.run,
        args=("0.0.0.0", 5001),
        daemon=True
    )
    proc.start()
    return proc
