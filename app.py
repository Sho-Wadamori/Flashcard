"""
This is a flashcard making app that allows users to:
- create decks of flashcards
- create flashcards with a question and answer
- edit and delete decks and flashcards
- study flashcards individually
- login and sign up to save their decks
- view their profile and stats
- track how many times they got a flashcard correct or incorrect
- Type with mathematical symbols using LaTeX in flashcards
"""

# import libraries

import random  # for randomising card list
import time  # for study timer

from datetime import (
    datetime,
    timezone
)  # for time formatting and converting

import sqlite3  # for database connection

from flask import (
    Flask,
    g,
    request,  # used to get method
    session,  # used to store user data (for login & study)
    redirect,  # used to redirect users to another page
    render_template,  # used to render html pages
    url_for,  # used to redirect users
    flash  # used for error messages
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)  # for user login password encryption

DATABASE = 'database.db'  # relative path to the database file

# initialise app
app = Flask(__name__)

# set a secret key for sessions (should be in a seperate secure file)
app.config['SECRET_KEY'] = "8y9awhDWdhHfw8ghgrgdgGRgDEgwndaiundIUDNu1823892e8h"


# ---------- FLASK SETUP ----------
def get_db():
    """connect to the database"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute("PRAGMA foreign_keys = ON")  # enable on delete cascade
    return db


@app.teardown_appcontext
def close_connection(_exception):
    """auto close the database connection at the end of each request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# simplify database queries
def query_db(query, args=(), one=False):
    """simplify database queries"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# ---------- convert YYYY-MM-DD HH:MM:SS to x minutes/hours/days ago ----------
def time_ago(date_string):
    """convert YYYY-MM-DD HH:MM:SS to x minutes/hours/days ago"""
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)

    # convert to local zone
    local_dt = dt.astimezone()
    now = datetime.now().astimezone()  # local now

    diff = now - local_dt

    # if difference bigger than a day
    if diff.days > 0:
        return f"{diff.days} days ago"

    # if difference bigger than an hour
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hours ago"

    # if difference bigger than a minute
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minutes ago"


# ---------- return day difference ----------
def is_streak_eligible(last_datetime):
    """return day difference"""
    # convert str to datetime
    dt = datetime.strptime(last_datetime, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)  # set timezone to UTC
    dt = dt.astimezone()
    # convert datetime to day
    last_date = dt.date()

    # get today
    today = datetime.now().astimezone().date()

    # calculate difference in days
    diff = (today - last_date).days

    return diff


# ---------- update streak counter ----------
def update_streak():
    """update streak counter"""
    # get current streak & last studied
    get_streak = """
        SELECT user_lastStudied, user_streak
        FROM Users
        WHERE user_ID = ?;
    """
    streaks = query_db(get_streak, (user_id(),))
    # get days since last studied
    diff = is_streak_eligible(streaks[0][0])

    current_streak = int(streaks[0][1])

    # if difference is 2+ days, set streak to 0
    if diff >= 2:
        update_streaks = """
            UPDATE Users
            SET user_streak = 0
            WHERE user_ID = ?;
        """
        get_db().execute(update_streaks, (user_id(),))
        get_db().commit()

        current_streak = 0

    # return current streak
    return current_streak


# ---------- convert YYYY-MM-DD HH:MM:SS to DD/Month/YYYY ----------
def format_date(date_string):
    """convert YYYY-MM-DD HH:MM:SS to DD/Month/YYYY"""
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)

    # convert to local time
    local_dt = dt.astimezone()  # system local zone
    return local_dt.strftime("%d/%b/%Y")


# ---------- get user ID ----------
def user_id():
    """return the session userID"""
    return session.get('userID', 0)


# ---------- obfuscate email using astrisk ----------
def obfuscate_email(email):
    """obfuscate email using astrisk"""
    # split email to {firstpart} + @ + {domain}
    first_part, domain = email.split('@')
    # return with first part obfiscated
    return first_part[0] + '*****@' + domain


# ---------- layout page ----------
@app.context_processor
def uservar():
    """layout page"""
    # get all settings
    settings_sql = """
        SELECT settings_bg1, settings_bg2, settings_text,
        settings_accentBG, settings_accentTXT, settings_cardBG,
        settings_cardTXT, settings_warning, settings_shadow, settings_fontSize,
        settings_animation
        FROM Settings
        WHERE settings_userID = ?
    """
    user_settings = query_db(settings_sql, (user_id(),))[0]

    return {
        "username": session.get("username", "Guest"),
        "userID": session.get("userID", 0),
        "settings": user_settings
    }


# ---------- homepage ----------
@app.route('/')
def home():
    """homepage"""
    # give message to users not logged in
    if not user_id():
        flash("""
            🛈 You have limited Access.
            Please Login to create your own decks!
        """, "info")

    # check if unfinished study session exists
    can_resume = bool(
        session.get('study_deckID') and session.get('shuffled_cards')
    )

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
    public_decks = query_db(public_sql)

    # get stats if user is logged in
    if user_id():
        # get total study time
        study_time = """
            SELECT SUM(study_duration), SUM(study_cardCount)
            FROM StudyHistory
            WHERE study_userID = ?;
        """
        total_duration = query_db(study_time, (user_id(),))[0]

        # get answer stats
        user_answer_stats = """
            SELECT SUM(stats_correct), SUM(stats_incorrect)
            FROM UserCardStats
            WHERE stats_userID = ?;
        """
        answer_stats = query_db(user_answer_stats, (user_id(),))[0]

        # calculate time studied
        if total_duration[0] is not None:
            if total_duration[0] >= 3600:
                hours = total_duration[0] // 3600
                minutes = (total_duration[0] % 3600) // 60
                seconds = total_duration[0] % 60
                total_duration = f"{hours}h {minutes}m {seconds}s"

            elif total_duration[0] >= 60:
                minutes = total_duration[0] // 60
                seconds = total_duration[0] % 60
                total_duration = f"{minutes}m {seconds}s"

            else:
                total_duration = f"{total_duration[0]}s"
        else:
            total_duration = "0s"

        # get all study history data
        study_history = """
            SELECT *
            FROM StudyHistory
            WHERE study_userID = ?
        """
        total_sessions = len(query_db(study_history, (user_id(),)))

        current_streak = update_streak()

    # if not logged in
    else:
        total_duration = "0s"
        total_sessions = 0
        answer_stats = 0
        current_streak = ""

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
        totalDuration=total_duration,
        totalSessions=total_sessions,
        publicDecks=public_decks,
        answer_stats=answer_stats,
        currentStreak=current_streak
    )


# ---------- list all decks ----------
@app.route('/decks/', methods=['GET', 'POST'])
def decks():
    """list all decks"""
    if request.method == 'POST':
        # get bookmarked deck's ID
        bookmark_id = request.form.get('bookmarkID')

        # check whether bookmarked deck is already bookmarked
        clicked_bookmark = """
            SELECT deck_bookmarked
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
        deck_bookmark = query_db(clicked_bookmark, (bookmark_id, user_id(),))

        # get number of already bookmarked decks
        all_bookmark = """
            SELECT COUNT(*)
            FROM Decks
            WHERE deck_userID = ?
            AND deck_bookmarked = 1;
        """
        total_bookmarks = query_db(all_bookmark, (user_id(),))[0][0]

        if not deck_bookmark:
            flash("⚠ Something Went Wrong...", "error")
            return redirect(request.url)

        # if bookmarking
        if deck_bookmark[0][0] == 0:
            # if total bookmarked is >= 3 return error
            if total_bookmarks >= 3:
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
            get_db().execute(update_bookmark, (bookmark_id, user_id(),))
            get_db().commit()

        # if unbookmarking, set deck_bookmarked to 0
        else:
            update_bookmark = """
                UPDATE Decks
                SET deck_bookmarked = 0
                WHERE deck_ID = ?
                AND deck_userID = ?;
            """
            get_db().execute(update_bookmark, (bookmark_id, user_id(),))
            get_db().commit()

        return redirect(request.url)

    # if request is GET
    else:
        # get filtering and sorting info (must use f-string for sorting)
        filter_value = request.args.get('filter')
        sort_by = request.args.get('sort_by')
        order = request.args.get('order')
        allowed_filter = {'none', 'public', 'unlisted', 'private'}
        allowed_sort = {'deck_creation', 'deck_name', 'deck_description'}
        allowed_order = {'ASC', 'DESC'}

        if filter_value not in allowed_filter:
            filter_value = 'none'  # default filter none

        if sort_by not in allowed_sort:
            sort_by = 'deck_creation'  # default sort by creation date

        if order not in allowed_order:
            order = 'DESC'  # default order descending

        # if user is logged in show all their decks
        if user_id():
            # if filter is not none
            if filter_value != 'none':
                filter_sql = "AND deck_visibility = ?"
                filter_args = (user_id(), filter_value)
            else:
                filter_sql = ""
                filter_args = (user_id(),)

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

            bookmark_result = query_db(bookmark_sql, filter_args)

        # if user not logged in show public decks
        else:
            flash("""
            🛈 You are viewing public decks.
            Please Login to create your own decks!
        """, "info")
            return redirect(url_for("public"))

        bookmark_length = len(bookmark_result)

        # return the results
        return render_template(
            "decks.html",
            results=result,
            sort_by=sort_by,
            order=order,
            filter=filter_value,
            userID=user_id(),
            bookmarkResult=bookmark_result,
            bookmarkLength=bookmark_length
        )


