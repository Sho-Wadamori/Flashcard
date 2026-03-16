# import libraries
from flask import (
    Flask,
    g,
    request,  # used to get method
    session,  # used to store user data
    redirect,  # used to redirect users to another page
    render_template,  # used to render html pages
    url_for,  # used to redirect users
    flash  # used for error messages (NOT SETUP YET)
)

# from werkzeug.utils import secure_filename  # for file uploads
from datetime import (
    datetime,
    timezone
)  # for time formatting

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)  # for user login password encryption

import sqlite3

DATABASE = 'database.db'  # relative path to the database file

# initialise app
app = Flask(__name__)

# set a secret key for sessions
app.config['SECRET_KEY'] = "8y9awhDWdhHfw8ghgrgdgGRgDEgwndaiundIUDNu1823892e8h"


# connect to the database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# automatically close the database connection at the end of each request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# simplify database queries
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# conveting YYYY-MM-DD HH:MM:SS to x minutes/hours/days ago
def time_ago(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)

    # convert to local zone
    local_dt = dt.astimezone()
    now = datetime.now().astimezone()  # local now

    diff = now - local_dt

    if diff.days > 0:
        return f"{diff.days} days ago"

    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hours ago"

    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minutes ago"

    return "just now"


# conveting YYYY-MM-DD HH:MM:SS to DD/Month/YYYY
def format_date(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)

    # convert to local time
    local_dt = dt.astimezone()  # system local zone
    return local_dt.strftime("%d/%b/%Y")


# get user ID from session username
def userID():
    return session.get('userID', 0)


# make username and userID available in all templates
@app.context_processor
def uservar():
    return {
        "username": session.get("username", "Guest"),
        "userID": session.get("userID", 0)
    }


# homepage
@app.route('/')
def home():
    return render_template(
        "homepage.html", username=session.get(
            'username', 'Guest'
        ),
        userID=session.get('userID', 0)
    )


# list all decks
@app.route('/decks/')
def Decks():
    # get all the decks id, name, description, and creation date
    sql = """
            SELECT deck_ID, deck_name, deck_description, deck_creation
            FROM Decks
            Where deck_userID = ?;
        """
    result = query_db(sql, (userID(),))
    # return the results
    return render_template("decks.html", results=result)


# list all flashcards for a single deck
@app.route('/decks/<int:id>/')
def Deck(id):
    # get all the card id, Q, A, and creation date for inputted deck id
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ? AND card_userID = ?;
        """
    # get the deck name of the inputted deck id
    sql_deck = """
                SELECT deck_name, deck_ID, deck_creation
                FROM Decks
                WHERE deck_ID = ?
                AND deck_userID = ?;
            """

    deck_info = query_db(sql_deck, (id, userID()), True)
    results = query_db(sql, (id, userID()))
    # return the results
    return render_template(
        "deck.html",
        results=results,
        deck_info=deck_info,
        time_ago=time_ago,
        format_date=format_date
    )


@app.route('/decks/<int:id>/cards/<int:card_id>/delete/', methods=['POST'])
def deleteCard(id, card_id):
    # delete the card with the inputted card id
    sql = """
            DELETE FROM Flashcards
            WHERE card_ID = ?
            AND card_userID = ?;
        """
    get_db().execute(sql, (card_id, userID()))
    get_db().commit()
    # redirect to the deck page
    return redirect(url_for('Deck', id=id))


@app.route('/decks/<int:id>/delete/', methods=['POST'])
def deleteDeck(id):
    # delete the deck with the inputted deck id
    sql = """
            DELETE FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    get_db().execute(sql, (id, userID()))
    get_db().commit()
    # redirect to the deck page
    return redirect(url_for('Decks'))


