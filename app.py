# import libraries
from flask import Flask, g, redirect, render_template, request, redirect, url_for
import sqlite3

DATABASE = 'database.db'

# initialise app
app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.route('/')
def home():
    return render_template("homepage.html")


# @app.route('/car/<int:id>')
# def Car(id):
#     # just one car based on the id
#     sql = """
#             SELECT *
#             FROM Cars, Makers
#             WHERE Makers.MakerID = Cars.MakerID
#             AND Cars.CarID = ?;
#         """
#     result = query_db(sql, (id, ), True)
#     return render_template("car.html", car=result)


@app.route('/decks/')
def Decks():
    # get all the decks id, name, and description
    sql = """
            SELECT deck_ID, deck_name, deck_description
            FROM Decks;
        """
    result = query_db(sql)
    return render_template("decks.html", results=result)


@app.route('/decks/<int:id>/')
def Deck(id):
    # show all flashcards for a single deck
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    sql_deck = """
                SELECT deck_name FROM Decks WHERE deck_ID = ?;
            """

    deck_name = query_db(sql_deck, (id,), True)[0]
    results = query_db(sql, (id,))
    return render_template("deck.html", results=results, deck_name=deck_name)


@app.route('/decks/<int:id>/study/<int:index>/')
def Study(id, index):
    # get all flashcard info
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    results = query_db(sql, (id,))
    total=len(results)

    card = results[index]

    return render_template(
        "card.html",
        cards=card,
        deck_id=id,
        total=total,
        index=index
        )


@app.route('/decks/create/', methods=['GET', 'POST'])
def createDeck():
    if request.method == "POST":
        deck_name = request.form['deckName']
        deck_description = request.form['deckDescription']
        sql = """
                INSERT INTO Decks (deck_name, deck_description)
                VALUES (?, ?);
            """
        get_db().execute(sql, (deck_name, deck_description))
        get_db().commit()
        return redirect(url_for('Decks'))
    else:
        # get all the decks id, name, and description
        sql = """
                SELECT deck_ID, deck_name, deck_description
                FROM Decks;
            """
        result = query_db(sql)
        return render_template("deckCreate.html", results=result)


@app.route('/decks/<int:id>/create/', methods=['GET', 'POST'])
def createCard(id):
    # get all the decks id, name, and description
    sql = """
            SELECT deck_ID, deck_name, deck_description
            FROM Decks;
        """
    result = query_db(sql)
    return render_template("deckCreate.html", results=result)


if __name__ == "__main__":
    app.run(debug=True)
