from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
import metrics

# configure application
app = Flask(__name__)

metrics.main(True)

@app.route("/", methods=["GET", "POST"])
def index():
    """ Homepage shows overview of general host metrics """

    output = metrics.main(True)



    return render_template("index.html")
