// define editable preview and hidden input
const questionEditable = document.getElementById("question");
const questionInput = document.getElementById("questionInput");

const answerEditable = document.getElementById("answer");
const answerInput = document.getElementById("answerInput");

const hintEditable = document.getElementById("hint");
const hintInput = document.getElementById("hintInput");


// store original values cos .defaultValue is a bum
const originalQuestion = questionInput.value;
const originalAnswer = answerInput.value;
const originalHint = hintInput.value;

// set placeholders
const QUESTION_PLACEHOLDER = "{ Flashcard Question }*";
const ANSWER_PLACEHOLDER = "{ Flashcard Answer }*";
const HINT_PLACEHOLDER = "{ Hint Text }";

// last focused variable for inputter
let lastFocused = null;

// MathJax toggle
function toggleMathJax() {
    var checkBox = document.getElementById("MathJaxCheck");

    // if checked, render MathJax
    if (checkBox.checked) {
        MathJax.typesetPromise([questionEditable, answerEditable, hintEditable]);
    } 
    // else show raw MathJax code (input values)
    else {
        questionEditable.innerText = questionInput.value;
        answerEditable.innerText = answerInput.value;
        hintEditable.innerText = hintInput.value;
    }
}

// remove placeholder on focus
questionEditable.addEventListener("focus", () => { // on focus
    lastFocused = questionEditable;
    if (questionEditable.innerText.trim() === QUESTION_PLACEHOLDER) { // if text = placeholder
        questionEditable.innerText = ""; // clear text
    }
    else { // else set preview text to input so MathJax unrenders
        questionEditable.innerText = questionInput.value
    }
});

// render MathJax on unfocus
questionEditable.addEventListener("blur", () => { // when unfocused
    var checkBox = document.getElementById("MathJaxCheck");
    if (checkBox.checked) { // if MathJax rendering Enabled
        MathJax.typesetPromise([questionEditable]); // render MathJax
    }
});

// update hidden input on input
questionEditable.addEventListener("input", () => { // on input
    let text = questionEditable.innerText.trim();
    if (text === "") { // if text is empty
        questionEditable.innerHTML = ""; // make sure its empty (removes <br>)
    }
    questionInput.value = text; // update hidden input value to preview text
});


// remove placeholder on focus
answerEditable.addEventListener("focus", () => { // on focus
    lastFocused = answerEditable;
    if (answerEditable.innerText.trim() === ANSWER_PLACEHOLDER) { // if text = placeholder
        answerEditable.innerText = ""; // clear text
    }
    else { // else set preview text to input so MathJax unrenders
        answerEditable.innerText = answerInput.value
    }
});

// render MathJax on unfocus
answerEditable.addEventListener("blur", () => { // when unfocused
    var checkBox = document.getElementById("MathJaxCheck");
    if (checkBox.checked) {
        MathJax.typesetPromise([answerEditable]);
    }
});

// update hidden input on input
answerEditable.addEventListener("input", () => { // on input
    let text = answerEditable.innerText.trim();
    if (text === "") { // if text is empty
        answerEditable.innerHTML = ""; // make sure its empty (removes <br>)
    }
    answerInput.value = text;
});


// remove placeholder on focus
hintEditable.addEventListener("focus", () => { // on focus
    lastFocused = hintEditable;
    if (hintEditable.innerText.trim() === HINT_PLACEHOLDER) { // if text = placeholder
        hintEditable.innerText = ""; // clear text
    }
    else { // else set preview text to input so MathJax unrenders
        hintEditable.innerText = hintInput.value
    }
});

// render MathJax on unfocus
hintEditable.addEventListener("blur", () => { // when unfocused
    var checkBox = document.getElementById("MathJaxCheck");
    if (checkBox.checked) {
        MathJax.typesetPromise([hintEditable]);
    }
});

// update hidden input on input
hintEditable.addEventListener("input", () => { // on input
    let text = hintEditable.innerText.trim();
    console.log(text);
    if (text === "") { // if text is empty
        hintEditable.innerHTML = ""; // make sure its empty (removes <br>)
    }
    hintInput.value = text;
});

// reset button
const cardForm = document.getElementById("cardForm"); // define form element
if (cardForm) {
    cardForm.addEventListener("reset", function() { // on reset button pressed
        // manually set inputs to original values cos reset button is a bum
        questionInput.value = originalQuestion;
        answerInput.value = originalAnswer;
        hintInput.value = originalHint;

        // render MathJax if enabled
        toggleMathJax()

        if (originalQuestion === "") { // if original value is empty
            questionEditable.innerHTML = ""; // make sure its empty (removes <br>)
        } 
        else { // else, set text to original value
            questionEditable.innerText = originalQuestion;
        }

        if (originalAnswer === "") { // if original value is empty
            answerEditable.innerHTML = ""; // make sure its empty (removes <br>)
        } 
        else { // else, set text to original value
            answerEditable.innerText = originalAnswer;
        }

        if (originalHint === "") { // if original value is empty
            hintEditable.innerHTML = ""; // make sure its empty (removes <br>)
        } 
        else { // else, set text to original value
            hintEditable.innerText = originalHint;
        }
    });
}