# ---------- list all flashcards for a single deck ----------
@app.route('/decks/<int:deck_id>/')
def deck(deck_id):
    """list all flashcards for a single deck"""
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

    deck_info = query_db(sql_deck, (deck_id, user_id()), True)

    # kick out user if they dont meet these conditions
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("decks"))

    filter_value = request.args.get('filter')
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

    # fallback for invalid sort/order
    if filter_value not in allowed_filter:
        filter_value = 'none'  # default filter none
    if sort_by not in allowed_sort:
        sort_by = 'card_creation'  # default sort creation date
    if order not in allowed_order:
        order = 'DESC'  # default order descending

    # create filter query that we will inject
    if filter_value != 'none':
        filter_sql = f"AND (Flashcards.card_mode = '{filter_value}') "
    else:
        filter_sql = ""

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
        LEFT JOIN FlashcardContent
            ON Flashcards.card_ID = FlashcardContent.card_ID
        LEFT JOIN QuizContent
            ON Flashcards.card_ID = QuizContent.card_ID
        LEFT JOIN TrueFalseContent
            ON Flashcards.card_ID = TrueFalseContent.card_ID
        WHERE Flashcards.card_deckID = ?
        {filter_sql};
    """
    cards = query_db(card_sql, (deck_id,))

    # format results
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
            continue

        results.append((card[0], card[1], card[2], question, answer))

    # handeling sorting and ordering
    ordering = order == "DESC"

    # sort the list using lambda
    if sort_by == "card_answer":
        results.sort(key=lambda x: x[4], reverse=ordering)

    elif sort_by == "card_question":
        results.sort(key=lambda x: x[3], reverse=ordering)

    elif sort_by == "card_mode":
        results.sort(key=lambda x: x[2], reverse=ordering)

    else:
        results.sort(key=lambda x: x[1], reverse=ordering)

    # chek if the user is the owner of the deck
    is_owner = deck_info[3] == user_id()

    # check if the user can resume studying the deck
    can_resume = (
        session.get('study_deckID') == deck_id
    ) and (
        session.get('shuffled_cards') is not None
    )

    # return the results
    return render_template(
        "cards.html",
        results=results,
        deck_info=deck_info,
        time_ago=time_ago,
        format_date=format_date,
        filter=filter_value,
        sort_by=sort_by,
        order=order,
        is_owner=is_owner,
        can_resume=can_resume
    )


# ---------- delete a card ----------
@app.route(
    '/decks/<int:deck_id>/cards/<int:card_id>/delete/',
    methods=['POST']
)
def delete_card(deck_id, card_id):
    """delete a card"""
    # check if the deck id is valid and belongs to the user
    sql_deck = """
        SELECT deck_ID
        FROM Decks
        WHERE deck_ID = ?
        AND deck_userID = ?;
    """
    deck_info = query_db(sql_deck, (deck_id, user_id()), one=True)
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("decks"))

    # delete the card with the inputted card id
    sql = """
            DELETE FROM Flashcards
            WHERE card_ID = ?
            AND card_deckID = ?;
        """
    get_db().execute(sql, (card_id, deck_id))
    get_db().commit()
    # redirect to the deck page
    flash("✔ Card Deleted Successfuly.", "success")
    return redirect(url_for('deck', deck_id=deck_id))


# ---------- delete a deck ----------
@app.route('/decks/<int:deck_id>/delete/', methods=['POST'])
def delete_deck(deck_id):
    """delete a deck"""
    # delete the deck with the inputted deck id
    sql = """
            DELETE FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    get_db().execute(sql, (deck_id, user_id()))
    get_db().commit()
    # redirect to the deck page
    flash("✔ Deck Deleted Successfully", "success")
    return redirect(url_for('decks'))


