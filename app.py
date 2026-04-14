"""
This is a flashcard making app that allows users to:
- create decks of flashcards
- create flashcards with a question and answer
- edit and delete decks and flashcards
- study flashcards indervidually
- delete decks and flashcards
- login and sign up to save their decks
- view their profile and stats
- track how many times they got a flashcard correct or incorrect
- Upload images to flashcards
- Type with mathematical symbols using LaTeX in flashcards
"""

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

import os  # for file extension and name extraction
import random  # for randomising card list

# from werkzeug.utils import secure_filename  # for file uploads
from datetime import (
    datetime,
    timezone
)  # for time formatting

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)  # for user login password encryption

from werkzeug.utils import (
    secure_filename
)  # for securing uploaded files

import sqlite3

DATABASE = 'database.db'  # relative path to the database file
UPLOAD_FOLDER = 'static\\uploads'  # folder to store uploaded files
ALLOWED_IMAGES = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.apng', '.svg'
}
ALLOWED_AUDIO = {
    '.mp3'
}

# initialise app
app = Flask(__name__)

# set a secret key for sessions
app.config['SECRET_KEY'] = "8y9awhDWdhHfw8ghgrgdgGRgDEgwndaiundIUDNu1823892e8h"
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB file size limit


# ---------- FLASK SETUP ----------
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


# ---------- convet YYYY-MM-DD HH:MM:SS to x minutes/hours/days ago ----------
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


# ---------- convet YYYY-MM-DD HH:MM:SS to DD/Month/YYYY ----------
def format_date(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)

    # convert to local time
    local_dt = dt.astimezone()  # system local zone
    return local_dt.strftime("%d/%b/%Y")


# ---------- get user ID ----------
def userID():
    return session.get('userID', 0)


# ---------- user information ----------
@app.context_processor
def uservar():
    return {
        "username": session.get("username", "Guest"),
        "userID": session.get("userID", 0)
    }


# ---------- homepage ----------
@app.route('/')
def home():
    # flash("Welcome to the Flashcard App!", "success")
    # flash("⚠ Something went wrong...", "error")

    can_resume = bool(session.get('study_deckID') and session.get('shuffled_cards'))

    if not userID():
        flash("🛈 You have limited Access. Please Login or Sign Up to create your own decks!", "info")

    if can_resume:
        sql = "SELECT deck_name FROM Decks WHERE deck_ID = ?"
        deck_name = query_db(sql, (session['study_deckID'],), one=True)[0]
        total = len(session['shuffled_cards'])
        percent = (session.get('current_index') / total) * 100
    else:
        deck_name = None
        total = 0
        percent = 0

    return render_template(
        "homepage.html", username=session.get(
            'username', 'Guest'
        ),
        userID=session.get('userID', 0),
        can_resume=can_resume,
        deckID=session.get('study_deckID', None),
        index=session.get('current_index', 0),
        deck_name=deck_name,
        total=total,
        percent=percent
    )


# ---------- list all decks ----------
@app.route('/decks/')
def Decks():
    filter = request.args.get('filter')
    sort_by = request.args.get('sort_by')
    order = request.args.get('order')
    allowed_filter = {'none', 'public', 'unlisted', 'private'}
    allowed_sort = {'deck_creation', 'deck_name', 'deck_description'}
    allowed_order = {'ASC', 'DESC'}

    if filter not in allowed_filter:
        filter = 'none'  # default filter none

    if sort_by not in allowed_sort:
        sort_by = 'deck_creation'  # default sort by creation date

    if order not in allowed_order:
        order = 'DESC'  # default order descending

    # if user is logged in show all their decks
    if userID():
        # if filter is not none
        if filter != 'none':
            filter_sql = "AND deck_visibility = ?"
            filter_args = (userID(), filter)
        else:
            filter_sql = ""
            filter_args = (userID(),)

        # get all the decks id, name, description, and creation date
        sql = f"""
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks
                WHERE deck_userID = ?
                {filter_sql}
                ORDER BY {sort_by} {order};
            """
        result = query_db(sql, filter_args)

    # if user not logged in
    else:
        sql = f"""
            SELECT deck_ID, deck_name, deck_description, deck_creation
            FROM Decks
            WHERE deck_visibility = 'public'
            ORDER BY {sort_by} {order};
        """
        result = query_db(sql)

    # return the results
    return render_template(
        "decks.html",
        results=result,
        sort_by=sort_by,
        order=order,
        filter=filter,
        userID=userID()
    )


