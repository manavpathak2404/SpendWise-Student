/**
 * SpendWise Student - Main Client-Side JavaScript
 * Handles dynamic category filtering, inline form validation, and delete confirmation dialogs.
 */

// Category mappings based on transaction type
const CATEGORIES = {
    income: ['Salary', 'Freelance', 'Allowance', 'Scholarship', 'Other'],
    expense: ['Food', 'Transport', 'Education', 'Shopping', 'Bills', 'Entertainment', 'Other']
};

/**
 * Updates the category select options dynamically based on selected type
 * @param {string} selectedType - 'income' or 'expense'
 * @param {string} currentSelectedCategory - previously selected category to preserve if valid
 */
function updateCategoryDropdown(selectedType, currentSelectedCategory = '') {
    const categorySelect = document.getElementById('category');
    if (!categorySelect) return;

    const categories = CATEGORIES[selectedType] || CATEGORIES.expense;
    
    // Clear existing options
    categorySelect.innerHTML = '<option value="" disabled>-- Select Category --</option>';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        if (cat.toLowerCase() === currentSelectedCategory.toLowerCase()) {
            option.selected = true;
        }
        categorySelect.appendChild(option);
    });

    // If no option is selected, select the first category by default
    if (!categorySelect.value && categories.length > 0) {
        categorySelect.value = categories[0];
    }
}

/**
 * Initializes transaction form validation and dynamic category filtering
 */
function initTransactionForm() {
    const form = document.getElementById('transactionForm');
    const typeSelect = document.getElementById('type');
    const categorySelect = document.getElementById('category');

    if (!form || !typeSelect || !categorySelect) return;

    // Initial category population
    const initialCategory = categorySelect.getAttribute('data-selected') || '';
    updateCategoryDropdown(typeSelect.value, initialCategory);

    // Dynamic category update on transaction type change
    typeSelect.addEventListener('change', function () {
        updateCategoryDropdown(this.value);
    });

    // Client-side inline form validation (no alert popups)
    form.addEventListener('submit', function (e) {
        let isValid = true;

        const titleInput = document.getElementById('title');
        const amountInput = document.getElementById('amount');
        const dateInput = document.getElementById('date');

        // 1. Title validation
        if (!titleInput.value.trim()) {
            titleInput.classList.add('is-invalid');
            isValid = false;
        } else if (titleInput.value.trim().length > 100) {
            titleInput.classList.add('is-invalid');
            isValid = false;
        } else {
            titleInput.classList.remove('is-invalid');
            titleInput.classList.add('is-valid');
        }

        // 2. Amount validation (must be number > 0)
        const amountVal = parseFloat(amountInput.value);
        if (isNaN(amountVal) || amountVal <= 0) {
            amountInput.classList.add('is-invalid');
            isValid = false;
        } else {
            amountInput.classList.remove('is-invalid');
            amountInput.classList.add('is-valid');
        }

        // 3. Category validation
        if (!categorySelect.value) {
            categorySelect.classList.add('is-invalid');
            isValid = false;
        } else {
            categorySelect.classList.remove('is-invalid');
            categorySelect.classList.add('is-valid');
        }

        // 4. Date validation
        if (!dateInput.value) {
            dateInput.classList.add('is-invalid');
            isValid = false;
        } else {
            dateInput.classList.remove('is-invalid');
            dateInput.classList.add('is-valid');
        }

        if (!isValid) {
            e.preventDefault();
            e.stopPropagation();
        }
    });

    // Real-time input clearing for invalid status
    ['title', 'amount', 'category', 'date'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => {
                if (el.classList.contains('is-invalid')) {
                    el.classList.remove('is-invalid');
                }
            });
        }
    });
}

/**
 * Indian Rupee formatter utility for client-side display
 * e.g. 120000.00 -> ₹1,20,000.00
 */
function formatINR(amount) {
    const val = parseFloat(amount);
    if (isNaN(val)) return '₹0.00';
    
    const isNegative = val < 0;
    const absVal = Math.abs(val).toFixed(2);
    const [intPart, decPart] = absVal.split('.');

    let formattedInt = '';
    if (intPart.length <= 3) {
        formattedInt = intPart;
    } else {
        const lastThree = intPart.substring(intPart.length - 3);
        let remaining = intPart.substring(0, intPart.length - 3);
        const groups = [];
        while (remaining.length > 2) {
            groups.push(remaining.substring(remaining.length - 2));
            remaining = remaining.substring(0, remaining.length - 2);
        }
        if (remaining) groups.push(remaining);
        groups.reverse();
        formattedInt = groups.join(',') + ',' + lastThree;
    }

    const res = `₹${formattedInt}.${decPart}`;
    return isNegative ? `-${res}` : res;
}

// Global modal trigger for delete confirmation (used in Phase 3)
let deleteModalInstance = null;
function confirmDelete(id, title) {
    const modalEl = document.getElementById('deleteConfirmModal');
    const deleteForm = document.getElementById('deleteTransactionForm');
    const itemTitleEl = document.getElementById('deleteItemTitle');

    if (modalEl && deleteForm && itemTitleEl) {
        deleteForm.action = `/delete/${id}`;
        itemTitleEl.textContent = `"${title}"`;
        if (!deleteModalInstance) {
            deleteModalInstance = new bootstrap.Modal(modalEl);
        }
        deleteModalInstance.show();
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initTransactionForm();
});
