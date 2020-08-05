import os
import math
import pandas as pd
# this fixed the RuntimeError: main thread is not in main loop but not sure what it does
import matplotlib
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import time

import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# configure application
app = Flask(__name__)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        error = False
        # Ensure username was submitted
        if not request.form.get("username"):
            error = True
            return render_template("login.html", error = error)

        # Ensure password was submitted
        elif not request.form.get("password"):
            error = True
            return render_template("login.html", error = error)
        
        username = request.form.get("username")
        
        # Query database for username
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        db.execute("SELECT * FROM users WHERE username = ?", username)
        rows = db.fetchall()
        # rows is a list of tuples in form of [(id, username, hash)]

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            error = True
            return render_template("login.html", error = error)
        conn.close()

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/plates")
def plates():
    return render_template("plates.html")

@app.route("/1rmcalc")
def rmcalc():
    return render_template("1rmcalc.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        error = 0
        username = request.form.get("username")
        password = request.form.get("password")

        # if submitted is blank/null
        if not username:
            error = 1
            return render_template("register.html", error = error)

        # if submitted is blank/null
        elif not password:
            error = 1
            return render_template("register.html", error = error)

        if username.isalnum() == False or password.isalnum() == False:
            error = 3
            return render_template("register.html", error = error)

        if len(password) < 8:
            error = 4
            return render_template("register.html", error = error)

        # if password does not match confirm password
        elif password != request.form.get("confirm-password"):
            error = 1
            return render_template("register.html", error = error)

        # if username already exists
        # query the database for username
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        username = request.form.get("username")
        db.execute("SELECT * FROM users WHERE username = ?", username)
        rows = db.fetchall()
        
        # if list  has 1 or more row, it means username already exists
        if len(rows) != 0:
            error = 2
            conn.close()
            return render_template("register.html", error = error)
            
        # username doesnt exist, store the submited info into the database
        else:
            # convert the password into a hash
            hpassword = generate_password_hash(password)

            conn = sqlite3.connect('lifting.db')
            db = conn.cursor()
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", (username, hpassword))
            conn.commit()
            conn.close()
            return render_template("index.html")
    else:
        return render_template("register.html")


@app.route("/change", methods = ["GET", "POST"])
@login_required
def change():
    """Change password"""
    success = False
    if request.method =="POST":
        error = False
        old = request.form.get('old')
        new =  request.form.get('new')
        confirm_new = request.form.get('confirm_new')

        # get old pass hash from db
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])
        rows = db.fetchall() # list of tuples in form of [(hash)]

        # old pass does not match
        if check_password_hash(rows[0][0], old) == False:
            error = True
            message = "old password must match"
            return render_template("change.html", error = error, message = message)
        conn.close()

        if not new or not confirm_new:
            error = True
            message = "must enter a new password"
            return render_template("change.html", error = error, message = message)

        if new != confirm_new:
            error = True
            message = "confirm new password"
            return render_template("change.html", error = error, message = message)

        if new.isalnum() == False:
            error = True
            message = "new password must be alpha-numeric"
            return render_template("change.html", error = error, message = message)

        if len(new) < 8:
            error = True
            message = "password must be at least 8 characters"
            return render_template("change.html", error = error, message = message)

        else:
            conn = sqlite3.connect('lifting.db')
            db = conn.cursor()
            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new), session["user_id"])
            conn.commit()
            conn.close()
            success = True
            return render_template("change.html", success = success)
    else:
        return render_template("change.html", success = success)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to index
    return redirect("/")

@app.route("/LogSets", methods=["GET", "POST"])
@login_required
def LogSets():
    """allows user to enter a new set"""
    conn = sqlite3.connect('lifting.db')
    db = conn.cursor()
    db.execute("SELECT * FROM exercises")
    exercises = db.fetchall() # list of tuples in form of [(name)]
    
    # turn exercises into a list
    array = []
    for item in exercises:
        array.append(item[0])
    conn.close()

    if request.method == "POST":
        sets = int(request.form.get('sets'))
        reps = int(request.form.get('reps'))
        weight = round(float(request.form.get('weight')), 1)
        lift = request.form.get('select')
        estimated_1rm = round((weight * (36/( 37 - reps))), 1)

        #update the db
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        db.execute("INSERT INTO tracker (id, sets, reps, weight, exercise, onerm) VALUES(?, ?, ?, ?, ?, ?)", (session["user_id"], sets, reps, weight, lift, estimated_1rm))
        conn.commit()
        conn.close()

        return redirect("/history")
    else:
        return render_template("logsets.html", array = array)


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    # get the exercises that the current user has entered data for
    conn = sqlite3.connect('lifting.db')
    db = conn.cursor()
    db.execute("SELECT DISTINCT exercise FROM tracker WHERE id = ?", (session["user_id"],)) # ok, so the 2nd argument in execute() must be a tuple, so (var_name,) is the appropriate syntax
    exercises = db.fetchall() # list of tuples in form of [(exercise)]
    if not exercises:
        error = True
        message = "You have not tracked any lifts"
        return render_template("history.html", error = error, message = message)
    # turn exercises into an array
    array = []
    for item in exercises:
        array.append(item[0])
    conn.close()

    if request.method == "POST":
        lift = request.form.get('select')
        if lift == "Select lift":
            return render_template("history.html", array = array)

        # query the db, select the highest onerm for each datetime
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        db.execute("SELECT date, onerm FROM tracker WHERE id = ? and exercise = ? GROUP BY date ORDER BY date", (session["user_id"], lift))
        data = db.fetchall() # list of tuples in form of [(date, onerm)]
        
        # turn data into a dataframe, update the column headers
        df = pd.DataFrame(data)
        df.columns = ['date', 'onerm']
        # close the database
        conn.close()

        # convert the onerm into a useable format
        df['onerm'] = pd.to_numeric(df.onerm)
        # convert the datetime into a useable format
        df['date'] = pd.to_datetime(df.date)

        # plot the dataframe
        df.plot(kind = 'line', x = 'date', y = 'onerm')
        # create dynamic string that will be used for cache busting
        var = "?ver=" + str(time.time())
        # save the new figure
        plt.savefig('static/output.png')
        # clear the plot
        plt.clf()

        # create history table for the page
        conn = sqlite3.connect('lifting.db')
        db = conn.cursor()
        db.execute("SELECT sets, reps, weight, timestamp FROM tracker WHERE id = ? and exercise = ? ORDER BY date", (session["user_id"], lift))
        table = db.fetchall() # list of (sets, reps, weight, timestamp)
        conn.close()

        # return the cache-busting string
        return render_template("history.html", array = array, lift = lift, var = var, table = table)
    else:
        return render_template("history.html", array = array)