# ---------- list all flashcards for a single deck ----------
@app.route('/decks/<int:id>/')
def Deck(id):
    sort_by = request.args.get('sort_by')
    order = request.args.get('order')
    allowed_sort = {'card_creation', 'card_question', 'card_answer'}
    allowed_order = {'ASC', 'DESC'}

    if sort_by not in allowed_sort:
        sort_by = 'card_creation'  # default sort by creation date
    if order not in allowed_order:
        order = 'DESC'  # default order descending

    # get all the card id, Q, A, and creation date for inputted deck id
    sql = f"""
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?
            ORDER BY {sort_by} {order};
        """
    # get the deck name of the inputted deck id
    # only show the deck if it belongs to the user or if it is public/unlisted
    sql_deck = """
                SELECT deck_name, deck_ID, deck_creation, deck_userID
                FROM Decks
                WHERE deck_ID = ?
                AND (
                    deck_userID = ? OR (
                        deck_visibility = 'public'
                        OR deck_visibility = 'unlisted'
                    )
                );
            """

    deck_info = query_db(sql_deck, (id, userID()), True)
    results = query_db(sql, (id,))

    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    # chek if the user is the owner of the deck
    is_owner = deck_info[3] == userID()

    # check if the user can resume studying the deck
    can_resume = (session.get('study_deckID') == id) and (session.get('shuffled_cards') is not None)

    # return the results
    return render_template(
        "deck.html",
        results=results,
        deck_info=deck_info,
        time_ago=time_ago,
        format_date=format_date,
        sort_by=sort_by,
        order=order,
        is_owner=is_owner,
        can_resume=can_resume
    )


# ---------- delete a card ----------
@app.route('/decks/<int:id>/cards/<int:card_id>/delete/', methods=['POST'])
def deleteCard(id, card_id):
    # check if the deck id is valid and belongs to the user
    sql_deck = """
        SELECT deck_ID
        FROM Decks
        WHERE deck_ID = ?
        AND deck_userID = ?;
    """
    deck_info = query_db(sql_deck, (id, userID()), one=True)
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    # delete the card with the inputted card id
    sql = """
            DELETE FROM Flashcards
            WHERE card_ID = ?
            AND card_deckID = ?;
        """
    get_db().execute(sql, (card_id, id))
    get_db().commit()
    # redirect to the deck page
    flash("✔ Card Deleted Successfuly.", "success")
    return redirect(url_for('Deck', id=id))


# ---------- delete a deck ----------
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
    flash("✔ Deck Deleted Successfully", "success")
    return redirect(url_for('Decks'))


# ---------- refresh session data on study ----------
@app.route('/decks/<int:id>/study/start/')
def start_study(id):
    # set session data to empty to remove previous list
    session.pop('shuffled_cards', None)
    session.pop('study_deckID', None)
    session.pop('current_index', None)
    # redirect to study
    return redirect(url_for('Study', id=id, index=0))


# ---------- redirect to study with saved index ----------
@app.route('/decks/<int:id>/study/resume/')
def resume_study(id):
    saved_index = session.get('current_index', 0)
    return redirect(url_for('Study', id=id, index=saved_index))


