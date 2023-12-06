from pyeod import config
from flask import Flask
import sys
import subprocess

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


@app.route("/update")
def update():
    subprocess.Popen(["git", "pull"])
    open(config.restartfile, "w+").close()
    return "Updating bot"


def run_webserver():
    proc = subprocess.Popen([sys.executable, "-m", __name__])
    return proc
