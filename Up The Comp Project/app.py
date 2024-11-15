import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from functools import wraps

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Decorate routes to require login.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/welcome")
        return f(*args, **kwargs)
    return decorated_function


# Return error codes
def errorcode(message, code=400):

    return render_template("errorcode.html", message=message), code


# Initial visit to site
@app.route("/welcome", methods=["GET"])
def welcome():

    # Display page
    return render_template("welcome.html")


# Home page
@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # User reached route via POST
    if request.method == "POST":

        # Store current user's username in variable
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # Get game value from Remove button
        if request.form.get("remove"):
            game = request.form.get("remove")

        # Remove game from user's games table in database
        db.execute("DELETE FROM games WHERE game = ?", game)

        # Redirect user back to home page
        return redirect("/")

    # User reached route via GET
    else:

        # Grab username of current user from database
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # Grab games data for current user from database
        games = db.execute("SELECT game FROM games WHERE games_username = ?", username)

        return render_template("index.html", games=games)


# Log user in
@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return errorcode("a username was not submitted")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return errorcode("a password was not submitted")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return errorcode("your username or password is incorrect")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("login.html")


# Register new users
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return errorcode("a username was not submitted")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return errorcode("a password was not submitted")

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return errorcode("no password confirmation was submitted")

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return errorcode("the passwords provided do not match")

        # Ensure username doesn't already exist
        usernames = db.execute("SELECT username FROM users")
        for entries in usernames:
            if request.form.get("username") == entries["username"]:
                return errorcode("username already exists. Please provide another one.")

        # Hash new user's password
        hash = generate_password_hash(request.form.get("password"))

        # Insert new user's username and hashed password into database
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", request.form.get("username"), hash)

        # Redirect user to login page
        return redirect("/login")

    # User reached route via GET
    else:
        return render_template("register.html")


# Log user out
@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to index
    return redirect("/")


# Display list of games available to add
@app.route("/games", methods=["GET", "POST"])
@login_required
def games():
    # User reached route via POST
    if request.method == "POST":

        # Store current user's username in variable
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # Get game value from Add button on games page
        if request.form.get("game"):
            game = request.form.get("game")

            # Look at existing game data in games table and ensure game has not already been added to home page
            db_game = db.execute("SELECT game FROM games WHERE games_username = ?", username)
            for entries in db_game:
                for entry in entries:
                    if entries[entry] == game:
                        return errorcode("the game you have selected is already added to your home page")

            # If game is not already in database, add game to home page
            db.execute("INSERT INTO games (games_username, game) VALUES (?, ?)", username, game)

        # Redirect user back to the home page
        return redirect("/")

    # User reached route via GET
    else:
        return render_template("games.html")


# Display boards for selected game
@app.route("/boards", methods=["POST"])
@login_required
def boards():

    # Store current user's username in variable
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Get game value from View Board button on home page
    if request.form.get("game"):
        game = request.form.get("game")

        # Get all posts from database
        posts = db.execute("SELECT * FROM posts WHERE posts_game = ?", game)

        # Display posts
        return render_template("boards.html", username=username, game=game, posts=posts)

    # Get game and description values from Remove button on boards
    if request.form.get("remove"):

        description = request.form.get("remove")

        game = db.execute("SELECT posts_game FROM posts WHERE description = ?", description)
        game = game[0]["posts_game"]

        # Remove post from database
        db.execute("DELETE FROM posts WHERE description = ?", description)

        # Get all posts from database
        posts = db.execute("SELECT * FROM posts WHERE posts_game = ?", game)

        # Display posts
        return render_template("boards.html", username=username, game=game, posts=posts)


# Create a post for discussion board
@app.route("/createpost", methods=["POST"])
@login_required
def createpost():

    # Get game value from create post button on boards page
    game = request.form.get("createpost")

    return render_template("createpost.html", game=game)


