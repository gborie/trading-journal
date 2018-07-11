import os
import csv
from datetime import datetime
from flask import Flask, flash, render_template, request, session, redirect, jsonify, url_for
from flask_session import Session
import pandas as pd
import requests
from sqlalchemy import and_, or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from helpers import *
from model import *


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["UPLOAD_FOLDER_PIC"] = UPLOAD_FOLDER_PIC
db.init_app(app)


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/", methods=["GET", "POST"])
def index():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        trade = Trade.query.order_by(Trade.id.asc()).filter(Trade.user_id == session["id"]).first()
        keyword = request.form.get("keyword")

        if not keyword:
            keyword = str(trade.date)

        # Make sure data requested exists
        trades = Trade.query.order_by(Trade.id.desc()).filter(and_(Trade.user_id == session["id"],
                 Trade.date_time_open >= keyword.upper())).all()

        if not trades:
            return render_template("error.html", message="No trades to display.")
        else:
            sum_pnl_w = 0
            sum_pnl_l = 0
            w = 0
            l = 0

            for i in range(len(trades)):
                if trades[i].w_l == "w":
                    w += 1
                    sum_pnl_w += trades[i].pnl-trades[i].commission

                elif trades[i].w_l == "l":
                    l += 1
                    sum_pnl_l += trades[i].pnl-trades[i].commission

        t = w + l
        sum_risk = 0
        sum_pnl = 0
        r = 0

        date = trades[0].date
        day = 1

        for i in range(len(trades)):
            sum_pnl += trades[i].pnl-trades[i].commission
            if trades[i].risk:
                sum_risk += trades[i].risk
                r += 1
            if trades[i].date != date:
                date = trades[i].date
                day += 1

        return render_template("index.html", trades=trades, sum_risk=sum_risk, sum_pnl=sum_pnl, sum_pnl_w=sum_pnl_w,
                                sum_pnl_l=sum_pnl_l, w=w, l=l, t=t, r=r, day=day, keyword=keyword)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        trade = Trade.query.order_by(Trade.id.asc()).filter(Trade.user_id == session["id"]).first()
        if not trade:
            return render_template("error.html", message="No trades to display.")
        else:
            keyword = str(trade.date)

            # Make sure data requested exists
            trades = Trade.query.order_by(Trade.id.desc()).filter(and_(Trade.user_id == session["id"],
                     Trade.date_time_open >= keyword.upper())).all()


            sum_pnl_w = 0
            sum_pnl_l = 0
            w = 0
            l = 0

            for i in range(len(trades)):
                if trades[i].w_l == "w":
                    w += 1
                    sum_pnl_w += trades[i].pnl-trades[i].commission

                elif trades[i].w_l == "l":
                    l += 1
                    sum_pnl_l += trades[i].pnl-trades[i].commission

        t = w + l
        sum_risk = 0
        sum_pnl = 0
        r = 0

        date = trades[0].date
        day = 1

        for i in range(len(trades)):
            sum_pnl += trades[i].pnl-trades[i].commission
            if trades[i].risk:
                sum_risk += trades[i].risk
                r += 1
            if trades[i].date != date:
                date = trades[i].date
                day += 1

        return render_template("index.html", trades=trades, sum_risk=sum_risk, sum_pnl=sum_pnl, sum_pnl_w=sum_pnl_w,
                                sum_pnl_l=sum_pnl_l, w=w, l=l, t=t, r=r, day=day, keyword=keyword)