# study a single card based on the index
@app.route('/decks/<int:id>/study/<int:index>/')
def Study(id, index):
    # get all the card id, Q, A, and creation date for inputted deck id
    sql = """
            SELECT card_ID, card_question,
            card_answer, card_creation, card_hint
            FROM Flashcards
            WHERE card_deckID = ? AND card_userID = ?;
        """
    results = query_db(sql, (id, userID()))

    total = len(results)  # total number of cards in the deck

    card = results[index]  # get the current card info based on the index

    return render_template(
        "card.html",
        cards=card,
        deck_id=id,
        total=total,
        index=index
        )


# create a new deck and add it to the database
@app.route('/decks/create/', methods=['GET', 'POST'])
def createDeck():
    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']

        # check if the form data is not empty
        if not deck_name:
            # reload the page with the error message
            error = "A deck name is required."
            flash("A deck name is required.")
            return render_template("deckCreate.html", error=error)

        else:
            sql = """
                    INSERT INTO Decks (
                    deck_name, deck_description, deck_creation, deck_userID
                    )
                    VALUES (?, ?, datetime('now'), ?);
                """
            get_db().execute(sql, (deck_name, deck_description, userID()))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks
                WHERE deck_userID = ?;
            """
        result = query_db(sql, (userID(),))
        # return the results
        return render_template("deckCreate.html", results=result)


# create a new card for a specific deck and add it to the database
@app.route('/decks/<int:id>/create/', methods=['GET', 'POST'])
def createCard(id):

    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    deck_info = query_db(sql_deck, (id, userID()))

    # check if deck_info is not empty
    if not deck_info:
        error = "No deck was found..."
        flash("No deck was found...")
        return redirect(url_for("Decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            error = "Both fields are required."
            flash("Both fields are required.")
            return render_template(
                "cardCreate.html",
                error=error,
                deck_info=deck_info[0]
            )

        else:
            sql = """
                    INSERT INTO Flashcards (
                    card_question, card_answer, card_deckID,
                    card_creation, card_hint, card_userID
                    )
                    VALUES (?, ?, ?, datetime('now'), ?, ?);
                """

            get_db().execute(sql, (
                card_question,
                card_answer,
                id,
                card_hint,
                userID()
            ))
            get_db().commit()
            # redirect to the deck page
            return redirect(url_for('Deck', id=id))

    # if request method is GET, return the sql results
    else:

        # return deckinfo
        return render_template("cardCreate.html", deck_info=deck_info)


# edit a deck and update the database
@app.route('/decks/<int:id>/edit/', methods=['GET', 'POST'])
def editDeck(id):
    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']

        # check if the form data is not empty
        if not deck_name:
            # reload the page with the error message
            error = "A deck name is required."
            flash("A deck name is required.")
            return render_template("deck.html", error=error, id=id)

        else:
            sql = """
                    UPDATE Decks
                    SET deck_name = ?, deck_description = ?
                    WHERE deck_ID = ?
                    AND deck_userID = ?;
                """
            get_db().execute(sql, (deck_name, deck_description, id, userID()))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks
                WHERE deck_ID = ? AND deck_userID = ?;
            """
        result = query_db(sql, (id, userID()))

        if not result:
            error = "Invalid deck..."
            flash("Invalid deck...")
            return redirect(url_for("Decks"))

        # return the results
        return render_template("deckEdit.html", results=result)


