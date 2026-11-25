/* Explore Organizations Search & Loading State Enhancements */

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("exploreSearchInput");
    const categorySelect = document.getElementById("exploreCategorySelect");
    const suggestionsBox = document.getElementById("searchSuggestionsBox");
    const exploreForm = document.getElementById("exploreFilterForm");
    const searchSpinner = document.getElementById("searchLoadingSpinner");

    if (exploreForm && searchSpinner) {
        exploreForm.addEventListener("submit", () => {
            searchSpinner.classList.remove("d-none");
        });
    }

    if (!searchInput || !suggestionsBox) {
        return;
    }

    let debounceTimer = null;

    const escapeHtml = (text) => {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    };

    const fetchSuggestions = async () => {
        const q = searchInput.value.trim();
        if (q.length < 2) {
            suggestionsBox.classList.remove("show");
            suggestionsBox.innerHTML = "";
            return;
        }
        const category = categorySelect ? categorySelect.value : "";
        const params = new URLSearchParams({ q, category });

        try {
            const resp = await fetch(`/api/organizations/search?${params.toString()}`);
            if (!resp.ok) return;
            const items = await resp.json();

            if (!items.length) {
                suggestionsBox.innerHTML =
                    '<div class="p-3 text-muted small">No verified matches found for that query.</div>';
                suggestionsBox.classList.add("show");
                return;
            }

            suggestionsBox.innerHTML = items
                .map(
                    (org) => `
                    <a href="/organization/${org.id}" class="search-suggestion-item">
                        <div class="fw-semibold text-dark">${escapeHtml(org.organization_name)}</div>
                        <div class="small text-muted">
                            ${escapeHtml(org.category)} &bull; ${escapeHtml(org.area)}, ${escapeHtml(org.city)} (${escapeHtml(org.pincode)})
                        </div>
                    </a>`
                )
                .join("");
            suggestionsBox.classList.add("show");
        } catch (_err) {
            suggestionsBox.classList.remove("show");
        }
    };

    searchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchSuggestions, 220);
    });

    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.classList.remove("show");
        }
    });
});