@app.route("/stats", methods=["GET", "POST"])
def stats():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    if request.method == "POST":
        # read excel file
        df = pd.read_excel('esi_nace2.xlsx',sheet_name='ESI MONTHLY')
        # add index names and reset index to only keep Dates
        df.index.names = ['Dates', 'Num']
        index = df.index.levels[0].unique()
        df.reset_index(inplace=True)
        df['Dates'] = pd.to_datetime(index)
        df.set_index('Dates',inplace=True)
        # clean df by dropping empty columns
        df.drop('Num', axis=1, inplace=True)
        df = df.dropna(axis=1,how='all')

        return render_template("stats.html", df=df.to_html, name="GB")

    else:
        # read excel file
        df = pd.read_excel('esi_nace2.xlsx',sheet_name='ESI MONTHLY')
        # add index names and reset index to only keep Dates
        df.index.names = ['Dates', 'Num']
        index = df.index.levels[0].unique()
        df.reset_index(inplace=True)
        df['Dates'] = pd.to_datetime(index)
        df.set_index('Dates',inplace=True)
        # clean df by dropping empty columns
        df.drop('Num', axis=1, inplace=True)
        df = df.dropna(axis=1,how='all')

        eu_indu = df['EU.INDU']
        print(df)
        print(eu_indu)
        
        return render_template("stats.html", df=df.to_html, name="GB", eu_indu=eu_indu)


@app.route("/charts", methods=["GET", "POST"])
def charts():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    if request.method == "POST":

        trade = Trade.query.get(1)
        keyword = request.form.get("keyword")

        if not keyword:
            keyword = str(trade.date)

        # Make sure data requested exists
        trades = Trade.query.order_by(Trade.id.asc()).filter(and_(Trade.user_id == session["id"],
        Trade.date_time_open >= keyword.upper())).all()
        if not trades:
            return render_template("error.html", message="No such data.")
        else:
            labels = []
            for trade in trades:
                labels.append(trade.date)
            values = []
            calc = 0
            for trade in trades:
                calc += (trade.pnl-trade.commission)
                values.append(round(calc, 2))

            return render_template("charts.html", values=values, labels=labels, keyword=keyword)

    else:
        trade = Trade.query.get(838)
        keyword = str(trade.date)

        trades = Trade.query.order_by(Trade.id.asc()).filter(and_(Trade.user_id == session["id"],
                 Trade.date_time_open >= keyword.upper())).all()
        if not trades:
            return render_template("error.html", message="No such data.")
        else:
            labels = []
            for trade in trades:
                labels.append(trade.date)
            values = []
            calc = 0
            for trade in trades:
                calc += (trade.pnl-trade.commission)
                values.append(round(calc, 2))
            return render_template("charts.html", values=values, labels=labels, keyword=keyword)


@app.route("/notes", methods=["GET", "POST"])
def notes():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    return render_template("notes.html")


@app.route("/quote", methods=["GET", "POST"])
def quote():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    return render_template("quote.html")


@app.route("/convert", methods=["POST"])
def convert():

    # Query for currency exchange rate
    currency = request.form.get("currency")
    res = requests.get("https://api.fixer.io/latest", params={
        "base": "EUR", "symbols": currency})

    # Make sure request succeeded
    if res.status_code != 200:
        return jsonify({"success": False})

    # Make sure currency is in response
    data = res.json()
    if currency not in data["rates"]:
        return jsonify({"success": False})

    return jsonify({"success": True, "rate": data["rates"][currency]})


