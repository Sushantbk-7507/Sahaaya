/* Client-side Form Validation matching Server-side Constraints */

document.addEventListener("DOMContentLoaded", () => {
    const regForm = document.getElementById("registerForm");
    if (regForm) {
        const pwd = document.getElementById("regPassword");
        const confirmPwd = document.getElementById("regConfirmPassword");
        const feedback = document.getElementById("passwordMatchFeedback");

        const validateMatch = () => {
            if (!pwd || !confirmPwd || !feedback) return true;
            if (confirmPwd.value && pwd.value !== confirmPwd.value) {
                confirmPwd.setCustomValidity("Passwords do not match.");
                feedback.textContent = "Passwords do not match.";
                feedback.classList.remove("d-none");
                return false;
            }
            confirmPwd.setCustomValidity("");
            feedback.classList.add("d-none");
            return true;
        };

        if (pwd && confirmPwd) {
            pwd.addEventListener("input", validateMatch);
            confirmPwd.addEventListener("input", validateMatch);
        }

        regForm.addEventListener("submit", (e) => {
            const strongEnough = pwd && pwd.value.length >= 8 && /[A-Za-z]/.test(pwd.value) && /\d/.test(pwd.value);
            if (pwd && !strongEnough) {
                pwd.setCustomValidity("Password must be at least 8 characters with letters and numbers.");
            } else if (pwd) {
                pwd.setCustomValidity("");
            }
            if (!validateMatch() || !regForm.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            regForm.classList.add("was-validated");
        });
    }

    document.querySelectorAll("form.needs-validation").forEach((form) => {
        if (form.id === "registerForm") return;
        form.addEventListener("submit", (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });
});
