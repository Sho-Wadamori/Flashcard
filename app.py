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
import time  # for timer

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
        db.execute("PRAGMA foreign_keys = ON")  # enable on delete cascade
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


# ---------- send day difference ----------
def is_streak_eligible(last_datetime):
    # convert str to datetime
    dt = datetime.strptime(last_datetime, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone()
    # convert datetime to day
    last_date = dt.date()

    today = datetime.now().astimezone().date()

    diff = (today - last_date).days

    return diff


# ---------- update streak counter ----------
def updateStreak():
    get_streak = """
        SELECT user_lastStudied, user_streak
        FROM Users
        WHERE user_ID = ?;
    """
    streaks = query_db(get_streak, (userID(),))
    diff = is_streak_eligible(streaks[0][0])

    current_streak = int(streaks[0][1])

    if diff >= 2:
        update_streaks = """
            UPDATE Users
            SET user_streak = 0
            WHERE user_ID = ?;
        """
        get_db().execute(update_streaks, (userID(),))
        get_db().commit()

        current_streak = 0

    return current_streak


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


# ---------- obfuscate email using astrisk ----------
def obfuscate_email(email):
    fistPart, domain = email.split('@')
    return fistPart[0] + '*****@' + domain


# ---------- layout page ----------
@app.context_processor
def uservar():
    settingsSQL = """
        SELECT settings_bg1, settings_bg2, settings_text,
        settings_accentBG, settings_accentTXT, settings_cardBG,
        settings_cardTXT, settings_warning, settings_shadow, settings_fontSize,
        settings_animation
        FROM Settings
        WHERE settings_userID = ?
    """
    settings = query_db(settingsSQL, (userID(),))[0]

    return {
        "username": session.get("username", "Guest"),
        "userID": session.get("userID", 0),
        "settings": settings
    }


# ---------- homepage ----------
@app.route('/')
def home():
    # check if unfinished study session exists
    can_resume = bool(
        session.get('study_deckID') and session.get('shuffled_cards')
    )

    # give message to users not logged in
    if not userID():
        flash("""
            🛈 You have limited Access.
            Please Login to create your own decks!
        """, "info")

    # get info of the unfishished study session
    if can_resume:
        sql = "SELECT deck_name FROM Decks WHERE deck_ID = ?"
        deck_name = query_db(sql, (session['study_deckID'],), one=True)[0]
        total = len(session['shuffled_cards'])
        percent = (session.get('current_index') / total) * 100
    else:
        deck_name = None
        total = 0
        percent = 0

    # get public decks
    public_sql = """
        SELECT deck_ID, deck_name, deck_description, deck_creation
        FROM Decks
        WHERE deck_visibility = 'public'
        ORDER BY deck_creation DESC
        LIMIT 3;
    """
    publicDecks = query_db(public_sql)

    # get stats if user is logged in
    if userID():
        # get total study time
        studyTime = """
            SELECT SUM(study_duration), SUM(study_cardCount)
            FROM StudyHistory
            WHERE study_userID = ?;
        """
        totalDuration = query_db(studyTime, (userID(),))[0]

        # get answer stats
        userAnswerStats = """
            SELECT SUM(stats_correct), SUM(stats_incorrect)
            FROM UserCardStats
            WHERE stats_userID = ?;
        """
        answer_stats = query_db(userAnswerStats, (userID(),))[0]

        if totalDuration[0] is not None:
            if totalDuration[0] >= 3600:
                hours = totalDuration[0] // 3600
                minutes = (totalDuration[0] % 3600) // 60
                seconds = totalDuration[0] % 60
                totalDuration = f"{hours}h {minutes}m {seconds}s"

            elif totalDuration[0] >= 60:
                minutes = totalDuration[0] // 60
                seconds = totalDuration[0] % 60
                totalDuration = f"{minutes}m {seconds}s"

            else:
                totalDuration = f"{totalDuration[0]}s"
        else:
            totalDuration = "0s"

        # get all study history data
        studyHistory = """
            SELECT *
            FROM StudyHistory
            WHERE study_userID = ?
        """
        totalSessions = len(query_db(studyHistory, (userID(),)))

        currentStreak = updateStreak()

    # if not logged in
    else:
        totalDuration = "0s"
        totalSessions = 0
        answer_stats = 0
        currentStreak = ""

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
        percent=percent,
        totalDuration=totalDuration,
        totalSessions=totalSessions,
        publicDecks=publicDecks,
        answer_stats=answer_stats,
        currentStreak=currentStreak
    )


