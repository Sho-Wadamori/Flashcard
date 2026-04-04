// ---------- Character Inputter ----------

const panel = document.getElementById('characterPanel');
const characterOverlay = document.getElementById('characterPopup-overlay');

const toast = document.getElementById('toast');

function togglePanel() {
    panel.classList.toggle('open'); // add open class
    characterOverlay.classList.toggle('open'); // add open class
}

function closeDropdownPanel() {
    panel.classList.remove('open'); // remove open class
    characterOverlay.classList.remove('open'); // remove open class
}

function insertChar(char) {
    if (lastFocused) {
        lastFocused.innerText += char; // add char to preview
        lastFocused.dispatchEvent(new Event("input")); // trigger input event to update hidden input
    }

    else { // if not input is focused
        navigator.clipboard.writeText(char); // copy char to clipboard
        toast.classList.add('open');
        toast.innerText = "No input selected. " + char + " has been copied to clipboard."
        setTimeout(() => {
            toast.classList.remove('open');
        }, 2000);
    }
}

// listen for window resizing to prevent styling issues
let resizeTimer;
window.addEventListener('resize', () => {
    document.body.classList.add('no-transition');
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        document.body.classList.remove('no-transition');
    }, 100); // remove after 100ms
});