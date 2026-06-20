// define editable preview and hidden input
const cardQuestionEditable = document.getElementById("cardQuestion");
const cardQuestionInput = document.getElementById("cardQuestionInput");

const cardAnswerEditable = document.getElementById("cardAnswer");
const cardAnswerInput = document.getElementById("cardAnswerInput");

const cardHintInput = document.getElementById("cardHintInput");

const hintEditable = document.getElementById("hint");

// quiz elements
const quizQuestionEditable = document.getElementById("quizQuestion");
const quizQuestionInput = document.getElementById("quizQuestionInput");

const quizAnswer1Editable = document.getElementById("quizAnswer1");
const quizAnswer1Input = document.getElementById("quizAnswer1Input");

const quizAnswer2Editable = document.getElementById("quizAnswer2");
const quizAnswer2Input = document.getElementById("quizAnswer2Input");

const quizAnswer3Editable = document.getElementById("quizAnswer3");
const quizAnswer3Input = document.getElementById("quizAnswer3Input");

const quizAnswer4Editable = document.getElementById("quizAnswer4");
const quizAnswer4Input = document.getElementById("quizAnswer4Input");

const quizHintInput = document.getElementById("quizHintInput");

// true/false elements
const tfQuestionEditable = document.getElementById("tfQuestion");
const tfQuestionInput = document.getElementById("tfQuestionInput");

const tfHintInput = document.getElementById("tfHintInput");


// store original values cos .defaultValue does not work
const originalCardQuestion = cardQuestionInput.value;
const originalCardAnswer = cardAnswerInput.value;
const originalHint = cardHintInput.value;

const originalQuizQuestion = quizQuestionInput.value;
const originalQuizAnswer1 = quizAnswer1Input.value;
const originalQuizAnswer2 = quizAnswer2Input.value;
const originalQuizAnswer3 = quizAnswer3Input.value;
const originalQuizAnswer4 = quizAnswer4Input.value;

const originalTFQuestion = tfQuestionInput.value;


// set placeholders
const CARD_QUESTION_PLACEHOLDER = "{ Flashcard Question }*";
const CARD_ANSWER_PLACEHOLDER = "{ Flashcard Answer }*";
const HINT_PLACEHOLDER = "{ Hint Text }";

const QUIZ_QUESTION_PLACEHOLDER = "{ Quiz Question }*";
const QUIZ_ANSWER1_PLACEHOLDER = "{ Answer 1 }*";
const QUIZ_ANSWER2_PLACEHOLDER = "{ Answer 2 }*";
const QUIZ_ANSWER3_PLACEHOLDER = "{ Answer 3 }*";
const QUIZ_ANSWER4_PLACEHOLDER = "{ Answer 4 }*";

const TF_QUESTION_PLACEHOLDER = "{ Question }*";

// combine placeholders into arrays for easy access
const fields = [
    {editable: cardQuestionEditable, input: cardQuestionInput, placeholder: CARD_QUESTION_PLACEHOLDER, original: originalCardQuestion, form: "cardForm"},
    {editable: cardAnswerEditable, input: cardAnswerInput, placeholder: CARD_ANSWER_PLACEHOLDER, original: originalCardAnswer, form: "cardForm"},
    {editable: hintEditable, input: cardHintInput, placeholder: HINT_PLACEHOLDER, original: originalHint, form: "cardForm"},
    {editable: quizQuestionEditable, input: quizQuestionInput, placeholder: QUIZ_QUESTION_PLACEHOLDER, original: originalQuizQuestion, form: "quizForm"},
    {editable: quizAnswer1Editable, input: quizAnswer1Input, placeholder: QUIZ_ANSWER1_PLACEHOLDER, original: originalQuizAnswer1, form: "quizForm"},
    {editable: quizAnswer2Editable, input: quizAnswer2Input, placeholder: QUIZ_ANSWER2_PLACEHOLDER, original: originalQuizAnswer2, form: "quizForm"},
    {editable: quizAnswer3Editable, input: quizAnswer3Input, placeholder: QUIZ_ANSWER3_PLACEHOLDER, original: originalQuizAnswer3, form: "quizForm"},
    {editable: quizAnswer4Editable, input: quizAnswer4Input, placeholder: QUIZ_ANSWER4_PLACEHOLDER, original: originalQuizAnswer4, form: "quizForm"},
    {editable: hintEditable, input: quizHintInput, placeholder: HINT_PLACEHOLDER, original: originalHint, form: "quizForm"},
    {editable: tfQuestionEditable, input: tfQuestionInput, placeholder: TF_QUESTION_PLACEHOLDER, original: originalTFQuestion, form: "tfForm"},
    {editable: hintEditable, input: tfHintInput, placeholder: HINT_PLACEHOLDER, original: originalHint, form: "tfForm"}
];

const formFields = [
    {editable: cardQuestionEditable, input: cardQuestionInput},
    {editable: cardAnswerEditable, input: cardAnswerInput},
];

// last focused variable for inputter
let lastFocused = null;

// MathJax toggle
function toggleMathJax() {
    var checkBox = document.getElementById("MathJaxCheck");

    // if checked, render MathJax
    if (checkBox.checked) {
        MathJax.typesetPromise(fields.map(f => f.editable)); // render MathJax on all editable fields
    } 
    // else show raw MathJax code (input values)
    else {
        fields.forEach(f => {
            f.editable.innerText = f.input.value;
        });
    }
}

// event listeners for all editable fields
fields.forEach(({ editable, input, placeholder }) => {
    // remove placeholder on focus
    editable.addEventListener("focus", () => { // on focus
        lastFocused = editable;
        if (editable.innerText.trim() === placeholder) { // if text = placeholder
            editable.innerText = ""; // clear text
        }
        else { // else set preview text to input so MathJax unrenders
            editable.innerText = input.value;
        }
    });

    // render MathJax on unfocus
    editable.addEventListener("blur", () => { // when unfocused
        var checkBox = document.getElementById("MathJaxCheck");
        if (checkBox.checked) { // if MathJax rendering Enabled
            MathJax.typesetPromise([editable]); // render MathJax
        }
    });

    // update hidden input on input
    editable.addEventListener("input", () => { // on input
        let text = editable.innerText.trim();
        if (text === "") { // if text is empty
            editable.innerHTML = ""; // make sure its empty (removes <br>)
        }
        input.value = text; // update hidden input value to preview text
    });
});

// reset button
["cardForm", "quizForm", "tfForm"].forEach(formId => {
    const form = document.getElementById(formId);
    if (form) {
        form.addEventListener("reset", function() { // on reset button pressed
            fields.forEach(({ input, original, editable }) => {
                // manually set inputs to original values cos reset button does not reset hidden inputs
                input.value = original;
                
                if (original === "") {
                    editable.innerHTML = "";
                } 
                else {
                    editable.innerText = original;
                }
            });

            // render MathJax if enabled
            toggleMathJax()
        });
    }
});