# ---------- study a single card based on the index ----------
@app.route('/decks/<int:id>/study/<int:index>/', methods=['GET', 'POST'])
def Study(id, index):
    # check if the deck id is valid and belongs to the user
    sql_deck = """
        SELECT deck_ID, deck_userID, deck_visibility
        FROM Decks
        WHERE deck_ID = ?;
    """
    deck_info = query_db(sql_deck, (id,), one=True)
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    # check if deck is private and if user has permission to view it
    if deck_info[2] == 'private' and deck_info[1] != userID():
        flash("⚠ You Do Not Have Permission to Study This Deck...", "error")
        return redirect(url_for("Decks"))

    # get all the card id, Q, A, and creation date for inputted deck id
    sql = """
        SELECT card_ID, card_question,
        card_answer, card_creation, card_hint
        FROM Flashcards
        WHERE card_deckID = ?;
    """
    results = query_db(sql, (id,))

    # get session data
    currentSession = session.get('shuffled_cards', None)
    currentSessionDeck = session.get('study_deckID', None)

    # check if session exists or matches deck ID
    if currentSessionDeck != id or not currentSession:
        temp_list = [list(item) for item in results]
        random.shuffle(temp_list)
        session['shuffled_cards'] = temp_list
        session['study_deckID'] = id
        session['current_index'] = 0

    # set session index to current index
    else:
        session['current_index'] = index

    # set card_list to the session list
    card_list = session['shuffled_cards']

    # get total number of cards in the deck
    total = len(card_list)

    card = card_list[index]  # get the current card info based on the index
    card_id = card[0]

    # request is POST, get the form data and add to database
    if request.method == 'POST':
        if userID():
            # get response
            response = request.form.get('response')
            # get the user's stats for the current card
            get_stats = """
                SELECT *
                FROM UserCardStats
                WHERE stats_cardID = ?
                AND stats_userID = ?;
            """
            stats = query_db(get_stats, (card_id, userID()))

            # if the user got the card correct
            if response == "correct":

                # if the user has no stats for card, create new entry
                if not stats:
                    add_stats = """
                        INSERT INTO UserCardStats (
                            stats_correct, stats_userID, stats_cardID
                        )
                        Values (?, ?, ?)
                    """
                    # add 1 correct
                    get_db().execute(add_stats, (1, userID(), card_id))
                    get_db().commit()

                # if the user has stats for the card, add 1 to correct
                else:
                    update_stats = """
                        UPDATE UserCardStats
                        SET stats_correct = stats_correct + 1
                        WHERE stats_cardID = ?
                        AND stats_userID = ?
                    """
                    get_db().execute(update_stats, (card_id, userID()))
                    get_db().commit()

            # if the user got the card incorrect
            elif response == "incorrect":
                # if the user has no stats for card, create new entry
                if not stats:
                    add_stats = """
                        INSERT INTO UserCardStats (
                            stats_incorrect, stats_userID, stats_cardID
                        )
                        Values (?, ?, ?)
                    """
                    # add 1 incorrect
                    get_db().execute(add_stats, (1, userID(), card_id))
                    get_db().commit()

                # if the user has stats for card, add 1 to incorrect
                else:
                    update_stats = """
                        UPDATE UserCardStats
                        SET stats_incorrect = stats_incorrect + 1
                        WHERE stats_cardID = ?
                        AND stats_userID = ?
                    """
                    get_db().execute(update_stats, (card_id, userID()))
                    get_db().commit()

        # go to next page
        if index + 1 < total:
            session['current_index'] = index + 1
            return redirect(url_for('Study', id=id, index=index + 1))

        # exit to deck page if there are no more cards
        else:
            # clear sessions after exit
            session.pop('shuffled_cards', None)
            session.pop('study_deckID', None)
            session.pop('current_index', None)
            # redirect to deck page
            flash("✔ You Have Finished Studying This Deck!", "success")
            return redirect(url_for('Deck', id=id))

    # return the results in method is GET
    else:
        return render_template(
            "card.html",
            cards=card,
            deck_id=id,
            total=total,
            index=index
        )


# ---------- create a new deck ----------
@app.route('/decks/create/', methods=['GET', 'POST'])
def createDeck():
    if not userID():
        flash("⚠ You Are Not Logged In. Please Log In to Create a Deck.",
              "error")
        return redirect(url_for('Decks'))
    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']
        deck_visibility = request.form['deckVisibility']

        # check if the form data is not empty
        if not deck_name:
            # reload the page with the error message
            flash("⚠ A Deck Name is Required.", "error")
            return render_template("deckCreate.html")

        else:
            sql = """
                    INSERT INTO Decks (
                        deck_name, deck_description, deck_creation, deck_userID, deck_visibility
                    )
                    VALUES (?, ?, datetime('now'), ?, ?);
                """
            get_db().execute(sql, (deck_name, deck_description, userID(), deck_visibility))
            get_db().commit()
            # redirect to the decks list page
            flash("✔ Deck Created Successfully!", "success")
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        deck_visibility = "private"  # default visibility
        return render_template("deckCreate.html", visibility=deck_visibility)