# ---------- list all decks ----------
@app.route('/decks/', methods=['GET', 'POST'])
def Decks():
    if request.method == 'POST':
        # get bookmarked deck's ID
        bookmarkID = request.form.get('bookmarkID')

        # check whether bookmarked deck is already bookmarked
        clicked_bookmark = """
            SELECT deck_bookmarked
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
        deckBookmark = query_db(clicked_bookmark, (bookmarkID, userID(),))

        # get number of already bookmarked decks
        all_bookmark = """
            SELECT COUNT(*)
            FROM Decks
            WHERE deck_userID = ?
            AND deck_bookmarked = 1;
        """
        totalBookmarks = query_db(all_bookmark, (userID(),))[0][0]

        if not deckBookmark:
            flash("⚠ Something Went Wrong...", "error")
            return redirect(request.url)

        # if bookmarking
        if deckBookmark[0][0] == 0:
            # if total bookmarked is >= 3 return error
            if totalBookmarks >= 3:
                flash("""
                    ⚠ You Can Only Have 3 Decks Bookmarked.
                    Please Unbookmark A Deck First.
                """, "error")
                return redirect(request.url)

            # else update the deck_bookmarked to 1
            update_bookmark = """
                UPDATE Decks
                SET deck_bookmarked = 1
                WHERE deck_ID = ?
                AND deck_userID = ?;
            """
            get_db().execute(update_bookmark, (bookmarkID, userID(),))
            get_db().commit()

        # if unbookmarking, set deck_bookmarked to 0
        else:
            update_bookmark = """
                UPDATE Decks
                SET deck_bookmarked = 0
                WHERE deck_ID = ?
                AND deck_userID = ?;
            """
            get_db().execute(update_bookmark, (bookmarkID, userID(),))
            get_db().commit()

        return redirect(request.url)

    else:
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
                    AND deck_bookmarked = 0
                    {filter_sql}
                    ORDER BY {sort_by} {order};
                """
            result = query_db(sql, filter_args)

            bookmark_sql = f"""
                    SELECT deck_ID, deck_name, deck_description, deck_creation
                    FROM Decks
                    WHERE deck_userID = ?
                    AND deck_bookmarked = 1
                    {filter_sql}
                    ORDER BY {sort_by} {order};
                """

            bookmarkResult = query_db(bookmark_sql, filter_args)

        # if user not logged in
        else:
            sql = f"""
                SELECT deck_ID, deck_name, deck_description, deck_creation
                FROM Decks
                WHERE deck_visibility = 'public'
                ORDER BY {sort_by} {order};
            """
            result = query_db(sql)

            bookmarkResult = ""

        bookmarkLength = len(bookmarkResult)

        # return the results
        return render_template(
            "decks.html",
            results=result,
            sort_by=sort_by,
            order=order,
            filter=filter,
            userID=userID(),
            bookmarkResult=bookmarkResult,
            bookmarkLength=bookmarkLength
        )


