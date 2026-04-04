// load html brefore running
document.addEventListener("DOMContentLoaded", () => {

    // ---------- Render Scientific Text for each instance (ONLY STATIC) ----------
    document.querySelectorAll(".scientific").forEach(i => {
        if (i.textContent.includes('\\(')) { 
            MathJax.typesetPromise([i]);
        }
    });


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

});

