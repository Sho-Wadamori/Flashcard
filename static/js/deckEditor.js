// define editable preview and hidden input
const nameEditable = document.getElementById("deckName");
const nameInput = document.getElementById("deckInput");

const descriptionEditable = document.getElementById("deckDescription");
const descriptionInput = document.getElementById("descriptionInput");


// store original values cos .defaultValue is a bum
const originalName = nameInput.value;
const originalDescription = descriptionInput.value;

// set placeholders
const NAME_PLACEHOLDER = "{ Deck Name }*";
const DESCRPTION_PLACEHOLDER = "{ Deck Description }";

// last focused variable for inputter
let lastFocused = null;

// MathJax toggle
function toggleMathJax() {
    var checkBox = document.getElementById("MathJaxCheck");

    // if checked, render MathJax
    if (checkBox.checked) {
        MathJax.typesetPromise([nameEditable, descriptionEditable]);
    } 
    // else show raw MathJax code (input values)
    else {
        nameEditable.innerText = nameInput.value;
        descriptionEditable.innerText = descriptionInput.value;
    }
}

// remove placeholder on focus
nameEditable.addEventListener("focus", () => { // on focus
    lastFocused = nameEditable;
    if (nameEditable.innerText.trim() === NAME_PLACEHOLDER) { // if text = placeholder
        nameEditable.innerText = ""; // clear text
    }
    else { // else set preview text to input so MathJax unrenders
        nameEditable.innerText = nameInput.value
    }
});

// render MathJax on unfocus
nameEditable.addEventListener("blur", () => { // when unfocused
    var checkBox = document.getElementById("MathJaxCheck");
    if (checkBox.checked) { // if MathJax rendering Enabled
        MathJax.typesetPromise([nameEditable]);
    }
});

// update hidden input on input
nameEditable.addEventListener("input", () => { // on input
    let text = nameEditable.innerText.trim();
    if (text === "") { // if text is empty
        nameEditable.innerHTML = ""; // make sure its empty (removes <br>)
    }
    nameInput.value = text; // update hidden input value to preview text
});


// remove placeholder on focus
descriptionEditable.addEventListener("focus", () => { // on focus
    lastFocused = descriptionEditable;
    if (descriptionEditable.innerText.trim() === DESCRPTION_PLACEHOLDER) { // if text = placeholder
        descriptionEditable.innerText = ""; // clear text
    }
    else { // else set preview text to input so MathJax unrenders
        descriptionEditable.innerText = descriptionInput.value
    }
});

// render MathJax on unfocus
descriptionEditable.addEventListener("blur", () => { // when unfocused
    var checkBox = document.getElementById("MathJaxCheck");
    if (checkBox.checked) {
        MathJax.typesetPromise([descriptionEditable]);
    }
});

// update hidden input on input
descriptionEditable.addEventListener("input", () => { // on input
    let text = descriptionEditable.innerText.trim();
    if (text === "") { // if text is empty
        descriptionEditable.innerHTML = ""; // make sure its empty (removes <br>)
    }
    descriptionInput.value = text;
});


// reset button
const deckForm = document.getElementById("deckForm"); // define form element
if (deckForm) {
    deckForm.addEventListener("reset", function() { // on reset button pressed
        // manually set inputs to original values cos reset button is a bum
        nameInput.value = originalName;
        descriptionInput.value = originalDescription;

        // render MathJax if enabled
        toggleMathJax()

        if (originalName === "") { // if original value is empty
            nameEditable.innerHTML = ""; // make sure its empty (removes <br>)
        } 
        else { // else, set text to original value
            nameEditable.innerText = originalName;
        }

        if (originalDescription === "") { // if original value is empty
            descriptionEditable.innerHTML = ""; // make sure its empty (removes <br>)
        } 
        else { // else, set text to original value
            descriptionEditable.innerText = originalDescription;
        }
    });
}