@app.route("/upload", methods=["GET", "POST"])
def upload():
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    # User reached route via POST (as by submitting a form via POST)
    # From http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash(u"No file part", "error")
            return redirect("upload")
        file = request.files["file"]
        # if user does not select file, browser also
        # submit a empty part without filename
        if file:
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], "trades.csv"))

            position = {}

            f = open("static/uploads/trades/trades.csv")
            reader = csv.reader(f)

            try:
                for ccy, direction, quantity, symbol, price, time, date, commission, syntax in reader:
                    if direction == "BOT":
                        trade = Trade(direction="long", ccy=ccy, symbol=symbol, order=1, quantity=int(quantity),
                                quantity_b=int(quantity), quantity_s=0, av_price_b=int(quantity) * float(price),
                                av_price_s=0, pnl=-int(quantity) * float(price), commission=float(commission),
                                date=date, time=time, date_time_open=date + " " + time,
                                date_time_close=date + " " + time, w_l=0, max_quantity=int(quantity), user_id=session["id"])

                        if trade.symbol not in position.keys():
                            position[trade.symbol] = trade

                        elif trade.symbol in position.keys():
                            position[trade.symbol].quantity +=  int(quantity)
                            position[trade.symbol].order += 1
                            position[trade.symbol].pnl += -int(quantity) * float(price)
                            position[trade.symbol].commission += float(commission)
                            position[trade.symbol].quantity_b +=  int(quantity)
                            position[trade.symbol].av_price_b += int(quantity) * float(price)
                            print(position)
                            if position[trade.symbol].max_quantity < position[trade.symbol].quantity:
                                position[trade.symbol].max_quantity = position[trade.symbol].quantity

                            if position[trade.symbol].quantity == 0:
                                position[trade.symbol].av_price_b /= position[trade.symbol].quantity_b
                                position[trade.symbol].av_price_s /= position[trade.symbol].quantity_s
                                position[trade.symbol].pnl = round(position[trade.symbol].pnl, 2)
                                position[trade.symbol].commission = round(position[trade.symbol].commission, 2)
                                position[trade.symbol].date_time_close = trade.date_time_close

                                if position[trade.symbol].pnl >= 0:
                                    position[trade.symbol].w_l = "w"
                                else:
                                    position[trade.symbol].w_l = "l"

                                db.session.add(position[trade.symbol])
                                del position[trade.symbol]

                    elif direction == "SLD":
                        trade = Trade(direction="short", ccy=ccy, symbol=symbol, order=1, quantity=-int(quantity),
                                quantity_b=0, quantity_s=int(quantity), av_price_b=0, av_price_s=int(quantity) * float(price),
                                pnl=int(quantity) * float(price), commission=float(commission),
                                date=date, time=time, date_time_open=date + " " + time,
                                date_time_close=date + " " + time, w_l=0, max_quantity=int(quantity), user_id=session["id"])

                        if trade.symbol not in position.keys():
                            position[trade.symbol] = trade

                        elif trade.symbol in position.keys():
                            position[trade.symbol].quantity += -int(quantity)
                            position[trade.symbol].order += 1
                            position[trade.symbol].pnl += int(quantity) * float(price)
                            position[trade.symbol].commission += float(commission)
                            position[trade.symbol].quantity_s +=  int(quantity)
                            position[trade.symbol].av_price_s += int(quantity) * float(price)
                            print(position)
                            if position[trade.symbol].max_quantity < abs(position[trade.symbol].quantity):
                                position[trade.symbol].max_quantity = abs(position[trade.symbol].quantity)

                            if position[trade.symbol].quantity == 0:
                                position[trade.symbol].av_price_b /= position[trade.symbol].quantity_b
                                position[trade.symbol].av_price_s /= position[trade.symbol].quantity_s
                                position[trade.symbol].pnl = round(position[trade.symbol].pnl, 2)
                                position[trade.symbol].commission = round(position[trade.symbol].commission, 2)
                                position[trade.symbol].date_time_close = trade.date_time_close

                                if position[trade.symbol].pnl >= 0:
                                    position[trade.symbol].w_l = "w"
                                else:
                                    position[trade.symbol].w_l = "l"

                                db.session.add(position[trade.symbol])
                                del position[trade.symbol]

                db.session.commit()
                flash("Trades imported")
                return redirect("upload")

            except:
                pass
                flash(u"Trades NOT imported", "error")
                return redirect("upload")



    # User reached route via GET (as by clicking a link or via redirect)# User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("upload.html")