# Write data into posts database after creating post and displaying boards for new post
@app.route("/createdpost", methods=["POST"])
@login_required
def createdpost():

    # Ensure description was submitted
    if not request.form.get("description"):
        return errorcode("a description was not submitted")

    # Ensure number of players needed was submitted
    elif not request.form.get("players"):
        return errorcode("no number of players was submitted")

    # Store current user's username in variable
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Grab description from form and add to posts table in database
    description = request.form.get("description")

    # Grab rank from account settings if chosen to be displayed and add to posts table in database
    if request.form.get("rank") == "Yes":
        db.game = request.form.get("boardpost")
        rank = db.execute("SELECT ranks_rank FROM ranks WHERE ranks_game = ? AND ranks_username = ?", db.game, username)
        
        if rank != []:
            rank = rank[0]["ranks_rank"]
        else:
            rank = "N/A"

    else:
        rank = "N/A"

    # Grab number of players from form and add to posts table in database
    players = request.form.get("players")

    # Grab current date and time
    current_datetime = datetime.datetime.now()
    month = current_datetime.month
    day = current_datetime.day
    year = current_datetime.year
    hour = current_datetime.hour
    minutes = current_datetime.minute

    # Get game value from post to board button on create post page
    posts_game = request.form.get("boardpost")

    # Add post to database
    db.execute("INSERT INTO posts (posts_username, description, rank, players, month, day, year, hour, minutes, posts_game) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", username, description, rank, players, month, day, year, hour, minutes, posts_game)

    # Create game variable for boards.html display
    game = posts_game

    # Get all posts from database
    posts = db.execute("SELECT * FROM posts WHERE posts_game = ?", posts_game)

    return render_template("boards.html", username=username, game=game, posts=posts)


# Account settings
@app.route("/settings", methods=["GET"])
@login_required
def settings():

    # Store current user's username in variable
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Grab user data for current user from database
    userinfo = db.execute("SELECT * FROM users WHERE username = ?", username)

    # Grab ranks data for current user from database
    ranks = db.execute("SELECT * FROM ranks WHERE ranks_username = ?", username)

    return render_template("settings.html", username=username, userinfo=userinfo, ranks=ranks)


# Change account settings
@app.route("/changesettings", methods=["GET", "POST"])
@login_required
def changesettings():

    # User reached route via POST
    if request.method == "POST":

        # Store current user's username in variable
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # Update name in users table if one is provided
        if request.form.get("name"):
            name = request.form.get("name")
            db.execute("UPDATE users SET name = ? WHERE username = ?", name, username)

        # Update bio in users table if one is provided
        if request.form.get("bio"):
            bio = request.form.get("bio")
            db.execute("UPDATE users SET bio = ? WHERE username = ?", bio, username)

        # Update achievements in users table if one is provided
        if request.form.get("achievements"):
            achievements = request.form.get("achievements")
            db.execute("UPDATE users SET achievements = ? WHERE username = ?", achievements, username)

        # Update setup in users table if one is provided
        if request.form.get("setup"):
            setup = request.form.get("setup")
            db.execute("UPDATE users SET setup = ? WHERE username = ?", setup, username)

        # Check if game was provided
        if request.form.get("gameselect") != "Choose...":

            # Look at existing data in ranks table and check if game has already been added under that user, and if so, update information
            game = request.form.get("gameselect")
            db_game = db.execute("SELECT ranks_game FROM ranks WHERE ranks_username = ?", username)
            for entries in db_game:
                for entry in entries:
                    if entries[entry] == game:
                        rank = request.form.get("rank")
                        db.execute("UPDATE ranks SET ranks_rank = ? WHERE ranks_game = ?", rank, game)
                        return redirect("/settings")

            # Otherwise insert that information into a new row in ranks table
            rank = request.form.get("rank")
            db.execute("INSERT INTO ranks (ranks_username, ranks_game, ranks_rank) VALUES (?, ?, ?)", username, game, rank)

        # Redirect user back to settings page
        return redirect("/settings")

    # User reached route via GET
    else:

        return render_template("changesettings.html")


# Reset account settings
@app.route("/resetinfo", methods=["GET"])
@login_required
def resetinfo():

    # Store current user's username in variable
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Reset user information data in users table and ranks data from ranks table for that user
    db.execute("UPDATE users SET name = ? WHERE username = ?", "", username)
    db.execute("UPDATE users SET bio = ? WHERE username = ?", "", username)
    db.execute("UPDATE users SET achievements = ? WHERE username = ?", "", username)
    db.execute("UPDATE users SET setup = ? WHERE username = ?", "", username)
    db.execute("DELETE FROM ranks WHERE ranks_username = ?", username)

    return redirect("/settings")


