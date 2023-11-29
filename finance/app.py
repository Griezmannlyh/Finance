import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, time_now
import string

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Create new table, and index (for efficient search later on) to keep track of stock orders, by each user
db.execute("CREATE TABLE IF NOT EXISTS  transactions (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER, symbol TEXT NOT NULL,\
            shares NUMERIC NOT NULL, price NUMERIC NOT NULL, timestamp TEXT)")
db.execute("CREATE INDEX IF NOT EXISTS transactions_by_id_index ON transactions (user_id)")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
        # Stock, number of shares, current price, share times price, shares times price plus cash balance
    user_id = session["user_id"]
    # returns a list of dictionaries of the symbols
    Name = db.execute("SELECT DISTINCT(symbol) FROM transactions WHERE user_id = ?", user_id)
    Index_main = []
    Value_Total = []
    for each in Name:
        # calling symbol from the individual dictionaries in the list
        name = each['symbol']
        Shares = db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = ? AND user_id = ?", name, user_id )
        print("this is a share", Shares)
        Shares = int(Shares[0]["SUM(shares)"])
        print(Shares)
        Price = lookup(name)["price"]
        Shares_Value = Shares*Price
        # need to include[0] as db.execute returns a list of dictionary eg [{"cash": 10000},{}]
        Index = {}
        Index["name"] = lookup(name)["name"]
        Index["shares"] = Shares
        Index["shares_value"] = usd(Shares_Value)
        Index["price"] = usd(Price)
        Index_main.append(Index)
        Value_Total.append(Shares_Value)
        if Shares == 0:
           print("this has happened")
           Index_main.remove(Index)

    Cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id )[0]['cash'])
    Total_Cash = Cash + sum(Value_Total)


    return render_template("index.html", Index_main = Index_main, Cash = usd(Cash), Total_Cash = usd(Total_Cash))



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
       if not request.form.get("symbol"):
          return apology("must provide stock symbol",403)
       else:
          symbol = request.form.get("symbol")
       try:
         # Tagging dictionary from lookup() to a name so that keys can be accessed
         stock_data = lookup(symbol)
         stock_name = stock_data["name"]
         stock_price = stock_data["price"]

       except:
          return apology("Invalid stock symbol", 403)

       # Obtaining shares
       shares = request.form.get("shares")

      # Ensuring shares input is not blank
       if not request.form.get("shares"):
          return apology("must provide number of shares",403)

       # Ensuring shares input is positive
       elif int(shares) < 0:
          return apology("shares must be positive",403)

       # Ensuring shares input is an integer
       def integer(A):
        try:
           int(A)
        except ValueError:
           return apology("share must be an integer",403)

        integer(shares)

       user_id = session["user_id"]
       Cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash'])
       Cost = int(shares) * stock_price
       if Cash < Cost:
          return apology("Insufficient cash balance",403)
       else:
          New_Cash = Cash - Cost
       db.execute("UPDATE users SET cash = ? WHERE id = ?", New_Cash, user_id)
       db.execute("INSERT INTO transactions (user_id, symbol, shares, price, timestamp) VALUES (?, ?, ?, ?, ?)",\
                                      user_id, symbol, shares, usd(stock_price), time_now())

       flash("Bought!")

       return redirect("/")

# User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("shares.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    Transactions = db.execute("SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = ?", user_id)
    return render_template("history.html", Transactions = Transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
        # Once user provides stock quote
    if request.method == "POST":
       if not request.form.get("symbol"):
          return apology("must provide stock symbol",403)
       else:
          symbol = request.form.get("symbol")

       try:
         # Tagging dictionary from lookup() to a name so that keys can be accessed
         stock_data = lookup(symbol)
         stock_name = stock_data["name"]
         stock_price = usd(stock_data["price"])

       except:
          return apology("Invalid stock symbol", 403)

       return render_template("quoted.html", NAME = stock_name, PRICE = stock_price)
    else:
       return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
       return render_template("register.html")
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

    # Ensure username is not blank
    if not request.form.get("username"):
       return apology("must provide username", 403)

    # Ensure username does not already exist
    rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
    if len(rows) == 1:
       return apology("username already exists" , 403)

    # Ensure neither password nor confirmation is blank
    if not request.form.get("password"):
       return apology("must provide password", 403)

    elif not request.form.get("confirmation"):
       return apology("must get confirmation", 403)

    # Additional Feature, Require users’ passwords to have some number of letters, numbers, and/or symbols.
    if len(password) < 12:
       flash("Password must be at least 12 characters!")
       return redirect("/register")
    alphacount = 0
    numcount = 0
    symcount = 0
    for each in str(password):
       if each in [str(alphabet) for alphabet in str(string.ascii_letters)]:
          alphacount +=1
       elif each in [str(digit) for digit in str(string.digits)]:
          numcount +=1
       elif each in ["!","@","#","$","%","^","&","*","(",")"]:
          symcount +=1
    if alphacount < 3:
       flash("Password must have at least 3 letters!")
       return redirect("/register")
    elif numcount <1:
       flash("Password must have at least 1 number!")
       return redirect("/register")
    elif symcount <1:
       flash("Password must have at least 1 symbol!")
       return redirect("/register")



    # Ensure password = confirmation
    if str(password) != str(confirmation):
       return apology("passwords do not match", 403)

 # Hashing password and storing it in users table

    hashed = generate_password_hash(password)
    db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashed)

 # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = ?", username)
 # Log user in, i.e. Remember that this user has logged in
    session["user_id"] = rows[0]["id"]
    # Redirect user to home page
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock """
    if request.method == "POST":
       user_id = session["user_id"]
       if not request.form.get("symbol"):
          return apology("must provide symbol", 403)
       if not request.form.get("shares"):
          return apology("must provide shares", 403)
       elif int(request.form.get("shares")) < 0:
          return apology("shares must be positive",403)
       Symbol = request.form.get("symbol")
       Shares = int(request.form.get("shares"))
       Name = lookup(Symbol)["name"]
       Price = lookup(Symbol)["price"]

       try:
          User_shares = int(db.execute("SELECT SUM(shares) FROM transactions WHERE symbol = ? AND user_id = ?", Symbol, user_id )[0]["SUM(shares)"])
       except:
          return apology("You do not own this stock", 403)
       if User_shares == 0 or User_shares < Shares:
          return apology("insufficient shares", 403)

       def integer(A):
        try:
           int(A)
        except ValueError:
           return apology("share must be an integer",403)
        integer(Shares)
       Cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash'])
       Revenue = Shares * Price
       New_Cash = Cash + Revenue
       db.execute("UPDATE users SET cash = ? WHERE id = ?", New_Cash, user_id)
       db.execute("INSERT INTO transactions (user_id, symbol, shares, price, timestamp) VALUES (?, ?, ?, ?, ?)",\
                                      user_id, Symbol, -Shares, usd(Price), time_now())

       flash("Sold!")

       return redirect("/")

    else:
       return render_template("sell.html")