# ---------- create a new card ----------
@app.route('/decks/<int:id>/create/', methods=['GET', 'POST'])
def createCard(id):
    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation, deck_userID
            FROM Decks
            WHERE deck_ID = ?;
        """
    deck_info = query_db(sql_deck, (id,))

    # check if deck_info is not empty
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    if deck_info[0][3] != userID():
        flash("⚠ You Do Not Own This Deck. You Cannot Create a Card.", "error")
        return redirect(url_for("Decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            flash("⚠ Both Fields Are Required.", "error")
            return render_template(
                "cardCreate.html",
                deck_info=deck_info[0]
            )

        else:
            sql = """
                    INSERT INTO Flashcards (
                        card_question, card_answer, card_deckID,
                        card_creation, card_hint
                    )
                    VALUES (?, ?, ?, datetime('now'), ?);
                """

            get_db().execute(sql, (
                card_question,
                card_answer,
                id,
                card_hint
            ))
            get_db().commit()
            # redirect to the deck page
            flash("✔ Card Created Successfully!", "success")
            return redirect(url_for('Deck', id=id))

    # if request method is GET, return the sql results
    else:
        # return deckinfo
        return render_template("cardCreate.html", deck_info=deck_info[0])


# ---------- edit a deck ----------
@app.route('/decks/<int:id>/edit/', methods=['GET', 'POST'])
def editDeck(id):
    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']
        deck_visibility = request.form['deckVisibility']

        # check if the form data is not empty
        if not deck_name:
            # reload the page with the error message
            flash("⚠ A Deck Name is Required.", "error")
            return render_template("deck.html", id=id)

        else:
            sql = """
                    UPDATE Decks
                    SET deck_name = ?, deck_description = ?, deck_visibility = ?
                    WHERE deck_ID = ?
                    AND deck_userID = ?;
                """
            get_db().execute(sql, (deck_name, deck_description, deck_visibility, id, userID()))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description, deck_creation, deck_visibility
                FROM Decks
                WHERE deck_ID = ? AND deck_userID = ?;
            """
        result = query_db(sql, (id, userID()))

        if not result:
            flash("⚠ Invalid Deck...", "error")
            return redirect(url_for("Decks"))

        # return the results
        return render_template("deckEdit.html", results=result)