# Change user's password
@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def change_password():

    # User reached route via POST
    if request.method == "POST":

        # Ensure old password was submitted
        if not request.form.get("oldpassword"):
            return errorcode("a previous password was not provided")

        # Ensure new password was submitted
        elif not request.form.get("newpassword"):
            return errorcode("a new password was not provided")

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return errorcode("a new password confirmation was not provided")

        # Query database for username and hashed password
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]
        oldpassword = db.execute("SELECT password FROM users WHERE username = ?", username)
        oldpassword = oldpassword[0]["password"]

        # Ensure old password is correct
        if not check_password_hash(oldpassword, request.form.get("oldpassword")):
            return errorcode("the previous password submitted doesn't match your current password")

        # Ensure new password and confirmation match
        elif request.form.get("newpassword") != request.form.get("confirmation"):
            return errorcode("the new password and confirmation provided do not match")

        # Hash new user's password
        newpassword = generate_password_hash(request.form.get("newpassword"))

        # Insert new user's hashed password into database
        db.execute("UPDATE users SET password = ? WHERE username = ?", newpassword, username)

        # Force user logout
        return redirect("/logout")

    # User reached route via GET
    else:

        return render_template("changepassword.html")


# Send a message to another user
@app.route("/sendmessage", methods=["GET", "POST"])
@login_required
def sendmessage():

    # Store current user's username in variable
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # User reached route via POST
    if request.method == "POST":

        # If messaging a user through discussion board, grab poster's username
        if request.form.get("messageuser"):

            receiving = request.form.get("messageuser")
            sending = username

            # Display the send message template
            return render_template("sendmessage.html", receiving=receiving, sending=sending)

        # After message is sent
        else:

            if not request.form.get("receiver"):

                return errorcode("a username was not specified for your message to be sent to")

            if request.form.get("receiver") == username:

                return errorcode("you tried to send a message to yourself, which is not allowed")

            receiver = request.form.get("receiver")
            sender = username
            message = request.form.get("message")

            print(receiver, sender, message)

            db.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", sender, receiver, message)

            # Redirect user to their messages page
            return redirect("/messages")

    # User reached route via GET
    else:

        return render_template("sendmessage.html")


# Display messages user has sent and read
@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():

    # User reached route via POST
    if request.method == "POST":

        # Store current user's username in variable
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # If message was removed by receiver
        if request.form.get("receiverremove"):

            message = request.form.get("receiverremove")
            db.execute("UPDATE messages SET receiverremoved = 1 WHERE message = ?", message)

        # If message was removed by sender
        if request.form.get("senderremove"):

            message = request.form.get("senderremove")
            db.execute("UPDATE messages SET senderremoved = 1 WHERE message = ?", message)

        # If message has been removed on both ends by sender and receiver, then delete message in database
        db.execute("DELETE FROM messages WHERE receiverremoved = 1 AND senderremoved = 1")

        # Redirect user back to their messages
        return redirect("/messages")


    # User reached route via GET
    else:

        # Grab username of current user from database
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]

        # Grab message data for current user from database
        sentmessages = db.execute("SELECT * FROM messages WHERE sender = ?", username)
        receivedmessages = db.execute("SELECT * FROM messages WHERE receiver = ?", username)

        return render_template("messages.html", sentmessages=sentmessages, receivedmessages=receivedmessages)


# Display user's profile
@app.route("/profile", methods=["POST"])
@login_required
def profile():

    # Store chosen user's username in variable
    username = request.form.get("profileuser")

    # Grab user data for current user from database
    userinfo = db.execute("SELECT * FROM users WHERE username = ?", username)

    # Grab ranks data for current user from database
    ranks = db.execute("SELECT * FROM ranks WHERE ranks_username = ?", username)

    return render_template("profile.html", username=username, userinfo=userinfo, ranks=ranks)


# Search for different game boards
@app.route("/search", methods=["POST"])
@login_required
def search():

    # Grab username of current user from database
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Get game value from Add button on games page
    if not request.form.get("search"):

        return errorcode("no search text was submitted")

    search = request.form.get("search")

    # Search for game in games database
    searches = db.execute("SELECT * FROM searchgames WHERE games LIKE ?", "%" + search + "%")

    # Redirect user back to the home page
    return render_template("search.html", searches=searches)