# ---------- refresh session data on study ----------
@app.route('/decks/<int:deck_id>/study/start/')
def start_study(deck_id):
    """refresh session data on study"""
    # set session data to empty to remove previous list
    session.pop('shuffled_cards', None)
    session.pop('study_deckID', None)
    session.pop('current_index', None)
    session.pop('correct', None)
    session.pop('incorrect', None)
    session.pop('study_startTime', None)
    # redirect to study
    return redirect(url_for('study', deck_id=deck_id, index=0))


# ---------- redirect to study with saved index ----------
@app.route('/decks/<int:deck_id>/study/resume/')
def resume_study(deck_id):
    """redirect to study with saved index"""
    saved_index = session.get('current_index', 0)
    session['study_startTime'] = time.time()
    return redirect(url_for('study', deck_id=deck_id, index=saved_index))


def update_cardstats(result, card_id):
    """get the user's stats for the current card"""
    get_stats = """
        SELECT *
        FROM UserCardStats
        WHERE stats_cardID = ?
        AND stats_userID = ?;
    """
    card_stats = query_db(get_stats, (card_id, user_id()))

    # if the user got the card correct
    if result:
        # if the user has no stats for card, create new entry
        if not card_stats:
            add_stats = """
                INSERT INTO UserCardStats (
                    stats_correct, stats_userID, stats_cardID
                )
                Values (?, ?, ?)
            """
            # add 1 correct
            get_db().execute(add_stats, (1, user_id(), card_id))
            get_db().commit()

        # if the user has stats for the card, add 1 to correct
        else:
            update_stats = """
                UPDATE UserCardStats
                SET stats_correct = stats_correct + 1
                WHERE stats_cardID = ?
                AND stats_userID = ?
            """
            get_db().execute(update_stats, (card_id, user_id()))
            get_db().commit()

        session['correct'] = session.get('correct', 0) + 1

    # if the user got the card incorrect
    elif not result:
        # if the user has no stats for card, create new entry
        if not card_stats:
            add_stats = """
                INSERT INTO UserCardStats (
                    stats_incorrect, stats_userID, stats_cardID
                )
                Values (?, ?, ?)
            """
            # add 1 incorrect
            get_db().execute(add_stats, (1, user_id(), card_id))
            get_db().commit()

        # if the user has stats for card, add 1 to incorrect
        else:
            update_stats = """
                UPDATE UserCardStats
                SET stats_incorrect = stats_incorrect + 1
                WHERE stats_cardID = ?
                AND stats_userID = ?
            """
            get_db().execute(update_stats, (card_id, user_id()))
            get_db().commit()

        session['incorrect'] = session.get('incorrect', 0) + 1


