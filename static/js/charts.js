/* SpendWise Student - Dashboard Charts */

(() => {
    "use strict";

    const formatMoney = (value) => {
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0
        }).format(Number(value) || 0);
    };

    const showMessage = (canvas, message) => {
        if (!canvas) return;

        const parent = canvas.parentElement;

        if (parent) {
            parent.innerHTML = `
                <div class="text-center text-muted p-4">
                    ${message}
                </div>
            `;
        }
    };

    document.addEventListener("DOMContentLoaded", async () => {
        const incomeExpenseCanvas =
            document.getElementById("incomeExpenseChart");

        const categoryCanvas =
            document.getElementById("categoryChart");

        if (!incomeExpenseCanvas && !categoryCanvas) return;

        if (typeof Chart === "undefined") {
            showMessage(
                incomeExpenseCanvas,
                "Charts could not load. Please refresh the page."
            );

            showMessage(
                categoryCanvas,
                "Charts could not load. Please refresh the page."
            );

            return;
        }

        try {
            const response = await fetch("/chart-data", {
                headers: {
                    Accept: "application/json"
                }
            });

            if (!response.ok) {
                throw new Error("Failed to load chart data.");
            }

            const data = await response.json();

            /* Income and Expenses Chart */

            if (incomeExpenseCanvas) {
                const monthly = Array.isArray(data.monthly)
                    ? data.monthly
                    : [];

                if (monthly.length === 0) {
                    showMessage(
                        incomeExpenseCanvas,
                        "Add transactions to see your income and expenses."
                    );
                } else {
                    new Chart(incomeExpenseCanvas, {
                        type: "line",

                        data: {
                            labels: monthly.map(item => item.month),

                            datasets: [
                                {
                                    label: "Income",
                                    data: monthly.map(
                                        item => Number(item.income) || 0
                                    ),
                                    borderColor: "#16a34a",
                                    backgroundColor: "rgba(22,163,74,0.12)",
                                    fill: true,
                                    tension: 0.35,
                                    borderWidth: 2.5
                                },
                                {
                                    label: "Expenses",
                                    data: monthly.map(
                                        item => Number(item.expense) || 0
                                    ),
                                    borderColor: "#dc2626",
                                    backgroundColor: "rgba(220,38,38,0.08)",
                                    fill: true,
                                    tension: 0.35,
                                    borderWidth: 2.5
                                }
                            ]
                        },

                        options: {
                            responsive: true,
                            maintainAspectRatio: false,

                            interaction: {
                                mode: "index",
                                intersect: false
                            },

                            plugins: {
                                legend: {
                                    position: "bottom"
                                },

                                tooltip: {
                                    callbacks: {
                                        label: context =>
                                            `${context.dataset.label}: ${formatMoney(context.parsed.y)}`
                                    }
                                }
                            },

                            scales: {
                                y: {
                                    beginAtZero: true,

                                    ticks: {
                                        callback: value => formatMoney(value)
                                    }
                                }
                            }
                        }
                    });
                }
            }

            /* Expense Categories Chart */

            if (categoryCanvas) {
                const categories = Array.isArray(data.categories)
                    ? data.categories
                    : [];

                if (categories.length === 0) {
                    showMessage(
                        categoryCanvas,
                        "Add some expenses to see your category breakdown."
                    );
                } else {
                    new Chart(categoryCanvas, {
                        type: "doughnut",

                        data: {
                            labels: categories.map(
                                item => item.category
                            ),

                            datasets: [
                                {
                                    data: categories.map(
                                        item => Number(item.total) || 0
                                    ),

                                    backgroundColor: [
                                        "#4f46e5",
                                        "#0ea5e9",
                                        "#14b8a6",
                                        "#f59e0b",
                                        "#f97316",
                                        "#ec4899",
                                        "#8b5cf6",
                                        "#64748b"
                                    ],

                                    borderWidth: 3,
                                    borderColor: "#ffffff",
                                    hoverOffset: 7
                                }
                            ]
                        },

                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            cutout: "63%",

                            plugins: {
                                legend: {
                                    position: "bottom"
                                },

                                tooltip: {
                                    callbacks: {
                                        label: context =>
                                            `${context.label}: ${formatMoney(context.parsed)}`
                                    }
                                }
                            }
                        }
                    });
                }
            }
        } catch (error) {
            console.error("Dashboard chart error:", error);

            showMessage(
                incomeExpenseCanvas,
                "Unable to load chart data. Please refresh the page."
            );

            showMessage(
                categoryCanvas,
                "Unable to load chart data. Please refresh the page."
            );
        }
    });
})();