# Display create team form
@app.route("/createteam", methods=["GET", "POST"])
@login_required
def createteam():

    # Grab username of current user from database
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # User reached route via POST
    if request.method == "POST":

        # Ensure a team name was submitted
        if not request.form.get("teamname"):

            return errorcode("a team name was not submitted")

        # Ensure team name does not already exist
        namecheck = db.execute("SELECT name FROM teams WHERE name = ?", request.form.get("teamname"))

        for entry in namecheck:
            if entry.name == request.form.get("teamname"):
                return errorcode("team name is already being used")

        name = request.form.get("teamname")
        description = request.form.get("teamdescription")

        db.execute("INSERT INTO teams (name, description, owner) VALUES (?, ?, ?)", name, description, username)

        invites = request.form.get("invites")
        invites = int(invites)

        if invites > 0:

            return render_template("invitemembers.html", name=name, invites=invites)

        else:

            return redirect("/teams")

    # User reached route via GET
    else:

        return render_template("createteam.html")


# Invite members to team
@app.route("/invitemembers", methods=["GET", "POST"])
@login_required
def invitemembers():

    # Grab username of current user from database
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # User reached route via POST
    if request.method == "POST":

        teamname = request.form.get("submitmembers")

        userinvites = request.form.getlist("membername")

        invited = db.execute("SELECT receiver FROM invites WHERE team_name = ?", teamname)
        members = db.execute("SELECT member FROM members WHERE team_name = ?", teamname)

        for user in userinvites:

            for values in invited:

                if values["receiver"] == user:
                    return errorcode("that user has already been invited to this team")

            for values in members:

                if values["member"] == user:
                    return errorcode("that user is already on this team")

            if user != "":

                db.execute("INSERT INTO invites (team_name, sender, receiver) VALUES (?, ?, ?)", teamname, username, user)

        return redirect("/teams")

    # User reached route via GET
    else:

        invites = 1
        name = request.args.get("inviteuser")

        return render_template("invitemembers.html", name=name, invites=invites)


# Display existing teams
@app.route("/teams", methods=["GET"])
@login_required
def teams():

    # Grab username of current user from database
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # Get all teams information from database
    teams = db.execute("SELECT * FROM teams")

    members = db.execute("SELECT * FROM members")

    # Load teams.html template
    return render_template("teams.html", username=username, teams=teams, members=members)


# Display team invites received
@app.route("/teaminvites", methods=["GET", "POST"])
@login_required
def teaminvites():

    # Grab username of current user from database
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    username = username[0]["username"]

    # User reached route via POST
    if request.method == "POST":

        if request.form.get("acceptinvite"):

            teamname = request.form.get("acceptinvite")
            db.execute("INSERT INTO members (team_name, member) VALUES (?, ?)", teamname, username)
            db.execute("DELETE FROM invites WHERE receiver = ? AND team_name = ?", username, teamname)

        if request.form.get("rejectinvite"):

            teamname = request.form.get("rejectinvite")
            db.execute("DELETE FROM invites WHERE receiver = ? AND team_name = ?", username, teamname)

        return redirect("/teams")

    # User reached route via GET
    else:

        invites = db.execute("SELECT * FROM invites WHERE receiver = ?", username)

        return render_template("teaminvites.html", invites=invites)


# Remove members from teams
@app.route("/removemembers", methods=["GET", "POST"])
@login_required
def removemembers():

    # User reached route via POST
    if request.method == "POST":

        if request.form.get("memberselect") != "Choose...":

            teamname = request.form.get("removeteammember")
            member = request.form.get("memberselect")
            db.execute("DELETE FROM members WHERE team_name = ? AND member = ?", teamname, member)

            return redirect("/teams")

        else:

            return errorcode("no member was chosen to remove")

    # User reached route via GET
    else:

        if request.args.get("removeuser"):

            teamname = request.args.get("removeuser")
            members = db.execute("SELECT * FROM members WHERE team_name = ?", teamname)

            return render_template("removemembers.html", teamname=teamname, members=members)

        else:

            return errorcode("no team was selected to remove users from")


# Delete team
@app.route("/deleteteam", methods=["GET", "POST"])
@login_required
def deleteteam():

    # User reached route via POST
    if request.method == "POST":

        if request.form.get("yes"):

            teamname = request.form.get("yes")

            db.execute("DELETE FROM teams WHERE name = ?", teamname)
            db.execute("DELETE FROM members WHERE team_name = ?", teamname)
            db.execute("DELETE FROM invites WHERE team_name = ?", teamname)

            return redirect("/teams")

        else:

            return redirect("/teams")

    # User reached route via GET
    else:

        teamname = request.args.get("deleteteam")

        return render_template("deleteteam.html", teamname=teamname)
