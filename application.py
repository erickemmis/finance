from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():

    #get current stock values
    #update current stock prices

    #pull current portfolio
    rows = db.execute("SELECT cash FROM users WHERE id = :current_user_id", current_user_id = session["user_id"])
    current_money = rows[0]["cash"]
    #clear list
    del rows[:]
    #get each stock that have greater than 0 multiply by current price
    rows = db.execute("SELECT symbol, SUM(num_shares) AS total_shares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares != 0", user_id = session["user_id"])


    # get current price and name for each stock
    data = rows[:]
    total_value = current_money
    for count, row in enumerate(rows):
        stock_info = lookup(row["symbol"])
        #if not(stock_info):
        #    return apology("")

        data[count].update(stock_info)
        data[count]["value"] = stock_info["price"] * row["total_shares"]
        total_value += data[count]["value"]


    return render_template("index.html", net_worth = total_value, cash = current_money)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""

    if request.method == "GET":
        return render_template("buy.html")
    else:
        #validate symbol against yahoo
        symbol_name = request.form.get('symbol')
        request_shares = int(request.form.get('num_shares'))
        data = lookup(symbol_name)
        if data and request_shares > 0:
            #be sure user has enough money
            rows = db.execute("SELECT cash FROM users WHERE id = :current_user_id", current_user_id = session["user_id"])
            current_money = rows[0]["cash"]
            total_cost = data["price"] * request_shares

            #if cash is enough continue else redirect
            if total_cost > current_money:
                return apology("You dont have enough money :(")
            else:
                #if symbol is not currently in stocks add along with current price and business name
                result = db.execute("SELECT * FROM stocks WHERE symbol = :symbol", symbol=data["symbol"])
                if not result:
                    db.execute("INSERT INTO stocks (symbol, business_name, current_price) VALUES(:symbol, :business_name, :current_price)",
                                symbol = data["symbol"],
                                business_name = data["name"],
                                current_price = data["price"]
                                )


                #add transaction to table
                db.execute("INSERT INTO transactions (user_id, symbol, num_shares, bought_price) VALUES(:user_id, :symbol, :num_shares, :price)",
                            user_id = session["user_id"],
                            symbol = data["symbol"],
                            num_shares = request_shares,
                            price = data["price"]
                            )

                #update user cash
                db.execute("UPDATE users SET cash = :user_cash WHERE id = :user_id",
                            user_cash = current_money - total_cost,
                            user_id = session["user_id"]
                            )


            return redirect(url_for("index"))
        else:
            return apology("must enter a valid stock symbol and valid number of shares to buy")


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    return apology("TODO")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        return render_template("quote.html")
    else:
        if not request.form.get("symbol"):
            return apology("must enter a stock symbol")

        symbol_name = request.form.get('symbol')
        data = lookup(symbol_name)
        if data:
            return render_template("qouted.html", symbol = data["symbol"], name = data["name"], price = data["price"])
        else:
            return apology("must enter a valid stock symbol")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        #ensure password confirm attempted
        elif not request.form.get("password_check"):
            return apology("must confirm password")
        #ensure password is confirmed
        elif not request.form.get("password") == request.form.get("password_check"):
            return apology("passwords must match")

        #hash password
        hash_pwd = pwd_context.hash(request.form.get("password"))

        #check is username exists
        result = db.execute("SELECT username FROM users WHERE username = :username", username = request.form.get("username"))
        if result:
            return apology("username already exists")

        #insert into database
        db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash_pwd)", username = request.form.get("username"), hash_pwd = hash_pwd)

        #get user id from database
        data = db.execute("SELECT id FROM users WHERE username = :username", username=request.form.get("username"))

        #login new user
        session["user_id"] = data[0]["id"]

        #redirect to user homepage
        return redirect(url_for("index"))


    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "GET":
        return render_template("sell.html")


