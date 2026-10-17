/* SpendWise Student - Dashboard Charts */

(() => {
    "use strict";

    const money = (value) => {
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0
        }).format(Number(value) || 0);
    };

    const showChartError = (canvas, message) => {
        if (!canvas) return;

        const parent = canvas.parentElement;

        if (parent) {
            parent.innerHTML = `
                <div class="d-flex align-items-center justify-content-center
                            text-muted text-center h-100 p-4">
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

        if (!incomeExpenseCanvas && !categoryCanvas) {
            return;
        }

        if (typeof Chart === "undefined") {
            showChartError(
                incomeExpenseCanvas,
                "Chart library could not load. Please refresh the page."
            );

            showChartError(
                categoryCanvas,
                "Chart library could not load. Please refresh the page."
            );

            return;
        }

        try {
            const response = await fetch("/api/chart-data", {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            });

            if (!response.ok) {
                throw new Error(
                    `Chart API failed with status ${response.status}`
                );
            }

            const data = await response.json();

            // Income vs Expenses chart
            if (incomeExpenseCanvas) {
                const monthly = data.monthly || {};

                const labels = Array.isArray(monthly.labels)
                    ? monthly.labels
                    : [];

                const income = Array.isArray(monthly.income)
                    ? monthly.income
                    : [];

                const expenses = Array.isArray(monthly.expense)
                    ? monthly.expense
                    : [];

                new Chart(incomeExpenseCanvas, {
                    type: "bar",

                    data: {
                        labels: labels,

                        datasets: [
                            {
                                label: "Income",
                                data: income,
                                backgroundColor: "#16a34a",
                                borderColor: "#15803d",
                                borderWidth: 1,
                                borderRadius: 6
                            },
                            {
                                label: "Expenses",
                                data: expenses,
                                backgroundColor: "#ef4444",
                                borderColor: "#dc2626",
                                borderWidth: 1,
                                borderRadius: 6
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
                                position: "bottom",

                                labels: {
                                    usePointStyle: true,
                                    boxWidth: 8,
                                    padding: 16
                                }
                            },

                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        return `${context.dataset.label}: ${money(context.parsed.y)}`;
                                    }
                                }
                            }
                        },

                        scales: {
                            y: {
                                beginAtZero: true,

                                ticks: {
                                    callback: (value) => money(value)
                                },

                                grid: {
                                    color: "rgba(148, 163, 184, 0.18)"
                                }
                            },

                            x: {
                                grid: {
                                    display: false
                                }
                            }
                        }
                    }
                });
            }

            // Expense Categories chart
            if (categoryCanvas) {
                const categories = data.categories || {};

                const categoryLabels = Array.isArray(categories.labels)
                    ? categories.labels
                    : [];

                const categoryValues = Array.isArray(categories.data)
                    ? categories.data
                    : [];

                if (
                    categoryLabels.length === 0 ||
                    categoryValues.length === 0
                ) {
                    showChartError(
                        categoryCanvas,
                        "Add some expenses to see your category breakdown."
                    );
                } else {
                    new Chart(categoryCanvas, {
                        type: "doughnut",

                        data: {
                            labels: categoryLabels,

                            datasets: [
                                {
                                    label: "Expenses",

                                    data: categoryValues,

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

                                    borderColor: "#ffffff",
                                    borderWidth: 3,
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
                                    position: "bottom",

                                    labels: {
                                        usePointStyle: true,
                                        boxWidth: 8,
                                        padding: 16
                                    }
                                },

                                tooltip: {
                                    callbacks: {
                                        label: (context) => {
                                            return `${context.label}: ${money(context.parsed)}`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            }
        } catch (error) {
            console.error("Dashboard chart error:", error);

            showChartError(
                incomeExpenseCanvas,
                "Unable to load chart data. Please refresh the page."
            );

            showChartError(
                categoryCanvas,
                "Unable to load chart data. Please refresh the page."
            );
        }
    });
})();
