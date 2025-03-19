from flask import Flask, request, render_template, redirect, url_for, session
import math
import os
import json
import random
import re
from urllib.parse import quote
from collections import Counter
import requests
import time

# Flask app setup
app = Flask(__name__)


# Round 4 functions
def round_4(value):
    if value.is_integer():
        return f"{int(value)}"
    elif len(f"{value}".split('.')[1]) <= 4:
        return f"{value}"
    else:
        return f"~{value:.4f}"


@app.route("/")
def index():
    return render_template('budget.html')

@app.route("/appreciation-depreciation")
def appreciation_depreciation():
    return render_template('appreciation-depreciation.html')

@app.route("/stocks")
def stock_grapher():
    return render_template('stock-grapher.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0")