# edit a card and update the database
@app.route(
    '/decks/<int:id>/cards/<int:card_id>/edit/',
    methods=['GET', 'POST']
)
def editCard(id, card_id):
    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    deck_info = query_db(sql_deck, (id, userID()))

    # check if deckinfo is not empty
    if not deck_info:
        error = "Invalid deck..."
        flash("Invalid deck...")
        return redirect(url_for("Decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            error = "Both fields are required."
            flash("Both fields are required.")
            sql_card = """
                SELECT card_ID, card_question,
                card_answer, card_creation, card_hint
                FROM Flashcards
                WHERE card_ID = ?
                AND card_userID = ?;
            """
            card = query_db(sql_card, (card_id, userID()), one=True)
            return render_template(
                "cardEdit.html",
                error=error,
                deck_info=deck_info[0],
                cards=card
            )

        # if form data is present in both
        else:
            sql = """
                    UPDATE Flashcards
                    SET card_question = ?, card_answer = ?, card_hint = ?
                    WHERE card_ID = ? AND card_deckID = ?
                    AND card_userID = ?;
                """

            get_db().execute(sql, (
                card_question,
                card_answer,
                card_hint,
                card_id,
                id,
                userID()
            ))
            get_db().commit()
            # redirect to the deck page
            return redirect(url_for('Deck', id=id))

    # if request method is GET, return the sql results
    else:

        # return cardinfo
        sql_card = """
            SELECT card_ID, card_question,
            card_answer, card_creation, card_hint
            FROM Flashcards
            WHERE card_ID = ?
            AND card_userID = ?;
        """
        card = query_db(sql_card, (card_id, userID()), one=True)

        # check if card is not empty
        if not card:
            error = "Invalid Card..."
            flash("Invalid Card...")
            return redirect(url_for('Deck', id=id))

        return render_template(
            "cardEdit.html",
            deck_info=deck_info[0],
            cards=card
        )


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        # get the form data
        username = request.form['username']
        password = request.form['password']

        # get usernames in the database
        sql = """
                SELECT user_name, user_password
                FROM Users
                WHERE user_name = ?;
            """
        username_list = query_db(sql, (username,))

        # check if the username and password are not empty
        if not username or not password:
            error = "Both fields are required."
            flash("Both fields are required.")
            return render_template("login.html", error=error)

        elif not username_list:
            # reload the page with the error message
            error = "No account under the username " + username + "."
            flash("No account under the username " + username + ".")
            return render_template("login.html", error=error)

        elif username_list[0][0] == username:
            # check if the password is correct
            if check_password_hash(username_list[0][1], password):
                # logged in successfully, redirect to homepage
                session['username'] = username
                session['userID'] = query_db(
                    "SELECT user_ID FROM Users WHERE user_name = ?",
                    (username,), one=True
                )[0]
                return redirect(url_for('home'))
            else:
                error = "Incorrect password."
                flash("Incorrect password.")
                return render_template("login.html", error=error)
        else:
            error = "Something Went Wrong..."
            return render_template("login.html", error=error)

    else:
        return render_template("login.html")


@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        # get the form data
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        sql = """
                SELECT user_name
                FROM Users
                WHERE user_name = ?;
            """
        username_list = query_db(sql, (username,))

        # check if the username and password are not empty
        if not username or not password or not confirm_password:
            error = "All fields are required."
            flash("All fields are required.")
            return render_template("signup.html", error=error)

        elif confirm_password != password:
            error = "Passwords do not match."
            flash("Passwords do not match.")
            return render_template("signup.html", error=error)

        # check if the username already exists in the database
        elif username_list:
            error = "Username already exists."
            flash("Username already exists.")
            return render_template("signup.html", error=error)

        else:
            hashed_password = generate_password_hash(password)
            sql = """
                    INSERT INTO Users (user_name, user_password, user_creation)
                    VALUES (?, ?, datetime('now'));
                """
            get_db().execute(sql, (username, hashed_password))
            get_db().commit()
            error = "Account created successfully. Please log in."
            flash("Account created successfully. Please log in.")
            return render_template("login.html", error=error)

    else:
        return render_template("signup.html")


@app.route('/profile/')
def profile():
    if not userID():
        flash("You are not logged in.")
        return redirect(url_for('logout'))

    sql = """
            SELECT user_name, user_creation
            FROM Users
            WHERE user_ID = ?;
        """

    results = query_db(sql, (userID(),))

    if not results:
        flash("User details not found. Logging out.")
        return redirect(url_for('logout'))

    # return the results
    return render_template(
        "profile.html",
        results=results[0],
        format_date=format_date,
        time_ago=time_ago
    )


@app.route('/logout/')
def logout():
    session.pop('username', None)
    session.pop('userID', None)
    flash("Logged out successfully.")
    return redirect(url_for('home'))


# only run the app if app.py is executed directly
if __name__ == "__main__":
    app.run(debug=True)