# ---------- study a single card based on the index ----------
@app.route('/decks/<int:deck_id>/study/<int:index>/', methods=['GET', 'POST'])
def study(deck_id, index):
    """study a single card based on the index"""
    # check if the deck id is valid and belongs to the user
    sql_deck = """
        SELECT deck_ID, deck_userID, deck_visibility
        FROM Decks
        WHERE deck_ID = ?;
    """
    deck_info = query_db(sql_deck, (deck_id,), one=True)

    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("decks"))

    # check if deck is private and if user has permission to view it
    if deck_info[2] == 'private' and deck_info[1] != user_id():
        flash("⚠ You Do Not Have Permission to Study This Deck...", "error")
        return redirect(url_for("decks"))

    # get card IDs
    card_sql = """
        SELECT card_ID
        FROM Flashcards
        WHERE card_deckID = ?;
    """
    results = query_db(card_sql, (deck_id,))

    # check if deck is not empty
    if not results:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for('deck', deck_id=deck_id))

    # get session data
    current_session = session.get('shuffled_cards', None)
    current_session_deck = session.get('study_deckID', None)

    # reset all values and shuffle cards if no unfinished sessions
    if current_session_deck != deck_id or not current_session:
        temp_list = [list(item) for item in results]
        random.shuffle(temp_list)
        session['shuffled_cards'] = temp_list
        session['study_deckID'] = deck_id
        session['current_index'] = 0
        session['correct'] = 0
        session['incorrect'] = 0
        session['study_startTime'] = time.time()

    # set session index to current index if unfinished sessions exist
    else:
        session['current_index'] = index

    # set cardid_list to the session list
    cardid_list = session['shuffled_cards']

    total = len(cardid_list)  # total num of cards

    # check if index is valid
    if index < 0 or index >= total:
        flash("⚠ Invalid Card Index...", "error")
        return redirect(url_for('deck', deck_id=deck_id))

    # get current card info
    card_sql2 = """
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
        LEFT JOIN FlashcardContent
            ON Flashcards.card_ID = FlashcardContent.card_ID
        LEFT JOIN QuizContent
            ON Flashcards.card_ID = QuizContent.card_ID
        LEFT JOIN TrueFalseContent
            ON Flashcards.card_ID = TrueFalseContent.card_ID
        WHERE Flashcards.card_ID = ?;
    """
    card_result = query_db(card_sql2, (cardid_list[index][0],))

    # check if card exists (eg, deleted card)
    if not card_result:
        flash("⚠ A card was skipped during the study session.", "error")
        # remove card from session list
        cardid_list.pop(index)
        session['shuffled_cards'] = cardid_list

        # check if there are no more cards in deck
        if not cardid_list:
            session.pop('shuffled_cards', None)
            session.pop('study_deckID', None)
            session.pop('current_index', None)
            session.pop('correct', None)
            session.pop('incorrect', None)
            session.pop('study_startTime', None)

            flash("⚠ No More Cards in This Deck...", "error")
            return redirect(url_for('deck', deck_id=deck_id))

        # exit if card is last one
        if index >= len(cardid_list):
            session.pop('shuffled_cards', None)
            session.pop('study_deckID', None)
            session.pop('current_index', None)
            session.pop('correct', None)
            session.pop('incorrect', None)
            session.pop('study_startTime', None)

            # redirect to deck page
            flash("✔ You Have Finished Studying This Deck!", "success")
            flash("""
                🛈 Some cards have been skipped as they were removed.
            """, "info")
            return redirect(url_for('deck', deck_id=deck_id))

        # redirect to the next card
        return redirect(url_for(
            'study',
            deck_id=deck_id,
            index=index
        ))

    card_full_list = card_result[0]

    card_id = card_full_list[0]  # cardID

    # request is POST, get the form data and add to database
    if request.method == 'POST':
        # process responses if user is logged in
        if user_id():
            # get card mode
            response_type = card_full_list[2]
            # get already answered or not
            answered = request.form.get('answered') == 'true'

            # if mode is flashcard
            if response_type == 'flashcard':
                response = request.form.get('response')  # get response

                # update stats
                if response == "correct":
                    result = True

                elif response == "incorrect":
                    result = False

                else:
                    result = None

                if result is not None:
                    update_cardstats(result, card_id)

            # if mode is quiz and not alr answered
            elif response_type == 'quiz' and not answered:
                selected = request.form.get('quizAnswer')  # get response
                correct = card_full_list[11]  # get correct
                is_correct = str(selected) == str(correct)  # check if correct
                skipped = selected is None  # check if skipped

                result = is_correct

                # skip showing answer if skip
                if skipped:
                    result = None

                # update stats
                if result is not None:
                    update_cardstats(result, card_id)

                    # return w/ correct correct info & answed = True
                    return render_template(
                        "study.html",
                        cards=card_full_list,
                        deck_id=deck_id,
                        total=total,
                        index=index,
                        answered=True,
                        selected=selected,
                        correct=correct,
                        is_correct=is_correct
                    )

            # if mode is true/false and not alr answered
            elif response_type == 'TF' and not answered:
                selected = request.form.get('tfAnswer')  # get response
                correct = card_full_list[13]  # get correct ans
                is_correct = str(selected) == str(correct)  # check if correct
                skipped = selected is None  # check if skipped

                result = is_correct

                # skip showing answer if skip
                if skipped:
                    result = None

                # update stats
                if result is not None:
                    update_cardstats(result, card_id)

                    # return w/ correct info & answed = True
                    return render_template(
                        "study.html",
                        cards=card_full_list,
                        deck_id=deck_id,
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
            return redirect(url_for('study', deck_id=deck_id, index=index + 1))

        # exit to deck page if there are no more cards
        else:
            end_time = time.time()  # get endtime
            if user_id():
                # ----- STREAKS SYSTEM -----
                get_streak = """
                    SELECT user_lastStudied, user_streak,
                    user_longestStreak
                    FROM Users
                    WHERE user_ID = ?;
                """
                streaks = query_db(get_streak, (user_id(),))

                # check difference between last studied and now
                diff = is_streak_eligible(streaks[0][0])

                # if same day, pass
                if diff == 0:
                    pass

                # if the day after, update streak
                elif diff == 1:
                    # update user lastStudied & current streak
                    update_streak_sql = """
                        UPDATE Users
                        SET user_lastStudied = datetime('now'),
                        user_streak = user_streak + 1
                        WHERE user_ID = ?;
                    """
                    get_db().execute(update_streak_sql, (user_id(),))
                    get_db().commit()

                    # update longest streak if current larger than longest
                    if streaks[0][1] > streaks[0][2]:
                        update_streak_sql = """
                            UPDATE Users
                            SET user_longestStreak = user_streak
                            WHERE user_ID = ?;
                        """
                        get_db().execute(update_streak_sql, (user_id(),))
                        get_db().commit()

                # if more than 1 day after, reset streak
                else:
                    update_streak_sql = """
                        UPDATE Users
                        SET user_lastStudied = datetime('now'),
                        user_streak = 1
                        WHERE user_ID = ?;
                    """
                    get_db().execute(update_streak_sql, (user_id(),))
                    get_db().commit()

                # ----- HISTORY SYSTEM -----
                card_correct = session.get('correct', 0)
                card_incorrect = session.get('incorrect', 0)
                # calc study time
                study_duration = round(end_time - session.get(
                    'study_startTime', end_time
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
                    deck_id, user_id(), study_duration
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
            return redirect(url_for('deck', deck_id=deck_id))

    # return the results for GET
    else:
        return render_template(
            "study.html",
            cards=card_full_list,
            deck_id=deck_id,
            total=total,
            index=index,
            answered=False,
            correct=None,
            deck_info=deck_info
        )


# ---------- create a new deck ----------
@app.route('/decks/create/', methods=['GET', 'POST'])
def create_deck():
    """create a new deck"""
    # check if user is logged in
    if not user_id():
        session.pop('username', None)
        session.pop('userID', None)
        flash("⚠ You Are Not Logged In. Please Log In to Create a Deck.",
              "error")
        return redirect(url_for('decks'))
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
                deck_name, deck_description, user_id(), deck_visibility
            ))
            get_db().commit()
            # redirect to the decks list page
            flash("✔ Deck Created Successfully!", "success")
            return redirect(url_for('decks'))
    # if request method is GET, return the sql results
    else:
        deck_visibility = "private"  # default visibility
        return render_template("deckCreate.html", visibility=deck_visibility)


# ---------- create a new card ----------
@app.route('/decks/<int:deck_id>/create/', methods=['GET', 'POST'])
def create_card(deck_id):
    """create a new card"""
    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation, deck_userID
            FROM Decks
            WHERE deck_ID = ?;
        """
    deck_info = query_db(sql_deck, (deck_id,))

    # check if deck_info is not empty
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("decks"))

    if deck_info[0][3] != user_id():
        flash("⚠ You Do Not Own This Deck. You Cannot Create a Card.", "error")
        return redirect(url_for("decks"))

    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        card_type = request.form.get("cardType")

        if card_type == "flashcard":
            # get form info
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
                # insert info into Flashcards
                sql = """
                    INSERT INTO Flashcards (
                        card_deckID, card_creation,
                        card_hint, card_mode
                    )
                    VALUES (?, datetime('now'), ?, ?);
                """
                cursor = get_db().execute(sql, (
                    deck_id,
                    flashcard_hint,
                    "flashcard"
                ))
                # get id of last row
                cardid = cursor.lastrowid

                # insert info into FlashcardContent
                flashcard_content = """
                    INSERT INTO FlashcardContent (
                        card_ID, flashcard_question, flashcard_answer
                    )
                    VALUES (?, ?, ?);
                """

                get_db().execute(flashcard_content, (
                    cardid,
                    flashcard_question,
                    flashcard_answer
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Created Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

        if card_type == "quiz":
            # get form info
            quiz_correct = request.form.get('quizAnswer')

            quiz_question = request.form['quizQuestion']
            quiz_answer1 = request.form['quizAnswer1']
            quiz_answer2 = request.form['quizAnswer2']
            quiz_answer3 = request.form['quizAnswer3']
            quiz_answer4 = request.form['quizAnswer4']
            quiz_hint = request.form['quizHint']

            if not quiz_correct:
                flash("⚠ Please Select the Correct Answer.", "error")
                return render_template(
                    "cardCreate.html",
                    deck_info=deck_info[0]
                )

            elif (
                not quiz_question
                or not quiz_answer1
                or not quiz_answer2
                or not quiz_answer3
                or not quiz_answer4
            ):
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
                    deck_id,
                    quiz_hint,
                    "quiz"
                ))
                cardid = cursor.lastrowid

                quiz_content = """
                    INSERT INTO QuizContent (
                    card_ID, quiz_question, quiz_answer1,
                    quiz_answer2, quiz_answer3,
                    quiz_answer4, quiz_correct
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """

                get_db().execute(quiz_content, (
                    cardid,
                    quiz_question,
                    quiz_answer1,
                    quiz_answer2,
                    quiz_answer3,
                    quiz_answer4,
                    quiz_correct
                ))

                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Created Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

        if card_type == "TF":
            tf_correct = request.form.get('tfAnswer')
            tf_question = request.form['tfQuestion']
            tf_hint = request.form['tfHint']

            if not tf_correct:
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
                    deck_id,
                    tf_hint,
                    "TF"
                ))
                cardid = cursor.lastrowid

                tf_content = """
                    INSERT INTO TrueFalseContent (
                        card_ID, tf_question, tf_correct
                    )
                    VALUES (?, ?, ?);
                """

                get_db().execute(tf_content, (
                    cardid,
                    tf_question,
                    tf_correct
                ))

                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Created Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

    # if request method is GET, return the sql results
    else:
        # return deckinfo
        return render_template("cardCreate.html", deck_info=deck_info[0])


# ---------- edit a deck ----------
@app.route('/decks/<int:deck_id>/edit/', methods=['GET', 'POST'])
def edit_deck(deck_id):
    """edit a deck"""
    # if request method is POST, get the form data and insert into database
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']
        deck_visibility = request.form['deckVisibility']

        # check if the form data is not empty
        if not deck_name:
            # reload the page with the error message
            flash("⚠ A Deck Name is Required.", "error")
            return redirect(url_for('edit_deck', deck_id=deck_id))

        else:
            sql = """
                    UPDATE Decks
                    SET deck_name = ?, deck_description = ?,
                    deck_visibility = ?
                    WHERE deck_ID = ?
                    AND deck_userID = ?;
                """
            get_db().execute(sql, (
                deck_name,
                deck_description,
                deck_visibility,
                deck_id,
                user_id()
            ))
            get_db().commit()
            # redirect to the decks list page
            return redirect(url_for('decks'))
    # if request method is GET, return the sql results
    else:
        # get all the decks id, name, description, and creation date
        sql = """
                SELECT deck_ID, deck_name, deck_description,
                deck_creation, deck_visibility
                FROM Decks
                WHERE deck_ID = ? AND deck_userID = ?;
            """
        result = query_db(sql, (deck_id, user_id()))

        if not result:
            flash("⚠ Invalid Deck...", "error")
            return redirect(url_for("decks"))

        # return the results
        return render_template("deckEdit.html", results=result)


# ---------- edit a card ----------
@app.route(
    '/decks/<int:deck_id>/cards/<int:card_id>/edit/',
    methods=['GET', 'POST']
)
def edit_card(deck_id, card_id):
    """edit a card"""
    # get the deck name of the inputted deck id
    sql_deck = """
            SELECT deck_name, deck_ID, deck_creation, deck_userID
            FROM Decks
            WHERE deck_ID = ?
            AND deck_userID = ?;
        """
    deck_info = query_db(sql_deck, (deck_id, user_id()))

    # check if deckinfo is not empty
    if not deck_info:
        flash("⚠ Invalid Deck...", "error")
        return redirect(url_for("decks"))

    if deck_info[0][3] != user_id():
        flash("⚠ You Do Not Own This Deck. You Cannot Create a Card.", "error")
        return redirect(url_for("decks"))

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
                return redirect(url_for(
                    'edit_card', deck_id=deck_id, card_id=card_id
                ))

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

                quiz_content = """
                    INSERT INTO FlashcardContent (
                        flashcard_question, flashcard_answer, card_ID
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(card_ID) DO UPDATE SET
                    flashcard_question = EXCLUDED.flashcard_question,
                    flashcard_answer = EXCLUDED.flashcard_answer
                """
                get_db().execute(quiz_content, (
                    flashcard_question,
                    flashcard_answer,
                    card_id
                ))
                get_db().commit()

                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

        if card_type == "quiz":
            quiz_correct = request.form.get('quizAnswer')

            quiz_question = request.form['quizQuestion']
            quiz_answer1 = request.form['quizAnswer1']
            quiz_answer2 = request.form['quizAnswer2']
            quiz_answer3 = request.form['quizAnswer3']
            quiz_answer4 = request.form['quizAnswer4']
            quiz_hint = request.form['quizHint']

            if not quiz_correct:
                flash("⚠ Please Select the Correct Answer.", "error")
                return redirect(url_for(
                    'edit_card', deck_id=deck_id, card_id=card_id
                ))

            elif (
                not quiz_question
                or not quiz_answer1
                or not quiz_answer2
                or not quiz_answer3
                or not quiz_answer4
            ):
                flash("⚠ Question and Answer Fields Are Required.", "error")
                return redirect(url_for(
                    'edit_card', deck_id=deck_id, card_id=card_id
                ))

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

                quiz_content = """
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
                get_db().execute(quiz_content, (
                    quiz_question,
                    quiz_answer1,
                    quiz_answer2,
                    quiz_answer3,
                    quiz_answer4,
                    quiz_correct,
                    card_id
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

        if card_type == "TF":
            tf_correct = request.form.get('tfAnswer')
            tf_question = request.form['tfQuestion']
            tf_hint = request.form['tfHint']

            if not tf_correct:
                flash("⚠ Please Select the Correct Answer.", "error")
                return redirect(url_for(
                    'edit_card', deck_id=deck_id, card_id=card_id
                ))

            elif not tf_question:
                flash("⚠ Question Field Is Required.", "error")
                return redirect(url_for(
                    'edit_card', deck_id=deck_id, card_id=card_id
                ))

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

                tf_content = """
                    INSERT INTO TrueFalseContent (
                        tf_question, tf_correct, card_ID
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT (card_ID) DO UPDATE SET
                    tf_question = EXCLUDED.tf_question,
                    tf_correct = EXCLUDED.tf_correct
                """
                get_db().execute(tf_content, (
                    tf_question,
                    tf_correct,
                    card_id
                ))
                get_db().commit()
                # redirect to the deck page
                flash("✔ Card Updated Successfully!", "success")
                return redirect(url_for('deck', deck_id=deck_id))

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
            LEFT JOIN FlashcardContent
                ON Flashcards.card_ID = FlashcardContent.card_ID
            LEFT JOIN QuizContent
                ON Flashcards.card_ID = QuizContent.card_ID
            LEFT JOIN TrueFalseContent
                ON Flashcards.card_ID = TrueFalseContent.card_ID
            WHERE Flashcards.card_ID = ?;
        """
        card = query_db(card_sql, (card_id,))

        # check if card is not empty
        if not card:
            flash("⚠ Invalid Card...", "error")
            return redirect(url_for('deck', deck_id=deck_id))

        card = list(card[0])

        # set None values to empty str
        index = 0
        for i in card:
            if i is None:
                card[index] = ""
            index += 1

        return render_template(
            "cardEdit.html",
            deck_info=deck_info[0],
            cards=card
        )


# ---------- login ----------
@app.route('/login/', methods=['GET', 'POST'])
def login():
    """login page"""
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
                session.clear()
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
    """sign up page"""
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
    """profile page"""
    # check if user is logged in
    if not user_id():
        session.pop('username', None)
        session.pop('userID', None)
        flash("""
            ⚠ You Are Not Logged In. Please Log In to See Your Profile.
        """, "error")
        return redirect(url_for('home'))

    # get email
    get_email = """
        SELECT email
        FROM Users
        WHERE user_ID = ?
    """
    email_sql = query_db(get_email, (user_id(),))[0][0]
    if email_sql is None:
        email = ""
    else:
        email = email_sql

    if request.method == "POST":
        # get forms
        action_username = request.form.get('actionUsername')
        action_email = request.form.get('actionEmail')
        action_password = request.form.get('actionPassword')
        delete = request.form.get('DeleteAccount')
        reset = request.form.get('ResetAccount')

        if delete == 'True':
            delete_user = """
                DELETE FROM Users
                WHERE user_ID = ?;
            """
            get_db().execute(delete_user, (user_id(),))
            get_db().commit()

            # remove all sessions
            session.clear()

            flash("✔ Account deleted successfully.", "success")
            return redirect(url_for('home'))

        if reset == 'True':
            current_details = """
                SELECT user_name, user_password, user_creation
                FROM Users
                WHERE user_ID = ?
            """
            details = query_db(current_details, (user_id(),))[0]

            delete_user = """
                DELETE FROM Users
                WHERE user_ID = ?;
            """
            get_db().execute(delete_user, (user_id(),))
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

            get_userid = """
                SELECT user_ID
                FROM Users
                WHERE user_name = ?
                LIMIT 1;
            """
            userid = query_db(get_userid, (details[0],))[0]

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
        if action_email == "remove":
            remove_email = """
                UPDATE Users
                SET email = NULL
                WHERE user_ID = ?
            """
            get_db().execute(remove_email, (user_id(),))
            get_db().commit()
            flash("✔ Recovery email removed.", "success")
            return redirect(url_for('profile'))

        # change email if form is change
        elif action_email == "changeEmail":
            new_email = request.form['newEmail']

            update_email = """
                UPDATE Users
                SET email = ?
                WHERE user_ID = ?;
            """
            get_db().execute(update_email, (new_email, user_id(),))
            get_db().commit()
            flash("✔ Email updated.", "success")

            return redirect(url_for('profile'))

        # change username if form is change
        elif action_username == "changeUsername":
            new_username = request.form['newUsername']

            username_list = """
                    SELECT user_name
                    FROM Users
                    WHERE user_name = ?;
                """
            username_list = query_db(username_list, (new_username,))

            # check if the username and password are not empty
            if not new_username:
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
                get_db().execute(update_username, (new_username, user_id(),))
                get_db().commit()
                flash("✔ Username updated.", "success")

                return redirect(url_for('profile'))

        # change password if form is change
        elif action_password == "changePassword":
            new_password = request.form['newPassword']

            # hash passwords
            hashed_password = generate_password_hash(new_password)

            update_password = """
                UPDATE Users
                SET user_password = ?
                WHERE user_ID = ?;
            """
            get_db().execute(update_password, (hashed_password, user_id(),))
            get_db().commit()
            flash("✔ Password updated.", "success")

            return redirect(url_for('profile'))

        else:
            flash("⚠ Invalid Action.", "error")
            return redirect(url_for('profile'))

    else:
        # check if user is logged in
        if not user_id():
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

        results = query_db(sql, (user_id(),))

        # check if results exists just in case
        if not results:
            flash("⚠ User Details Not Found. Logging Out.", "error")
            return redirect(url_for('logout'))

        # obfuscate email
        if email:
            obfuscated_email = obfuscate_email(email)
        else:
            obfuscated_email = "No Email Added"

        # return the results
        return render_template(
            "profile.html",
            results=results[0],
            format_date=format_date,
            time_ago=time_ago,
            email=email,
            obfuscatedEmail=obfuscated_email
        )


# ---------- logout ----------
@app.route('/logout/')
def logout():
    """logout"""
    session.pop('username', None)
    session.pop('userID', None)
    flash("✔ Logged Out Successfully.", "success")
    return redirect(url_for('home'))


# ---------- stats ----------
@app.route('/stats/')
def stats():
    """stats page"""
    # check if user is logged in
    if not user_id():
        session.pop('username', None)
        session.pop('userID', None)
        flash("⚠ You Are Not Logged In. Please Log In to See Stats.", "error")
        return redirect(url_for('home'))

    # get correct and incorrect totals
    user_answer_stats = """
            SELECT SUM(stats_correct), SUM(stats_incorrect)
            FROM UserCardStats
            WHERE stats_userID = ?;
        """
    answer_stats = query_db(user_answer_stats, (user_id(),))[0]

    # get total number of decks
    user_deck_stats = """
        SELECT COUNT(deck_ID)
        FROM Decks
        WHERE deck_userID = ?;
    """
    deck_stats = query_db(user_deck_stats, (user_id(),))

    # get total number of cards
    user_card_stats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID AND Decks.deck_userID = ?;
    """
    card_stats = query_db(user_card_stats, (user_id(),))

    # get num of flashcards
    flashcard_stats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'flashcard';
    """
    flashcard_stats = query_db(flashcard_stats, (user_id(),))

    # get num of quizes cards
    quiz_stats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'quiz';
    """
    quiz_stats = query_db(quiz_stats, (user_id(),))

    # get num of true/false cards
    tf_stats = """
        SELECT COUNT(Flashcards.card_ID)
        FROM Flashcards, Decks
        WHERE Flashcards.card_deckID = Decks.deck_ID
        AND Decks.deck_userID = ?
        AND Flashcards.card_mode = 'TF';
    """
    tf_stats = query_db(tf_stats, (user_id(),))

    # get user stats
    user_stats = """
        SELECT user_name, user_creation,
        user_streak, user_longestStreak
        FROM Users
        WHERE user_ID = ?;
    """
    user_stats = query_db(user_stats, (user_id(),))

    # format join date to DD/Month/YYYY
    join_date = format_date(user_stats[0][1])

    # get num of private decks
    private_stats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'private'
        AND deck_userID = ?;
    """
    private_stats = query_db(private_stats, (user_id(),))

    # get num of unlisted decks
    unlisted_stats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'unlisted'
        AND deck_userID = ?;
    """
    unlisted_stats = query_db(unlisted_stats, (user_id(),))

    # get num of public decks
    public_stats = """
        SELECT COUNT(*)
        FROM Decks
        WHERE deck_visibility = 'public'
        AND deck_userID = ?;
    """
    public_stats = query_db(public_stats, (user_id(),))

    # get total study time
    study_time = """
        SELECT SUM(study_duration)
        FROM StudyHistory
        WHERE study_userID = ?;
        """
    total_duration = query_db(study_time, (user_id(),))[0][0]
    if total_duration is not None:
        # if more than 1hr
        if total_duration >= 3600:
            hours = total_duration // 3600
            minutes = (total_duration % 3600) // 60
            seconds = total_duration % 60
            total_duration = f"{hours}h {minutes}m {seconds}s"
        # if more than 1 min
        elif total_duration >= 60:
            minutes = total_duration // 60
            seconds = total_duration % 60
            total_duration = f"{minutes}m {seconds}s"

        else:
            total_duration = f"{total_duration}s"
    else:
        total_duration = "0s"

    # calculate correct %
    if answer_stats[0] is None:
        correct_percent = 0
    elif answer_stats[1] is None:
        correct_percent = 100
    else:
        correct_percent = round(
            (100 * answer_stats[0]) / (
                answer_stats[0] + answer_stats[1]
            ), 2
        )

    # get all study history data
    study_history_sql = """
        SELECT StudyHistory.study_date, StudyHistory.study_cardCount,
        StudyHistory.study_correct, StudyHistory.study_incorrect,
        StudyHistory.study_duration, Decks.deck_name, Decks.deck_userID
        FROM StudyHistory, Decks
        WHERE StudyHistory.study_userID = ?
        AND StudyHistory.study_deckID = Decks.deck_ID
        ORDER BY StudyHistory.study_date DESC;
    """
    study_history = query_db(study_history_sql, (user_id(),))
    total_sessions = len(study_history)

    study_totals = """
        SELECT SUM(study_cardCount)
        FROM StudyHistory
        WHERE study_userID = ?;
    """
    studytotals = query_db(study_totals, (user_id(),))

    # calculate skipped ensuring not errors
    if studytotals[0][0] is None:
        skipped = 0
        total_studied = 0

    else:
        total_studied = studytotals[0][0]
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
        joinDate=join_date,
        private_stats=private_stats[0][0],
        unlisted_stats=unlisted_stats[0][0],
        public_stats=public_stats[0][0],
        study_history=study_history,
        correctPercent=correct_percent,
        totalDuration=total_duration,
        totalSessions=total_sessions,
        totalStudied=total_studied,
        skipped=skipped,
        studytotals=studytotals,
        userID=user_id(),
        username=session.get('username', "USERNAME")
    )


# ---------- Settings ----------
@app.route('/settings/', methods=['POST', 'GET'])
def settings():
    """settings page"""
    # check if user is logged in
    if not user_id():
        session.pop('username', None)
        session.pop('userID', None)
        flash("""
            ⚠ You Are Not Logged In. Please Log In to Change Settings.
        """, "error")
        return redirect(url_for('home'))

    if request.method == "POST":

        # get form data from other colour pickers
        bg = request.form.get('bg')
        bg2 = request.form.get('bg2')
        text = request.form.get('text')
        accent = request.form.get('accent')
        accent_txt = request.form.get('accentTXT')
        card = request.form.get('card')
        card_txt = request.form.get('cardTXT')
        warning = request.form.get('warning')
        shadow_full = request.form.get('shadowFull')
        font_size = request.form.get('fontSize')
        anim = request.form.get('animToggle')

        # check if animation is enabled
        if anim is None:
            enable = 0
        else:
            enable = 1

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
            accent_txt,
            card,
            card_txt,
            warning,
            shadow_full,
            font_size,
            enable,
            user_id()
        ),)
        get_db().commit()

        flash("✔ Changes Saved!", "success")

    # get themes
    settings_sql = """
        SELECT settings_bg1, settings_bg2, settings_text,
        settings_accentBG, settings_accentTXT, settings_cardBG,
        settings_cardTXT, settings_warning, settings_shadow,
        settings_fontSize, settings_animation
        FROM Settings
        WHERE settings_userID = ?
    """
    settings_values = query_db(settings_sql, (user_id(),))[0]

    # convert 8 digit hex to alpha value from 0 to 1
    shadow_hex = settings_values[8]
    shadow_color = shadow_hex[:8]
    shadow_alpha = round(int(shadow_hex[7:], 16) / 255, 2)

    return render_template(
        "settings.html",
        settings=settings_values,
        shadow_color=shadow_color,
        shadow_alpha=shadow_alpha
    )


# ---------- Public Decks ----------
@app.route('/public/')
def public():
    """public decks page"""
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


# only run the app if app.py is executed directly
if __name__ == "__main__":
    app.run()
