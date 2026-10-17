/* SpendWise Student - Main JavaScript */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    // Automatically dismiss alerts
    document.querySelectorAll(".alert-dismissible").forEach((alert) => {
        window.setTimeout(() => {
            if (alert.isConnected) {
                const closeButton = alert.querySelector(".btn-close");

                if (closeButton) {
                    closeButton.click();
                }
            }
        }, 5000);
    });

    // Transaction form validation
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }

            form.classList.add("was-validated");
        });
    });

    // Update transaction category options
    const typeSelect = document.getElementById("type");
    const categorySelect = document.getElementById("category");

    if (typeSelect && categorySelect) {
        const updateCategories = () => {
            const type = typeSelect.value;

            const categories = type === "income"
                ? [
                    "Allowance",
                    "Scholarship",
                    "Salary",
                    "Freelance",
                    "Gift",
                    "Other"
                ]
                : [
                    "Food",
                    "Transport",
                    "Education",
                    "Shopping",
                    "Entertainment",
                    "Health",
                    "Bills",
                    "Other"
                ];

            const previousValue = categorySelect.value;

            categorySelect.replaceChildren();

            categories.forEach((category) => {
                const option = document.createElement("option");
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });

            if (categories.includes(previousValue)) {
                categorySelect.value = previousValue;
            }
        };

        typeSelect.addEventListener("change", updateCategories);
    }
});

// Confirm transaction deletion
function confirmDelete(id, title) {
    const form = document.getElementById("deleteTransactionForm");
    const titleElement = document.getElementById("deleteItemTitle");
    const modalElement = document.getElementById("deleteConfirmModal");

    if (form) {
        form.action = `/delete/${id}`;
    }

    if (titleElement) {
        titleElement.textContent = title || "this transaction";
    }

    if (modalElement && typeof bootstrap !== "undefined") {
        bootstrap.Modal.getOrCreateInstance(modalElement).show();
    } else if (form && window.confirm(`Delete "${title}"?`)) {
        form.submit();
    }
}