# ---------- list all flashcards for a single deck ----------
@app.route('/decks/<int:id>/')
def Deck(id):
    # get the deck info if deck belongs to user or if it is public/unlisted
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

    # kick out user if they dont meet these conditions
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    filter = request.args.get('filter')
    sort_by = request.args.get('sort_by')
    order = request.args.get('order')
    allowed_filter = {'none', 'flashcard', 'quiz', 'TF'}
    allowed_sort = {
        'card_creation',
        'card_question',
        'card_answer',
        'card_mode'
    }
    allowed_order = {'ASC', 'DESC'}

    # fallback for invalid sort/order (not really necessary)
    if filter not in allowed_filter:
        filter = 'none'  # default filter none
    if sort_by not in allowed_sort:
        sort_by = 'card_creation'  # default sort by creation date
    if order not in allowed_order:
        order = 'DESC'  # default order descending

    # create filter query that we will inject
    if filter != 'none':
        filterSQL = f"AND (Flashcards.card_mode != '{filter}') "
    else:
        filterSQL = ""

    # get all card info for inputted deck id
    # use LEFT JOIN to get all info even if they are invalid for the card mode
    card_sql = f"""
        SELECT Flashcards.card_ID,
        Flashcards.card_creation,
        Flashcards.card_mode,
        FlashcardContent.flashcard_question,
        FlashcardContent.flashcard_answer,
        QuizContent.quiz_question,
        QuizContent.quiz_answer1,
        QuizContent.quiz_answer2,
        QuizContent.quiz_answer3,
        QuizContent.quiz_answer4,
        QuizContent.quiz_correct,
        TrueFalseContent.tf_question,
        TrueFalseContent.tf_correct
        FROM Flashcards
        LEFT JOIN FlashcardContent ON Flashcards.card_ID = FlashcardContent.card_ID
        LEFT JOIN QuizContent ON Flashcards.card_ID = QuizContent.card_ID
        LEFT JOIN TrueFalseContent ON Flashcards.card_ID = TrueFalseContent.card_ID
        WHERE Flashcards.card_deckID = ?
        {filterSQL};
    """
    cards = query_db(card_sql, (id,))

    results = []
    for card in cards:
        if card[2] == 'flashcard':
            question = card[3]
            answer = card[4]

        elif card[2] == 'quiz':
            question = card[5]
            if card[10] == 1:
                answer = card[6]
            elif card[10] == 2:
                answer = card[7]
            elif card[10] == 3:
                answer = card[8]
            elif card[10] == 4:
                answer = card[9]
            else:
                answer = "ERROR"

        elif card[2] == 'TF':
            question = card[11]
            if card[12] == 1:
                answer = "True"
            elif card[12] == 2:
                answer = "False"
            else:
                answer = "ERROR"

        else:
            flash("""
                ⚠ Some of Your Cards Are Invalid. 
                Please contact the owner of the site.
            """, "error")

        results.append((card[0], card[1], card[2], question, answer))

    # card = f"""
    #     SELECT card_ID, card_creation, card_mode
    #     FROM Flashcards
    #     WHERE card_deckID = ?
    #     ORDER BY {sort_by} {order};
    # """
    # results = query_db(card, (id,))

    # cards = []
    # for row in results:
    #     mode = row[2]
    #     if mode == 'flashcard':
    #         content = query_db("""
    #             SELECT flashcard_question, flashcard_answer
    #             FROM Flashcards
    #             WHERE card_ID = ?
    #         """, (row[0],))

    #     elif mode == 'quiz':
    #         content = query_db("""
    #             SELECT quiz_question, quiz_answer
    #             FROM Flashcards
    #             WHERE card_ID = ?
    #         """, (row[0],))

    #     elif mode == 'TF':
    #         content = query_db("""
    #             SELECT tf_question, tf_answer
    #             FROM Flashcards
    #             WHERE card_ID = ?
    #         """, (row[0],))



    # handeling sorting and ordering
    ordering = order == "DESC"

    if sort_by == "card_answer":
        results.sort(key=lambda x: x[4], reverse=ordering)

    elif sort_by == "card_question":
        results.sort(key=lambda x: x[3], reverse=ordering)

    elif sort_by == "mode":
        results.sort(key=lambda x: x[2], reverse=ordering)

    else:
        results.sort(key=lambda x: x[1], reverse=ordering)

    # chek if the user is the owner of the deck
    is_owner = deck_info[3] == userID()

    # check if the user can resume studying the deck
    can_resume = (
        session.get('study_deckID') == id
    ) and (
        session.get('shuffled_cards') is not None
    )

    # return the results
    return render_template(
        "deck.html",
        results=results,
        deck_info=deck_info,
        time_ago=time_ago,
        format_date=format_date,
        filter=filter,
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
    session.pop('correct', None)
    session.pop('incorrect', None)
    session.pop('study_startTime', None)
    # redirect to study
    return redirect(url_for('Study', id=id, index=0))


# ---------- redirect to study with saved index ----------
@app.route('/decks/<int:id>/study/resume/')
def resume_study(id):
    saved_index = session.get('current_index', 0)
    session['study_startTime'] = time.time()
    return redirect(url_for('Study', id=id, index=saved_index))


def updateCardStats(result, id):
    # get the user's stats for the current card
    get_stats = """
        SELECT *
        FROM UserCardStats
        WHERE stats_cardID = ?
        AND stats_userID = ?;
    """
    stats = query_db(get_stats, (id, userID()))

    # if the user got the card correct
    if result:
        # if the user has no stats for card, create new entry
        if not stats:
            add_stats = """
                INSERT INTO UserCardStats (
                    stats_correct, stats_userID, stats_cardID
                )
                Values (?, ?, ?)
            """
            # add 1 correct
            get_db().execute(add_stats, (1, userID(), id))
            get_db().commit()

        # if the user has stats for the card, add 1 to correct
        else:
            update_stats = """
                UPDATE UserCardStats
                SET stats_correct = stats_correct + 1
                WHERE stats_cardID = ?
                AND stats_userID = ?
            """
            get_db().execute(update_stats, (id, userID()))
            get_db().commit()

        session['correct'] = session.get('correct', 0) + 1

    # if the user got the card incorrect
    elif not result:
        # if the user has no stats for card, create new entry
        if not stats:
            add_stats = """
                INSERT INTO UserCardStats (
                    stats_incorrect, stats_userID, stats_cardID
                )
                Values (?, ?, ?)
            """
            # add 1 incorrect
            get_db().execute(add_stats, (1, userID(), id))
            get_db().commit()

        # if the user has stats for card, add 1 to incorrect
        else:
            update_stats = """
                UPDATE UserCardStats
                SET stats_incorrect = stats_incorrect + 1
                WHERE stats_cardID = ?
                AND stats_userID = ?
            """
            get_db().execute(update_stats, (id, userID()))
            get_db().commit()

        session['incorrect'] = session.get('incorrect', 0) + 1


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

    # get card info
    card_sql = """
        SELECT Flashcards.card_ID,
        Flashcards.card_creation,
        Flashcards.card_mode,
        Flashcards.card_hint,
        FlashcardContent.flashcard_question,
        FlashcardContent.flashcard_answer,
        QuizContent.quiz_question,
        QuizContent.quiz_answer1,
        QuizContent.quiz_answer2,
        QuizContent.quiz_answer3,
        QuizContent.quiz_answer4,
        QuizContent.quiz_correct,
        TrueFalseContent.tf_question,
        TrueFalseContent.tf_correct
        FROM Flashcards
        LEFT JOIN FlashcardContent ON Flashcards.card_ID = FlashcardContent.card_ID
        LEFT JOIN QuizContent ON Flashcards.card_ID = QuizContent.card_ID
        LEFT JOIN TrueFalseContent ON Flashcards.card_ID = TrueFalseContent.card_ID
        WHERE Flashcards.card_deckID = ?;
    """
    results = query_db(card_sql, (id,))

    # check if card is not empty
    if not results:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for('Deck', id=id))

    # get session data
    currentSession = session.get('shuffled_cards', None)
    currentSessionDeck = session.get('study_deckID', None)

    # reset all values and shuffle cards if no unfinished sessions
    if currentSessionDeck != id or not currentSession:
        temp_list = [list(item) for item in results]
        random.shuffle(temp_list)
        session['shuffled_cards'] = temp_list
        session['study_deckID'] = id
        session['current_index'] = 0
        session['correct'] = 0
        session['incorrect'] = 0
        session['study_startTime'] = time.time()

    # set session index to current index if unfinished sessions exist
    else:
        session['current_index'] = index

    # set card_list to the session list
    card_list = session['shuffled_cards']

    total = len(card_list)  # total num of cards
    card = card_list[index]  # current card onfo
    card_id = card[0]  # cardID

    # request is POST, get the form data and add to database
    if request.method == 'POST':
        # process responses if user is logged in
        if userID():
            # get card mode
            response_type = card_list[index][2]
            # get already answered or not
            answered = request.form.get('answered') == 'true'

            # if mode is flashcard
            if response_type == 'flashcard':
                print("FLASHCARD")
                response = request.form.get('response')  # get response

                # update stats
                if response == "correct":
                    result = True

                elif response == "incorrect":
                    result = False

                else:
                    result = None

                if result is not None:
                    updateCardStats(result, card_id)

            # if mode is quiz and not alr answered
            elif response_type == 'quiz' and not answered:
                print("QUIZ")
                selected = request.form.get('quizAnswer')  # get response
                correct = card[11]  # get correct
                is_correct = str(selected) == str(correct)  # check if correct
                skipped = selected is None  # check if skipped

                print(selected)
                print(correct)

                result = is_correct

                # skip showing answer if skip
                if skipped:
                    result = None

                print(result)

                # update stats
                if result is not None:
                    updateCardStats(result, card_id)

                    # return to same card but w/ correct ans info & answed = True
                    return render_template(
                        "card.html",
                        cards=card,
                        deck_id=id,
                        total=total,
                        index=index,
                        answered=True,
                        selected=selected,
                        correct=correct,
                        is_correct=is_correct
                    )

            # if mode is true/false and not alr answered
            elif response_type == 'TF' and not answered:
                print("TF")
                selected = request.form.get('tfAnswer')  # get response
                correct = card[13]  # get correct ans
                is_correct = str(selected) == str(correct)  # check if correct
                skipped = selected is None  # check if skipped

                print(selected)
                print(correct)

                result = is_correct

                # skip showing answer if skip
                if skipped:
                    result = None

                # update stats
                if result is not None:
                    updateCardStats(result, card_id)

                    # return to same card but w/ correct ans info & answed = True
                    return render_template(
                        "card.html",
                        cards=card,
                        deck_id=id,
                        total=total,
                        index=index,
                        answered=True,
                        selected=selected,
                        correct=correct,
                        is_correct=is_correct
                    )

        # go to next page if next card exists
        if index + 1 < total:
            session['current_index'] = index + 1
            return redirect(url_for('Study', id=id, index=index + 1))

        # exit to deck page if there are no more cards
        else:
            endTime = time.time()  # get endtime
            if userID():
                # ----- STREAKS SYSTEM -----
                get_streak = """
                    SELECT user_lastStudied, user_streak,
                    user_longestStreak
                    FROM Users
                    WHERE user_ID = ?;
                """
                streaks = query_db(get_streak, (userID(),))

                # check difference between last studied and now
                diff = is_streak_eligible(streaks[0][0])

                # if same day, pass
                if diff == 0:
                    pass

                # if the day after, update streak
                elif diff == 1:
                    # update user lastStudied & current streak
                    update_streak = """
                        UPDATE Users
                        SET user_lastStudied = datetime('now'),
                        user_streak = user_streak + 1
                        WHERE user_ID = ?;
                    """
                    get_db().execute(update_streak, (userID(),))
                    get_db().commit()

                    # update longest streak if current larger than longest
                    if streaks[1] > streaks[2]:
                        update_streak = """
                            UPDATE Users
                            SET user_longestStreak = user_streak
                            WHERE user_ID = ?;
                        """
                        get_db().execute(update_streak, (userID(),))
                        get_db().commit()

                # if more than 1 day after, reset streak
                else:
                    update_streak = """
                        UPDATE Users
                        SET user_lastStudied = datetime('now'),
                        user_streak = 1
                        WHERE user_ID = ?;
                    """
                    get_db().execute(update_streak, (userID(),))
                    get_db().commit()

                # ----- HISTORY SYSTEM -----
                card_correct = session.get('correct', 0)
                card_incorrect = session.get('incorrect', 0)
                # calc study time
                study_duration = round(endTime - session.get(
                    'study_startTime', endTime
                ))

                # add info to stats DB
                update_history = """
                    INSERT INTO StudyHistory (
                        study_date, study_cardCount, study_correct,
                        study_incorrect, study_deckID, study_userID,
                        study_duration
                    )
                    VALUES (datetime('now'), ?, ?, ?, ?, ?, ?);
                """

                get_db().execute(update_history, (
                    total, card_correct, card_incorrect,
                    id, userID(), study_duration
                ))
                get_db().commit()

            # clear sessions after exit
            session.pop('shuffled_cards', None)
            session.pop('study_deckID', None)
            session.pop('current_index', None)
            session.pop('correct', None)
            session.pop('incorrect', None)
            session.pop('study_startTime', None)

            # redirect to deck page
            flash("✔ You Have Finished Studying This Deck!", "success")
            return redirect(url_for('Deck', id=id))

    # return the results for GET
    else:
        return render_template(
            "card.html",
            cards=card,
            deck_id=id,
            total=total,
            index=index,
            answered=False,
            correct=None,
            deck_info=deck_info
        )