@app.route("/trades/<int:id>", methods=["GET", "POST"])
def trade(id):
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")
    """List details about a single trade."""

    # Get all the trades from a user
    trades = Trade.query.order_by(Trade.id.asc()).filter(Trade.user_id == session["id"]).all()
    # Append all the trade ids to list_id
    list_id = []
    for trade in trades:
        list_id.append(trade.id)

    # Get the current position in list_id of the selected trades - id
    curr = list_id.index(id)
    # Get the next id in list_id
    try:
        nex = list_id[curr + 1]
    except:
        # if end of the list we go back to the first id in list_id
        nex = list_id[0]
    # Get the previous id in list_id
    try:
        prev = list_id[curr -1]
    except:
        # If first id in the list, previous one will be the last id in list_id
        prev = list_id[-1]

    # save selected trade
    trade = Trade.query.get(id)

    if trade is None:
        return render_template("error.html", message="No trades")

    if session["id"] == trade.user_id:

        if request.method == "POST" and request.form.get("comment") and request.form.get("rating"):
            trade.comment = request.form.get("comment")
            trade.rating = request.form.get("rating")

            db.session.commit()
            trade = Trade.query.get(id)
            flash("Comment & Rating updated for this trade")
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        if request.method == "POST" and request.form.get("comment") and not request.form.get("rating"):
            trade.comment = request.form.get("comment")

            db.session.commit()
            trade = Trade.query.get(id)
            flash("Comment updated for this trade")
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        if request.method == "POST" and request.form.get("rating") and not request.form.get("comment"):
            trade.rating = request.form.get("rating")

            db.session.commit()
            trade = Trade.query.get(id)
            flash("Rating updated for this trade")
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        if request.method == "POST" and not request.form.get("comment") and not request.form.get("rating") and request.form.get("stop"):
            stop = request.form.get("stop")
            trade.stop = float(stop)
            if trade.direction == "long":
                trade.r_r = round((trade.av_price_b-trade.av_price_s)/(float(stop)-trade.av_price_b), 2)
                trade.risk = round(trade.quantity_b * (trade.av_price_b - float(stop)), 2)
            else:
                trade.r_r = round((trade.av_price_s-trade.av_price_b)/(float(stop)-trade.av_price_s), 2)
                trade.risk = round(trade.quantity_s * (float(stop) - trade.av_price_s), 2)

            db.session.commit()
            flash("Stop updated")
            trade = Trade.query.get(id)
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        if request.method == "POST" and not request.form.get("comment") and not request.form.get("rating") and request.form.get("risk"):
            risk = request.form.get("risk")
            trade.risk = float(risk)
            if trade.direction == "long":
                trade.stop = round(trade.av_price_b - float(risk)/trade.quantity_b, 2)
                trade.r_r = round((trade.av_price_b-trade.av_price_s)/(trade.stop-trade.av_price_b), 2)
            else:
                trade.stop = round(trade.av_price_s + float(risk)/trade.quantity_s, 2)
                trade.r_r = round((trade.av_price_s-trade.av_price_b)/(trade.stop-trade.av_price_s), 2)

            db.session.commit()
            flash("Risk updated")
            trade = Trade.query.get(id)
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        if request.method == "POST" and not request.form.get("comment") and not request.form.get("rating") and not request.form.get("stop") and not "file" in request.files:
            flash(u"Nothing submited", "error")
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

        # From http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
        if request.method == "POST" and "file" in request.files:
            file = request.files["file"]
            filename = trade.symbol + "_" + str(trade.id) + ".PNG"
            file.save(os.path.join(app.config["UPLOAD_FOLDER_PIC"], filename))

            trade.picture = filename
            trade = Trade.query.get(id)
            db.session.commit()

            flash("Screenshot imported")
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)


        # User reached route via GET (as by clicking a link or via redirect)# User reached route via GET (as by clicking a link or via redirect)
        elif request.method == "GET":
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)

    else:
        return render_template("error.html", message="Cannot access this trade")


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete(id):
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")
    """List details about a single trade."""

    # Get all the trades from a user
    trades = Trade.query.order_by(Trade.id.asc()).filter(Trade.user_id == session["id"]).all()
    # Append all the trade ids to list_id
    list_id = []
    for trade in trades:
        list_id.append(trade.id)

    # Get the current position in list_id of the selected trades - id
    curr = list_id.index(id)
    # Get the next id in list_id
    try:
        nex = list_id[curr + 1]
    except:
        # if end of the list we go back to the first id in list_id
        nex = list_id[0]
    # Get the previous id in list_id
    try:
        prev = list_id[curr -1]
    except:
        # If first id in the list, previous one will be the last id in list_id
        prev = list_id[-1]

    trade = Trade.query.get(id)

    if session["id"] == trade.user_id:

        if request.method == "POST":
            trade.stop = None
            trade.risk = None
            trade.r_r = None
            db.session.commit()
            return render_template("trade.html", trade=trade, prev=prev, nex=nex)


        # User reached route via GET (as by clicking a link or via redirect)# User reached route via GET (as by clicking a link or via redirect)
        elif request.method == "GET":
            # Make sure trade exists.
            if trade is None:
                return render_template("error.html", message="No trades")
            else:
                return render_template("trade.html", trade=trade, prev=prev, nex=nex)

    else:
        return render_template("error.html", message="Cannot access this trade")


