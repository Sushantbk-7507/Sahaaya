/* Core UI interactions for Sahaaya */

document.addEventListener("DOMContentLoaded", () => {
    // Admin mobile sidebar toggle
    const sidebarToggle = document.getElementById("adminSidebarToggle");
    const sidebarNav = document.getElementById("adminSidebarNav");
    if (sidebarToggle && sidebarNav) {
        sidebarToggle.addEventListener("click", () => {
            sidebarNav.classList.toggle("open");
        });
    }

    // Dynamic assistance requirement rows on Add Organization page
    const addReqBtn = document.getElementById("addRequirementRowBtn");
    const reqContainer = document.getElementById("requirementRowsContainer");
    const reqTemplate = document.getElementById("requirementRowTemplate");
    if (addReqBtn && reqContainer && reqTemplate) {
        addReqBtn.addEventListener("click", () => {
            const clone = reqTemplate.content.cloneNode(true);
            const removeBtn = clone.querySelector(".remove-req-row");
            if (removeBtn) {
                removeBtn.addEventListener("click", (e) => {
                    e.target.closest(".requirement-row-card").remove();
                });
            }
            reqContainer.appendChild(clone);
        });

        reqContainer.querySelectorAll(".remove-req-row").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.target.closest(".requirement-row-card").remove();
            });
        });
    }

    // Confirmation prompts for destructive actions
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (e) => {
            const msg = form.getAttribute("data-confirm") || "Are you sure you want to proceed?";
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});
