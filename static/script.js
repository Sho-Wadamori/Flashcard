// ----- Scientific Text Renderer -----
// function escapeHTML(text) {
//     return text
//         .replace(/&/g, "&amp;")
//         .replace(/</g, "&lt;")
//         .replace(/>/g, "&gt;")
//         .replace(/"/g, "&quot;")
//         .replace(/'/g, "&#39;");
// }
// no longer needed as we are using textContent instead of innerHTML & conflicts with mathjax


// load html brefore running
document.addEventListener("DOMContentLoaded", () => {
    // ---------- Define Elements ----------
    // for card inputs:
    const questionInput = document.getElementById("questionInput");
    const answerInput = document.getElementById("answerInput");
    const hintInput = document.getElementById("hintInput");
    
    // for preview:
    const questionElement = document.getElementById("question");
    const answerElement = document.getElementById("answer");
    const hintElement = document.getElementById("hint");

    // for deck inputs:
    const DeckNameInput = document.getElementById("deckInput");
    const DeckDescriptionInput = document.getElementById("descriptionInput");
    
    const deckNameElement = document.getElementById("deckName");
    const deckDescriptionElement = document.getElementById("deckDescription");
    
    // for reset button:
    const cardForm = document.getElementById("cardForm"); // define form element
    const deckForm = document.getElementById("deckForm"); // define form element
    
    
    // ---------- Render Scientific Text for each instance (ONLY STATIC) ----------
    document.querySelectorAll(".scientific").forEach(i => {
        if (i.textContent.includes('\\(')) {
            MathJax.typesetPromise([i]);
        }
    });


    // ---------- Run on input ----------
    if (questionInput && questionElement) {
        questionInput.oninput = QuestionAction;
        QuestionAction();
    }
    if (answerInput && answerElement) {
        answerInput.oninput = AnswerAction;
        AnswerAction();
    }
    if (hintInput && hintElement) {
        hintInput.oninput = HintAction;
        HintAction();
    }

    if (DeckNameInput) {
        DeckNameInput.oninput = DeckNameAction;
        DeckNameAction();
    }
    if (DeckDescriptionInput) {
        DeckDescriptionInput.oninput = DeckDescriptionAction;
        DeckDescriptionAction();
    }



    // ---------- Update Preview Functions ----------
    // for Cards
    function QuestionAction() { // update question preview
        let raw = questionInput.value;
        if (raw == "") {
            questionElement.textContent = "{ Flashcard Question }";
        }
        else {
            questionElement.textContent = raw; // render scientific text
            MathJax.typesetPromise([questionElement]);
        }
    }

    function AnswerAction() { // update answer preview
        let raw = answerInput.value;
        if (raw == "") {
            answerElement.textContent = "{ Flashcard Answer }";
        }
        else {
            answerElement.textContent = raw; // render scientific text
            MathJax.typesetPromise([answerElement]);
        }
    }

    function HintAction() { // update hint preview
        let raw = hintInput.value;
        if (raw == "") {
            hintElement.textContent = "{ Hint text }";
        }
        else {
            hintElement.textContent = raw; // render scientific text
            MathJax.typesetPromise([hintElement]);
        }
    }

    // for Decks
    function DeckNameAction() {
        let raw = DeckNameInput.value;
        if (raw == "") {
            deckNameElement.textContent = "{ Deck Name }";
        }
        else {
            deckNameElement.textContent = raw; // render scientific text
            MathJax.typesetPromise([deckNameElement]);
        }
    }

    function DeckDescriptionAction() {
        let raw = DeckDescriptionInput.value;
        if (raw == "") {
            deckDescriptionElement.textContent = "{ Deck Description }";
        }
        else {
            deckDescriptionElement.textContent = raw; // render scientific text
            MathJax.typesetPromise([deckDescriptionElement]);
        }
    }

    // ---------- Password reveal system ----------
    function passwordReveal() {
        var password = document.getElementById("password");
        var confirm = document.getElementById("confirm_password");

        if (password.type === "password") {
            password.type = "text";
            confirm.type = "text";
        } else {
            password.type = "password";
            confirm.type = "password";
        }
    }

    // ---------- Reset Button ----------
    if (cardForm) {
        cardForm.addEventListener("reset", function() { // on reset run func
            setTimeout(() => {
                QuestionAction();
                AnswerAction();
                HintAction();
            }, 30); // pause to allow form reset
        });
    }

    if (deckForm) {
        deckForm.addEventListener("reset", function() { // on reset run func
            setTimeout(() => {
                DeckDescriptionAction();
                DeckNameAction();
            }, 30); // pause to allow form reset
        });
    }
 
});

