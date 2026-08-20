# Flashcard Maker
A website where you can create your own flashcards and study them.

> [!CAUTION]
> Please change the SECRET_KEY in the app.py file to your own long and random string.
```
app.config['SECRET_KEY'] = "YOUR-STRING-HERE"
```

## Features:
- create flashcards with a question and answer
- create quiz with a question and 4 possible answers
- create a true/false card
- organise cards into decks
- edit and delete decks and cards
- study cards and track progress
- login and sign up to decks
- view statistics of your study progress
- make decks public and share them with others
- use keyboard shortcuts to navigate quickly
- change page theme and font size to your liking
- Type with mathematical symbols using LaTeX in flashcards
- Special character inputter to easily input special characters
- and much more

## How to run
Download the code and run the python file. Open 127.0.0.1:5000 in your browser and create a new account.

## How to get started
1. Sign up by clicking the Sign Up/Login button on the top right
2. Click "View Decks" in the navbar and click the + to create a new deck.
3. Type in the name of the deck and click save
4. Click on the deck and click on the + to create a new deck
5. Type in the input fields. You can change card modes by changing the selector on the top right
6. Click save to save the card. Click the start studying button to start studying
7. Click the Flashcard to reveal the answer. Click the next button to go to the next card.
8. For more help, open the help popup using the ctrl + / shortcut

## Tips
- Click the "Click here to start studying!" button to begin studying a deck
- Flip the card and reveal the answer by clicking on the card or pressing the "Space" key on your keyboard
- You can view the hint text by hovering your mouse over the "Hint💡" text
- You can move to the next/previous card by pressing the arrows (> or <) or pressing the right/left arrow keys on your keyboard
- You can track how many you got right by clicking one of the options (Correct, Incorrect, or Skip) for Flashcards, or clicking one of the options for quiz/trueFalse
- You can also press the keys 1, 2, 3 to select them using your keyboard
- When creating a new card, select a mode and enter in the Question, Answer, and (optionally) a hint. Click the reset button to reset everything and submit when you are done!
- You can type special characters through the Special Character Inputter. Click the "⌨ Special Characters" button to open it.
- You can also display math equations using MathJax. Click on the "🛈 MathJax Help" button above to learn more. Eg, \\( x = { -b \pm \sqrt{ b^{ 2 } -4ac } \over 2a } \\)
- On the deck page, you can sort the grid of flashcards by Question, Answer, or Creation Date.
- You can edit and delete decks on the deck page. Click the ⋮ button on the top right of each card to reveal a dropdown of options. There is also an "expand" or "collapse" option that expands a card if some of the text is cut off with an ...
- Note that you can close all popups by clicking the "escape" key or clicking outside of the popup
- Click the "Back" button to return back to your collection of decks. You can create a new deck by clicking the + card on the top left of the page.
- You can also set your deck visibility to private (default), unlisted, or public. Private decks are only visible to you, unlisted decks can be viewed or studied by anyone with the link, and public decks are visible to everyone.
- There are additional options in the ⋮ button dropdown menu such as Study and Share.
You can share the deck link to others, with options for Whatsapp, Email, Facebook, Twitter, Reddit, Pinterest, and LinkedIn
- There is also an additional filtering option to only show Private, Unlisted, or Public decks.
Remember to clear filters to view all your decks!