# ---------- create a new deck ----------
@app.route('/decks/create/', methods=['GET', 'POST'])
def createDeck():
    # check if user is logged in
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
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
                        deck_name, deck_description, deck_creation,
                        deck_userID, deck_visibility
                    )
                    VALUES (?, ?, datetime('now'), ?, ?);
                """
            get_db().execute(sql, (
                deck_name, deck_description, userID(), deck_visibility
            ))
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
        card_type = request.form.get("cardType")

        if card_type == "flashcard":
            flashcard_question = request.form['cardQuestion']
            flashcard_answer = request.form['cardAnswer']
            flashcard_hint = request.form['cardHint']

            # check if the form data is not empty
            if not flashcard_question or not flashcard_answer:
                # reload the page with the error message
                flash("⚠ Question and Answer Fields Are Required.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            else:
                sql = """
                    INSERT INTO Flashcards (
                        card_deckID, card_creation,
                        card_hint, card_mode
                    )
                    VALUES (?, datetime('now'), ?, ?);
                """
                cursor = get_db().execute(sql, (
                    id,
                    flashcard_hint,
                    "flashcard"
                ))
                cardid = cursor.lastrowid

                flashcardContent = """
                    INSERT INTO FlashcardContent (
                        card_ID, flashcard_question, flashcard_answer
                    )
                    VALUES (?, ?, ?);
                """

                get_db().execute(flashcardContent, (
                    cardid,
                    flashcard_question,
                    flashcard_answer
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Created Successfully!", "success")
                return redirect(url_for('Deck', id=id))

        if card_type == "quiz":
            quizCorrect = request.form.get('quizAnswer')

            quiz_question = request.form['quizQuestion']
            quiz_answer1 = request.form['quizAnswer1']
            quiz_answer2 = request.form['quizAnswer2']
            quiz_answer3 = request.form['quizAnswer3']
            quiz_answer4 = request.form['quizAnswer4']
            quiz_hint = request.form['quizHint']

            if not quizCorrect:
                flash("⚠ Please Select the Correct Answer.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            elif not quiz_question or not quiz_answer1 or not quiz_answer2 or not quiz_answer3 or not quiz_answer4:
                flash("⚠ Question and Answer Fields Are Required.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            else:
                sql = """
                    INSERT INTO Flashcards (
                        card_deckID, card_creation,
                        card_hint, card_mode
                    )
                    VALUES (?, datetime('now'), ?, ?);
                """

                cursor = get_db().execute(sql, (
                    id,
                    quiz_hint,
                    "quiz"
                ))
                cardid = cursor.lastrowid

                quizContent = """
                    INSERT INTO QuizContent (
                    card_ID, quiz_question, quiz_answer1,
                    quiz_answer2, quiz_answer3,
                    quiz_answer4, quiz_correct
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """

                get_db().execute(quizContent, (
                    cardid,
                    quiz_question,
                    quiz_answer1,
                    quiz_answer2,
                    quiz_answer3,
                    quiz_answer4,
                    quizCorrect
                ))

                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Created Successfully!", "success")
                return redirect(url_for('Deck', id=id))

        if card_type == "TF":
            tfCorrect = request.form.get('tfAnswer')
            tf_question = request.form['tfQuestion']
            tf_hint = request.form['tfHint']

            print(f"""
                tfCorrect: {tfCorrect}
                tf_question: {tf_question}
                tf_hint: {tf_hint}
            """)

            if not tfCorrect:
                flash("⚠ Please Select the Correct Answer.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            elif not tf_question:
                flash("⚠ Question Field Is Required.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            else:
                sql = """
                    INSERT INTO Flashcards (
                        card_deckID, card_creation,
                        card_hint, card_mode
                    )
                    VALUES (?, datetime('now'), ?, ?);
                """

                cursor = get_db().execute(sql, (
                    id,
                    tf_hint,
                    "TF"
                ))
                cardid = cursor.lastrowid

                tfContent = """
                    INSERT INTO TrueFalseContent (
                        card_ID, tf_question, tf_correct
                    )
                    VALUES (?, ?, ?);
                """

                get_db().execute(tfContent, (
                    cardid,
                    tf_question,
                    tfCorrect
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
                    SET deck_name = ?, deck_description = ?,
                    deck_visibility = ?
                    WHERE deck_ID = ?
                    AND deck_userID = ?;
                """
            get_db().execute(sql, (
                deck_name, deck_description, deck_visibility, id, userID()
            ))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('Decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description,
                deck_creation, deck_visibility
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
            SELECT deck_name, deck_ID, deck_creation, deck_userID
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    deck_info = query_db(sql_deck, (id, userID()))

    # check if deckinfo is not empty
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("Decks"))

    if deck_info[0][3] != userID():
        flash("⚠ You Do Not Own This Deck. You Cannot Create a Card.", "error")
        return redirect(url_for("Decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_type = request.form.get("cardType")

        if card_type == "flashcard":
            flashcard_question = request.form['cardQuestion']
            flashcard_answer = request.form['cardAnswer']
            flashcard_hint = request.form['cardHint']

            # check if the form data is not empty
            if not flashcard_question or not flashcard_answer:
                # reload the page with the error message
                flash("⚠ Question and Answer Fields Are Required.", "error")
                sql_card = """
                    SELECT card_ID, card_question,
                    card_answer, card_creation, card_hint
                    FROM Flashcards
                    WHERE card_ID = ?
                    AND card_deckID = ?;
                """
                card = query_db(sql_card, (card_id, id), one=True)
                return redirect(url_for('editCard', id=id, card_id=card_id))

            else:
                sql = """
                    UPDATE Flashcards
                    SET card_hint = ?, card_mode = ?
                    WHERE card_ID = ?;
                """
                get_db().execute(sql, (
                    flashcard_hint,
                    "flashcard",
                    card_id
                ))
                get_db().commit()

                quizContent = """
                    INSERT INTO FlashcardContent (
                        flashcard_question, flashcard_answer, card_ID
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(card_ID) DO UPDATE SET
                    flashcard_question = EXCLUDED.flashcard_question,
                    flashcard_answer = EXCLUDED.flashcard_answer
                """
                get_db().execute(quizContent, (
                    flashcard_question,
                    flashcard_answer,
                    card_id
                ))
                get_db().commit()

                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('Deck', id=id))

        if card_type == "quiz":
            quizCorrect = request.form.get('quizAnswer')

            quiz_question = request.form['quizQuestion']
            quiz_answer1 = request.form['quizAnswer1']
            quiz_answer2 = request.form['quizAnswer2']
            quiz_answer3 = request.form['quizAnswer3']
            quiz_answer4 = request.form['quizAnswer4']
            quiz_hint = request.form['quizHint']

            if not quizCorrect:
                flash("⚠ Please Select the Correct Answer.", "error")
                return redirect(url_for('editCard', id=id, card_id=card_id))

            elif not quiz_question or not quiz_answer1 or not quiz_answer2 or not quiz_answer3 or not quiz_answer4:
                flash("⚠ Question and Answer Fields Are Required.", "error")
                return redirect(url_for('editCard', id=id, card_id=card_id))

            else:
                sql = """
                    UPDATE Flashcards
                    SET card_hint = ?, card_mode = ?
                    WHERE card_ID = ?;
                """
                get_db().execute(sql, (
                    quiz_hint,
                    "quiz",
                    card_id
                ))
                get_db().commit()

                quizContent = """
                    INSERT INTO QuizContent (
                        quiz_question, quiz_answer1, quiz_answer2,
                        quiz_answer3, quiz_answer4, quiz_correct,
                        card_ID
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (card_ID) DO UPDATE SET
                    quiz_question = EXCLUDED.quiz_question,
                    quiz_answer1 = EXCLUDED.quiz_answer1,
                    quiz_answer2 = EXCLUDED.quiz_answer2,
                    quiz_answer3 = EXCLUDED.quiz_answer3,
                    quiz_answer4 = EXCLUDED.quiz_answer4,
                    quiz_correct = EXCLUDED.quiz_correct
                """
                get_db().execute(quizContent, (
                    quiz_question,
                    quiz_answer1,
                    quiz_answer2,
                    quiz_answer3,
                    quiz_answer4,
                    quizCorrect,
                    card_id
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('Deck', id=id))

        if card_type == "TF":
            tfCorrect = request.form.get('tfAnswer')
            tf_question = request.form['tfQuestion']
            tf_hint = request.form['tfHint']

            if not tfCorrect:
                flash("⚠ Please Select the Correct Answer.", "error")
                return redirect(url_for('editCard', id=id, card_id=card_id))

            elif not tf_question:
                flash("⚠ Question Field Is Required.", "error")
                return redirect(url_for('editCard', id=id, card_id=card_id))

            else:
                sql = """
                    UPDATE Flashcards
                    SET card_hint = ?, card_mode = ?
                    WHERE card_id = ?;
                """
                get_db().execute(sql, (
                    tf_hint,
                    "TF",
                    card_id
                ))
                get_db().commit()

                tfContent = """
                    INSERT INTO TrueFalseContent (
                        tf_question, tf_correct, card_ID
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT (card_ID) DO UPDATE SET
                    tf_question = EXCLUDED.tf_question,
                    tf_correct = EXCLUDED.tf_correct
                """
                get_db().execute(tfContent, (
                    tf_question,
                    tfCorrect,
                    card_id
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('Deck', id=id))

    # if request method is GET, return the sql results
    else:
        # get card info
        card_sql = """
            SELECT Flashcards.card_ID,
            Flashcards.card_creation,
            Flashcards.card_mode,
            Flashcards.card_hint,
            FlashcardContent.flashcard_question,
            FlashcardContent.flashcard_answer,
            QuizContent.quiz_question,
            QuizContent.quiz_answer1,
            QuizContent.quiz_answer2,
            QuizContent.quiz_answer3,
            QuizContent.quiz_answer4,
            QuizContent.quiz_correct,
            TrueFalseContent.tf_question,
            TrueFalseContent.tf_correct
            FROM Flashcards
            LEFT JOIN FlashcardContent ON Flashcards.card_ID = FlashcardContent.card_ID
            LEFT JOIN QuizContent ON Flashcards.card_ID = QuizContent.card_ID
            LEFT JOIN TrueFalseContent ON Flashcards.card_ID = TrueFalseContent.card_ID
            WHERE Flashcards.card_ID = ?;
        """
        card = query_db(card_sql, (card_id,))

        print(card)

        # check if card is not empty
        if not card:
            flash("⚠ Invalid Card...", "error")
            return redirect(url_for('Deck', id=id))

        card = list(card[0])

        # set None values to empty str
        index = 0
        for i in card:
            if i is None:
                card[index] = ""
            index += 1

        print(card)

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

        # if all checks pass update user info into database
        else:
            # hash passwords
            hashed_password = generate_password_hash(password)
            usersql = """
                    INSERT INTO Users (
                        user_name, user_password, user_creation
                    )
                    VALUES (?, ?, datetime('now'));
                """
            cursor = get_db().execute(usersql, (username, hashed_password))
            userid = cursor.lastrowid

            # create settings for the new user
            settingssql = """
                    INSERT INTO Settings (
                        settings_userID
                    )
                    VALUES (?);
                """
            get_db().execute(settingssql, (userid,))
            get_db().commit()

            flash("✔ Account Created Successfully! Please Log In.", "success")
            return render_template("login.html")

    else:
        return render_template("signup.html")


# ---------- profile ----------
@app.route('/profile/', methods=['GET', 'POST'])
def profile():
    # check if user is logged in
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
        flash("""
            ⚠ You Are Not Logged In. Please Log In to See Your Profile.
        """, "error")
        return redirect(url_for('home'))

    # get email
    getEmail = """
        SELECT email
        FROM Users
        WHERE user_ID = ?
    """
    emailSQL = query_db(getEmail, (userID(),))[0][0]
    if emailSQL is None:
        email = ""
    else:
        email = emailSQL

    if request.method == "POST":
        # get forms
        actionUsername = request.form.get('actionUsername')
        actionEmail = request.form.get('actionEmail')
        actionPassword = request.form.get('actionPassword')
        Delete = request.form.get('DeleteAccount')
        Reset = request.form.get('ResetAccount')

        print(f"Delete: {Delete} | Reset: {Reset}")

        if Delete == 'True':
            delete_user = """
                DELETE FROM Users
                WHERE user_ID = ?;
            """
            get_db().execute(delete_user, (userID(),))
            get_db().commit()

            # remove all sessions
            session.clear()

            flash("✔ Account deleted successfully.", "success")
            return redirect(url_for('home'))

        if Reset == 'True':
            currentDetails = """
                SELECT user_name, user_password, user_creation
                FROM Users
                WHERE user_ID = ?
            """
            details = query_db(currentDetails, (userID(),))[0]

            print(details)

            delete_user = """
                DELETE FROM Users
                WHERE user_ID = ?;
            """
            get_db().execute(delete_user, (userID(),))
            get_db().commit()

            # remove all sessions
            session.clear()

            usersql = """
                    INSERT INTO Users (
                        user_name, user_password, user_creation
                    )
                    VALUES (?, ?, ?);
                """
            get_db().execute(usersql, (details[0], details[1], details[2]))
            get_db().commit()

            getuserID = """
                SELECT user_ID
                FROM Users
                WHERE user_name = ?
                LIMIT 1;
            """
            userid = query_db(getuserID, (details[0],))[0]

            # create settings for the new user
            settingssql = """
                    INSERT INTO Settings (
                        settings_userID
                    )
                    VALUES (?);
                """
            get_db().execute(settingssql, (userid))
            get_db().commit()

            session['username'] = details[0]
            session['userID'] = query_db(
                "SELECT user_ID FROM Users WHERE user_name = ?",
                (details[0],), one=True
            )[0]

            flash("✔ Account reset successfully.", "success")
            return redirect(url_for('profile'))

        # remove email if form is remove
        if actionEmail == "remove":
            removeEmail = """
                UPDATE Users
                SET email = NULL
                WHERE user_ID = ?
            """
            get_db().execute(removeEmail, (userID(),))
            get_db().commit()
            flash("✔ Recovery email removed.", "success")
            return redirect(url_for('profile'))

        # change email if form is change
        elif actionEmail == "changeEmail":
            newEmail = request.form['newEmail']

            update_email = """
                UPDATE Users
                SET email = ?
                WHERE user_ID = ?;
            """
            get_db().execute(update_email, (newEmail, userID(),))
            get_db().commit()
            flash("✔ Email updated.", "success")

            return redirect(url_for('profile'))

        # change username if form is change
        elif actionUsername == "changeUsername":
            newUsername = request.form['newUsername']

            usernameList = """
                    SELECT user_name
                    FROM Users
                    WHERE user_name = ?;
                """
            username_list = query_db(usernameList, (newUsername,))

            # check if the username and password are not empty
            if not newUsername:
                flash("⚠ You must enter a username.", "error")
                return redirect(url_for('profile'))

            # check if the username already exists in the database
            elif username_list:
                flash("⚠ Username Already Exists.", "error")
                return redirect(url_for('profile'))

            else:
                update_username = """
                    UPDATE Users
                    SET user_name = ?
                    WHERE user_ID = ?;
                """
                get_db().execute(update_username, (newUsername, userID(),))
                get_db().commit()
                flash("✔ Username updated.", "success")

                return redirect(url_for('profile'))

        # change password if form is change
        elif actionPassword == "changePassword":
            newPassword = request.form['newPassword']

            # hash passwords
            hashed_password = generate_password_hash(newPassword)

            update_password = """
                UPDATE Users
                SET user_password = ?
                WHERE user_ID = ?;
            """
            get_db().execute(update_password, (hashed_password, userID(),))
            get_db().commit()
            flash("✔ Password updated.", "success")

            return redirect(url_for('profile'))

        else:
            flash("⚠ Invalid Action.", "error")
            return redirect(url_for('profile'))

    else:
        # check if user is logged in
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

        # check if results exists just in case
        if not results:
            flash("⚠ User Details Not Found. Logging Out.", "error")
            return redirect(url_for('logout'))

        # obfuscate email
        if email:
            obfuscatedEmail = obfuscate_email(email)
        else:
            obfuscatedEmail = "No Email Added"

        # return the results
        return render_template(
            "profile.html",
            results=results[0],
            format_date=format_date,
            time_ago=time_ago,
            email=email,
            obfuscatedEmail=obfuscatedEmail
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
    # check if user is logged in
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
        flash("⚠ You Are Not Logged In. Please Log In to See Stats.", "error")
        return redirect(url_for('home'))

    # get correct and incorrect totals
    userAnswerStats = """
            SELECT SUM(stats_correct), SUM(stats_incorrect)
            FROM UserCardStats
            WHERE stats_userID = ?;
        """
    answer_stats = query_db(userAnswerStats, (userID(),))[0]

    # get total number of decks
    userDeckStats = """
        SELECT COUNT(deck_ID)
        FROM Decks
        WHERE deck_userID = ?;
    """
    deck_stats = query_db(userDeckStats, (userID(),))

    # get total number of cards
    userCardStats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID AND Decks.deck_userID = ?;
    """
    card_stats = query_db(userCardStats, (userID(),))

    # get num of flashcards
    flashcardStats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'flashcard';
    """
    flashcard_stats = query_db(flashcardStats, (userID(),))

    # get num of quizes cards
    quizStats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'quiz';
    """
    quiz_stats = query_db(quizStats, (userID(),))

    # get num of true/false cards
    tfStats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'TF';
    """
    tf_stats = query_db(tfStats, (userID(),))

    # get user stats
    userStats = """
        SELECT user_name, user_creation,
        user_streak, user_longestStreak
        FROM Users
        WHERE user_ID = ?;
    """
    user_stats = query_db(userStats, (userID(),))

    # format join date to DD/Month/YYYY
    joinDate = format_date(user_stats[0][1])

    # get num of private decks
    privateStats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'private'
        AND deck_userID = ?;
    """
    private_stats = query_db(privateStats, (userID(),))

    # get num of unlisted decks
    unlistedStats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'unlisted'
        AND deck_userID = ?;
    """
    unlisted_stats = query_db(unlistedStats, (userID(),))

    # get num of public decks
    publicStats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'public'
        AND deck_userID = ?;
    """
    public_stats = query_db(publicStats, (userID(),))

    # get total study time
    studyTime = """
        SELECT SUM(study_duration)
        FROM StudyHistory
        WHERE study_userID = ?;
        """
    totalDuration = query_db(studyTime, (userID(),))[0][0]
    if totalDuration is not None:
        if totalDuration >= 3600:
            hours = totalDuration // 3600
            minutes = (totalDuration % 3600) // 60
            seconds = totalDuration % 60
            totalDuration = f"{hours}h {minutes}m {seconds}s"

        elif totalDuration >= 60:
            minutes = totalDuration // 60
            seconds = totalDuration % 60
            totalDuration = f"{minutes}m {seconds}s"

        else:
            totalDuration = f"{totalDuration}s"
    else:
        totalDuration = "0s"

    # calculate correct %
    if answer_stats[0] is None:
        correctPercent = 0
    elif answer_stats[1] is None:
        correctPercent = 100
    else:
        correctPercent = round(
            (100 * answer_stats[0]) / (
                answer_stats[0] + answer_stats[1]
            ), 2
        )

    # get all study history data
    studyHistory = """
        SELECT StudyHistory.study_date, StudyHistory.study_cardCount,
        StudyHistory.study_correct, StudyHistory.study_incorrect,
        StudyHistory.study_duration, Decks.deck_name, Decks.deck_userID
        FROM StudyHistory, Decks
        WHERE StudyHistory.study_userID = ?
        AND StudyHistory.study_deckID = Decks.deck_ID
        ORDER BY StudyHistory.study_date DESC;
    """
    study_history = query_db(studyHistory, (userID(),))
    totalSessions = len(study_history)

    studyTotals = """
        SELECT SUM(study_cardCount)
        FROM StudyHistory
        WHERE study_userID = ?;
    """
    studytotals = query_db(studyTotals, (userID(),))

    # calculate skipped ensuring not errors
    if studytotals[0][0] is None:
        skipped = 0
        totalStudied = 0

    else:
        totalStudied = studytotals[0][0]
        if not answer_stats[0]:
            correct = 0
        else:
            correct = answer_stats[0]

        if not answer_stats[1]:
            incorrect = 0
        else:
            incorrect = answer_stats[1]

        skipped = studytotals[0][0] - correct - incorrect

    # return the results
    return render_template(
        "stats.html",
        answer_stats=answer_stats,
        deck_stats=deck_stats[0],
        card_stats=card_stats[0],
        flashcard_stats=flashcard_stats[0],
        quiz_stats=quiz_stats[0],
        tf_stats=tf_stats[0],
        user_stats=user_stats[0],
        joinDate=joinDate,
        private_stats=private_stats[0][0],
        unlisted_stats=unlisted_stats[0][0],
        public_stats=public_stats[0][0],
        study_history=study_history,
        correctPercent=correctPercent,
        totalDuration=totalDuration,
        totalSessions=totalSessions,
        totalStudied=totalStudied,
        skipped=skipped,
        studytotals=studytotals,
        userID=userID(),
        username=session.get('username', "USERNAME")
    )


# ---------- Settings ----------
@app.route('/settings/', methods=['POST', 'GET'])
def settings():
    # check if user is logged in
    if not userID():
        session.pop('username', None)
        session.pop('userID', None)
        flash("""
            ⚠ You Are Not Logged In. Please Log In to Change Themes.
        """, "error")
        return redirect(url_for('home'))

    if request.method == "POST":

        # get form data from other colour pickers
        bg = request.form.get('bg')
        bg2 = request.form.get('bg2')
        text = request.form.get('text')
        accent = request.form.get('accent')
        accentTXT = request.form.get('accentTXT')
        card = request.form.get('card')
        cardTXT = request.form.get('cardTXT')
        warning = request.form.get('warning')
        shadowFull = request.form.get('shadowFull')
        fontSize = request.form.get('fontSize')
        anim = request.form.get('animToggle')

        # check if animation is enabled
        if anim is None:
            enable = 0
        else:
            enable = 1

        print(shadowFull)

        # update themes
        update_settings = """
            UPDATE Settings
            SET settings_bg1 = ?, settings_bg2 = ?, settings_text = ?,
            settings_accentBG = ?, settings_accentTXT = ?, settings_cardBG = ?,
            settings_cardTXT = ?, settings_warning = ?, settings_shadow = ?,
            settings_fontSize = ?, settings_animation = ?
            WHERE settings_userID = ?;
        """
        get_db().execute(update_settings, (
            bg,
            bg2,
            text,
            accent,
            accentTXT,
            card,
            cardTXT,
            warning,
            shadowFull,
            fontSize,
            enable,
            userID()
        ),)
        get_db().commit()

        flash("✔ Changes Saved!", "success")

    # get themes
    settingsSQL = """
        SELECT settings_bg1, settings_bg2, settings_text,
        settings_accentBG, settings_accentTXT, settings_cardBG,
        settings_cardTXT, settings_warning, settings_shadow,
        settings_fontSize, settings_animation
        FROM Settings
        WHERE settings_userID = ?
    """
    settings = query_db(settingsSQL, (userID(),))[0]

    # convert 8 digit hex to alpha value from 0 to 1
    shadow_hex = settings[8]
    shadow_color = shadow_hex[:8]
    shadow_alpha = round(int(shadow_hex[7:], 16) / 255, 2)

    return render_template(
        "settings.html",
        settings=settings,
        shadow_color=shadow_color,
        shadow_alpha=shadow_alpha
    )


# ---------- Public Decks ----------
@app.route('/public/')
def public():
    # get form data
    sort_by = request.args.get('sort_by')
    order = request.args.get('order')
    # limit allowed values
    allowed_sort = {'deck_creation', 'deck_name', 'deck_description'}
    allowed_order = {'ASC', 'DESC'}

    if sort_by not in allowed_sort:
        sort_by = 'deck_creation'  # default sort by creation date

    if order not in allowed_order:
        order = 'DESC'  # default order descending

    sql = f"""
        SELECT deck_ID, deck_name, deck_description, deck_creation
        FROM Decks
        WHERE deck_visibility = 'public'
        ORDER BY {sort_by} {order};
    """
    result = query_db(sql)

    # return the results
    return render_template(
        "public.html",
        results=result,
        sort_by=sort_by,
        order=order
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
                SELECT Flashcards.card_hint,
                Flashcards.card_mode, Decks.deck_name
                FROM Flashcards, Decks;
            """
        card_list = query_db(sql1)

        a = """
            SELECT file_ID, file_type
            FROM Files
            WHERE file_userID = 0
            ORDER BY file_ID DESC;
        """
        b = query_db(a)

        return render_template("test.html", card_list=card_list, b=b)


# only run the app if app.py is executed directly
if __name__ == "__main__":
    app.run(debug=True)