@app.route("/delete_trade/<int:id>", methods=["GET", "POST"])
def delete_trade(id):
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")
    """List details about a single trade."""
    # Get all the trades from a user
    trades = Trade.query.order_by(Trade.id.asc()).filter(Trade.user_id == session["id"]).all()
    # Append all the trade ids to list_id
    list_id = []
    for trade in trades:
        list_id.append(trade.id)

    # Get the current position in list_id of the selected trades - id
    curr = list_id.index(id)
    # Get the next id in list_id
    try:
        nex = list_id[curr + 1]
    except:
        # if end of the list we go back to the first id in list_id
        nex = list_id[0]
    # Get the previous id in list_id
    try:
        prev = list_id[curr -1]
    except:
        # If first id in the list, previous one will be the last id in list_id
        prev = list_id[-1]

    trade = Trade.query.get(id)

    if session["id"] == trade.user_id:

        if request.method == "POST":
            db.session.delete(trade)
            db.session.commit()
            return redirect("/")


        # User reached route via GET (as by clicking a link or via redirect)# User reached route via GET (as by clicking a link or via redirect)
        elif request.method == "GET":
            # Make sure trade exists.
            if trade is None:
                return render_template("error.html", message="No trades")
            else:
                return render_template("trade.html", trade=trade, prev=prev, nex=nex)

    else:
        return render_template("error.html", message="Cannot access this trade")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        # Query database for username
        user = User.query.filter_by(username=request.form.get("username")).first()

        # Ensure username exists and password is correct
        if not user or not check_password_hash(user.hash_p, request.form.get("password")):
            return render_template("error.html", message="invalid username/password")

        # Remember which user has logged in
        session["id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        # Ensure password was submitted
        if not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        # Ensure confirmation password was submitted
        if not request.form.get("confirmation"):
            return render_template("error.html", message="must confirm password")

        # Ensure passwords are matching
        if not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords dont match")

        # Store hashed password
        hash_p = generate_password_hash(request.form.get("password"))

        # Query database with all username


        # Insert username and password in database
        me = User(username=request.form.get("username"), hash_p=hash_p)
        db.session.add(me)
        db.session.commit()

        # Query database for username
        user = User.query.filter_by(username=request.form.get("username")).first()

        # Remember which user has logged in
        session["id"] = user.id

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """Reset password"""
    # Check if logged in, if not redirect to login page
    if not session.get("id"):
        return redirect("/login")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure new password was submitted
        if not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        # Ensure new password_check was submitted
        if not request.form.get("password_check"):
            return render_template("error.html", message="must confirm password")

        # Ensure passwords are matching
        if not request.form.get("password") == request.form.get("password_check"):
            return render_template("error.html", message="passwords don't match")

        # Store hashed password
        hash_p = generate_password_hash(request.form.get("password"))

        # Update password in database
        password = User.query.filter_by(id=session["id"]).first()
        password.hash_p = hash_p
        db.session.commit()

        flash("Password updated")

        # Redirect user to home page
        return redirect("/")

    # Redirect user to login form
    else:
        return render_template("reset.html")
