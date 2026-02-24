# import libraries
from flask import Flask, g, render_template
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


@app.route('/decks/<int:id>')
def Deck(id):
    # show all flashcards for a single deck
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    results = query_db(sql, (id,))
    return render_template("deck.html", results=results)


@app.route('/decks/<int:id>/study/')
def Study(id):
    # get all flashcard info
    sql = """
            SELECT card_ID, card_question, card_answer, card_creation
            FROM Flashcards
            WHERE card_deckID = ?;
        """
    results = query_db(sql, (id,))
    return render_template("card.html", cards=results, deck_id=id)


if __name__ == "__main__":
    app.run(debug=True)
