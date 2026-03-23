// ----- Scientific Text Renderer -----
function escapeHTML(text) { // prevent html tags
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function renderScientific(text) { // convert _{} and ^{} to sub/sup
    return escapeHTML(text) // remove html tags
        .replace(/\^\{([^}]+)\}/g, '<sup>$1</sup>') // superscripts
        .replace(/_\{([^}]+)\}/g, '<sub>$1</sub>'); // subscripts
}

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
    const form = document.getElementById("cardForm"); // define form element


    // ---------- Render Scientific Text for each instance (ONLY STATIC) ----------
    document.querySelectorAll(".scientific").forEach(i => {
        i.innerHTML = renderScientific(i.textContent);
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
            questionElement.innerHTML = renderScientific(raw); // render scientific text
        }
    }

    function AnswerAction() { // update answer preview
        let raw = answerInput.value;
        if (raw == "") {
            answerElement.textContent = "{ Flashcard Answer }";
        }
        else {
            answerElement.innerHTML = renderScientific(raw); // render scientific text
        }
    }

    function HintAction() { // update hint preview
        let raw = hintInput.value;
        if (raw == "") {
            hintElement.textContent = "{ Hint text }";
        }
        else {
            hintElement.innerHTML = renderScientific(raw); // render scientific text
        }
    }

    // for Decks
    function DeckNameAction() {
        let raw = DeckNameInput.value;
        if (raw == "") {
            deckNameElement.textContent = "{ Deck Name }";
        }
        else {
            deckNameElement.innerHTML = renderScientific(raw); // render scientific text
        }
    }

    function DeckDescriptionAction() {
        let raw = DeckDescriptionInput.value;
        if (raw == "") {
            deckDescriptionElement.textContent = "{ Deck Description }";
        }
        else {
            deckDescriptionElement.innerHTML = renderScientific(raw); // render scientific text
        }
    }

    // ---------- Reset Button ----------
    if (form) {
        form.addEventListener("reset", function() { // on reset run func
            setTimeout(() => {
                QuestionAction();
                AnswerAction();
                HintAction();
            }, 30); // pause to allow form reset
        });
    }
 
});