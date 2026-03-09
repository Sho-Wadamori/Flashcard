# import libraries
from flask import Flask, g, redirect, render_template, request, url_for
# from werkzeug.utils import secure_filename  # for file uploads
from datetime import datetime, timezone  # for time formatting
import sqlite3

DATABASE = 'database.db'  # relative path to the database file

# initialise app
app = Flask(__name__)


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


# homepage
@app.route('/')
def home():
    return render_template("homepage.html")


# list all decks
@app.route('/decks/')
def Decks():
    # get all the decks id, name, description, and creation date
    sql = """
            SELECT deck_ID, deck_name, deck_description, deck_creation
            FROM Decks;
        """
    result = query_db(sql)
    # return the results
    return render_template("decks.html", results=result)


# list all flashcards for a single deck
@app.route('/decks/<int:id>/')
def Deck(id):
    # get all the card id, question, answer, and creation date for inputted deck id
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    # get the deck name of the inputted deck id
    sql_deck = """
                SELECT deck_name, deck_ID, deck_creation FROM Decks WHERE deck_ID = ?;
            """

    deck_info = query_db(sql_deck, (id,), True)
    results = query_db(sql, (id,))
    # return the results
    return render_template("deck.html", results=results, deck_info=deck_info, time_ago=time_ago, format_date=format_date)


@app.route('/decks/<int:id>/cards/<int:card_id>/delete/', methods=['POST'])
def deleteCard(id, card_id):
    # delete the card with the inputted card id
    sql = """
            DELETE FROM Flashcards WHERE card_ID = ?;
        """
    get_db().execute(sql, (card_id,))
    get_db().commit()
    # redirect to the deck page
    return redirect(url_for('Deck', id=id))


@app.route('/decks/<int:id>/delete/', methods=['POST'])
def deleteDeck(id):
    # delete the deck with the inputted deck id
    sql = """
            DELETE FROM Decks WHERE deck_ID = ?;
        """
    get_db().execute(sql, (id,))
    get_db().commit()
    # redirect to the deck page
    return redirect(url_for('Decks'))


# study a single card based on the index
@app.route('/decks/<int:id>/study/<int:index>/')
def Study(id, index):
    # get all the card id, question, answer, and creation date for inputted deck id
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation, card_hint
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    results = query_db(sql, (id,))

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
            return render_template("deckCreate.html", error=error)

        else:
            sql = """
                    INSERT INTO Decks (deck_name, deck_description, deck_creation)
                    VALUES (?, ?, datetime('now'));
                """
            get_db().execute(sql, (deck_name, deck_description))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks;
            """
        result = query_db(sql)
        # return the results
        return render_template("deckCreate.html", results=result)


# create a new card for a specific deck and add it to the database
@app.route('/decks/<int:id>/create/', methods=['GET', 'POST'])
def createCard(id):

    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation FROM Decks WHERE deck_ID = ?;
        """
    deck_info = query_db(sql_deck, (id,))[0]

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            error = "Both fields are required."

            return render_template("cardCreate.html", error=error, deck_info=deck_info)

        else:
            sql = """
                    INSERT INTO Flashcards (card_question, card_answer, card_deckID, card_creation, card_hint)
                    VALUES (?, ?, ?, datetime('now'), ?);
                """

            get_db().execute(sql, (card_question, card_answer, id, card_hint))
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
            return render_template("deck.html", error=error, id=id)

        else:
            sql = """
                    UPDATE Decks
                    SET deck_name = ?, deck_description = ?
                    WHERE deck_ID = ?;
                """
            get_db().execute(sql, (deck_name, deck_description, id))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks
                WHERE deck_ID = ?;
            """
        result = query_db(sql, (id,))
        # return the results
        return render_template("deckEdit.html", results=result)


# edit a card and update the database
@app.route('/decks/<int:id>/cards/<int:card_id>/edit/', methods=['GET', 'POST'])
def editCard(id, card_id):
    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation FROM Decks WHERE deck_ID = ?;
        """
    deck_info = query_db(sql_deck, (id,))[0]

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            error = "Both fields are required."

            sql_card = "SELECT card_ID, card_question, card_answer, card_creation, card_hint FROM Flashcards WHERE card_ID = ?;"
            card = query_db(sql_card, (card_id,), one=True)
            return render_template("cardEdit.html", error=error, deck_info=deck_info, cards=card)

        else:
            sql = """
                    UPDATE Flashcards
                    SET card_question = ?, card_answer = ?, card_hint = ?
                    WHERE card_ID = ? AND card_deckID = ?;
                """

            get_db().execute(sql, (card_question, card_answer, card_hint, card_id, id))
            get_db().commit()
            # redirect to the deck page
            return redirect(url_for('Deck', id=id))

    # if request method is GET, return the sql results
    else:

        # return cardinfo
        sql_card = "SELECT card_ID, card_question, card_answer, card_creation, card_hint FROM Flashcards WHERE card_ID = ?;"
        card = query_db(sql_card, (card_id,), one=True)
        return render_template("cardEdit.html", deck_info=deck_info, cards=card)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        # get the form data
        username = request.form['username']
        password = request.form['password']

        sql = """
                SELECT user_name, user_password
                FROM Users
                WHERE user_name = ?;
            """
        username_list = query_db(sql, (username,))

        # check if the username and password are not empty
        if not username or not password:
            error = "Both fields are required."
            return render_template("login.html", error=error)

        elif not username_list:
            # reload the page with the error message
            error = "No account under the username " + username + "."
            return render_template("login.html", error=error)

        else:
            # check if the password is correct
            if password == username_list[0][1]:
                # logged in successfully, redirect to homepage
                return redirect(url_for('home'))
            else:
                error = "Incorrect password."
                return render_template("login.html", error=error)

    else:
        return render_template("login.html")


@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        # get the form data
        username = request.form['username']
        password = request.form['password']

        sql = """
                SELECT user_name
                FROM Users
                WHERE user_name = ?;
            """
        username_list = query_db(sql, (username,))

        # check if the username and password are not empty
        if not username or not password:
            error = "Both fields are required."
            return render_template("signup.html", error=error)

        # check if the username already exists in the database
        elif username_list:
            error = "Username already exists."
            return render_template("signup.html", error=error)

        else:
            # reload the page with the error message
            error = "Not accepting new signups yet."
            return render_template("signup.html", error=error)

    else:
        return render_template("signup.html")

# only run the app if app.py is executed directly
if __name__ == "__main__":
    app.run(debug=True)