# ---------- edit a card ----------
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
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_question = request.form['cardQuestion']
        card_answer = request.form['cardAnswer']
        card_hint = request.form['cardHint']

        # check if the form data is not empty
        if not card_question or not card_answer:
            # reload the page with the error message
            flash("⚠ Both Fields Are Required.", "error")
            sql_card = """
                SELECT card_ID, card_question,
                card_answer, card_creation, card_hint
                FROM Flashcards
                WHERE card_ID = ?
                AND card_deckID = ?;
            """
            card = query_db(sql_card, (card_id, id), one=True)
            return render_template(
                "cardEdit.html",
                deck_info=deck_info[0],
                cards=card
            )

        # if form data is present in both
        else:
            sql = """
                    UPDATE Flashcards
                    SET card_question = ?, card_answer = ?, card_hint = ?
                    WHERE card_ID = ? AND card_deckID = ?;
                """

            get_db().execute(sql, (
                card_question,
                card_answer,
                card_hint,
                card_id,
                id
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
            AND card_deckID = ?;
        """
        card = query_db(sql_card, (card_id, id), one=True)

        # check if card is not empty
        if not card:
            flash("⚠ Invalid Card...", "error")
            return redirect(url_for('Deck', id=id))

        return render_template(
            "cardEdit.html",
            deck_info=deck_info[0],
            cards=card
        )


# ---------- login ----------
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
            flash("⚠ Both Fields Are Required.", "error")
            return render_template("login.html")

        elif not username_list:
            # reload the page with the error message
            flash(
                "⚠ No Account Exists Under the Username "
                f"{username}...", "error"
            )
            return render_template("login.html")

        elif username_list[0][0] == username:
            # check if the password is correct
            if check_password_hash(username_list[0][1], password):
                # logged in successfully, redirect to homepage
                session['username'] = username
                session['userID'] = query_db(
                    "SELECT user_ID FROM Users WHERE user_name = ?",
                    (username,), one=True
                )[0]
                flash("✔ Logged in Successfully!", "success")
                return redirect(url_for('home'))
            else:
                flash("⚠ Incorrect Password.", "error")
                return render_template("login.html")
        else:
            flash("⚠ Something Went Wrong...", "error")
            return render_template("login.html")
    else:
        return render_template("login.html")


# ---------- sign up ----------
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
            flash("⚠ All Fields Are Required.", "error")
            return render_template("signup.html")

        elif confirm_password != password:
            flash("⚠ Passwords Do Not Match.", "error")
            return render_template("signup.html")

        # check if the username already exists in the database
        elif username_list:
            flash("⚠ Username Already Exists.", "error")
            return render_template("signup.html")

        else:
            hashed_password = generate_password_hash(password)
            sql = """
                    INSERT INTO Users (
                        user_name, user_password, user_creation
                    )
                    VALUES (?, ?, datetime('now'));
                """
            get_db().execute(sql, (username, hashed_password))
            get_db().commit()
            flash("✔ Account Created Successfully! Please Log In.", "success")
            return render_template("login.html")

    else:
        return render_template("signup.html")


# ---------- profile ----------
@app.route('/profile/')
def profile():
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
        flash(
            "⚠ You Are Not Logged In. Please Log In to View Your Profile.",
            "error"
        )
        return redirect(url_for('home'))

    sql = """
            SELECT user_name, user_creation
            FROM Users
            WHERE user_ID = ?;
        """

    results = query_db(sql, (userID(),))

    if not results:
        flash("⚠ User Details Not Found. Logging Out.", "error")
        return redirect(url_for('logout'))

    # return the results
    return render_template(
        "profile.html",
        results=results[0],
        format_date=format_date,
        time_ago=time_ago
    )


# ---------- logout ----------
@app.route('/logout/')
def logout():
    session.pop('username', None)
    session.pop('userID', None)
    flash("✔ Logged Out Successfully.", "success")
    return redirect(url_for('home'))


# ---------- stats ----------
@app.route('/stats/')
def stats():
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
        flash("⚠ You Are Not Logged In. Please Log In to See Stats.", "error")
        return redirect(url_for('home'))

    userAnswerStats = """
            SELECT SUM(stats_correct), SUM(stats_incorrect)
            FROM UserCardStats
            WHERE stats_userID = ?;
        """
    answer_stats = query_db(userAnswerStats, (userID(),))

    userDeckStats = """
            SELECT COUNT(deck_ID)
            FROM Decks
            WHERE deck_userID = ?;
    """
    deck_stats = query_db(userDeckStats, (userID(),))

    userCardStats = """
            SELECT COUNT(Flashcards.card_ID)
            FROM Flashcards, Decks
            WHERE card_deckID = deck_ID AND deck_userID = ?;
    """
    card_stats = query_db(userCardStats, (userID(),))

    # return the results
    return render_template(
        "stats.html",
        answer_stats=answer_stats[0],
        deck_stats=deck_stats[0],
        card_stats=card_stats[0]
    )


# ---------- test ----------
@app.route('/test/', methods=['GET', 'POST'])
def test():
    if request.method == 'POST':
        # get the form data from the request object like this
        # item = request.form['file_name']
        # now get the filename from the form
        file = request.files['file']

        if file.filename == '':
            return "No selected file", 400

        # should check the file is valid but for simplicity......
        # save the file in the UPLOAD_FOLDER
        print(f"Uploading file: {file.filename} to {UPLOAD_FOLDER}")
        original_name = secure_filename(file.filename)

        extension = os.path.splitext(original_name)[1].lower()

        if extension not in ALLOWED_IMAGES:
            return "Invalid file type", 400

        sql = """
                INSERT INTO Files (
                    file_name, file_cardID, file_userID
                )
                VALUES (?, ?, ?);
            """
        get_db().execute(sql, (original_name, 2, userID()))
        get_db().commit()

        get_ID = "SELECT last_insert_rowid();"
        file_ID = query_db(get_ID, (), one=True)[0]  # get the ID of the file
        print(f"ROW ID: {file_ID}")

        extension = os.path.splitext(original_name)[1]
        new_filename = f"{file_ID}{extension}"

        file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        # now insert into the database

        return redirect(url_for('home'))
    else:
        # get the deck name of the inputted deck id
        sql1 = """
                SELECT Flashcards.card_question,
                Flashcards.card_answer, Decks.deck_name
                FROM Flashcards, Decks;
            """
        card_list = query_db(sql1)
        return render_template("test.html", card_list=card_list)


# only run the app if app.py is executed directly
if __name__ == "__main__":
    app.run(debug=True)
