/**
 * SpendWise Student - Chart.js Visualizations
 * Renders:
 * 1. Expense Breakdown Doughnut Chart
 * 2. Income vs Expenses 6-Month Bar Chart
 */

document.addEventListener('DOMContentLoaded', () => {
    initDashboardCharts();
});

async function initDashboardCharts() {
    const categoryCanvas = document.getElementById('categoryChart');
    const monthlyCanvas = document.getElementById('monthlyChart');

    if (!categoryCanvas || !monthlyCanvas) return;

    try {
        const response = await fetch('/api/chart-data');
        if (!response.ok) {
            console.error('Failed to load chart data');
            return;
        }

        const data = await response.json();

        // 1. Render Category Doughnut Chart
        renderCategoryDoughnut(categoryCanvas, data.categories);

        // 2. Render Monthly Comparison Bar Chart
        renderMonthlyBarChart(monthlyCanvas, data.monthly);

    } catch (err) {
        console.error('Error fetching or initializing charts:', err);
    }
}

/**
 * Renders Doughnut chart of expenses by category
 */
function renderCategoryDoughnut(canvas, categoryData) {
    const emptyMsg = document.getElementById('noExpenseChartData');
    
    if (!categoryData || !categoryData.labels || categoryData.labels.length === 0) {
        canvas.style.display = 'none';
        if (emptyMsg) emptyMsg.classList.remove('d-none');
        return;
    }

    if (emptyMsg) emptyMsg.classList.add('d-none');
    canvas.style.display = 'block';

    const colorPalette = [
        '#4f46e5', '#06b6d4', '#10b981', '#f59e0b', 
        '#ef4444', '#8b5cf6', '#ec4899', '#64748b'
    ];

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: categoryData.labels,
            datasets: [{
                data: categoryData.data,
                backgroundColor: colorPalette.slice(0, categoryData.labels.length),
                hoverOffset: 6,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const formatted = typeof formatINR === 'function' ? formatINR(value) : `₹${value.toFixed(2)}`;
                            return ` ${label}: ${formatted}`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

/**
 * Renders Bar Chart of Income vs Expenses for the last 6 months
 */
function renderMonthlyBarChart(canvas, monthlyData) {
    const emptyMsg = document.getElementById('noMonthlyChartData');

    const hasData = monthlyData && monthlyData.labels && monthlyData.labels.length > 0 &&
        (monthlyData.income.some(v => v > 0) || monthlyData.expense.some(v => v > 0));

    if (!hasData) {
        canvas.style.display = 'none';
        if (emptyMsg) emptyMsg.classList.remove('d-none');
        return;
    }

    if (emptyMsg) emptyMsg.classList.add('d-none');
    canvas.style.display = 'block';

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: monthlyData.labels,
            datasets: [
                {
                    label: 'Income',
                    data: monthlyData.income,
                    backgroundColor: '#10b981',
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.7
                },
                {
                    label: 'Expense',
                    data: monthlyData.expense,
                    backgroundColor: '#ef4444',
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.7
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return '₹' + (value >= 1000 ? (value / 1000) + 'k' : value);
                        },
                        font: { size: 11 }
                    },
                    grid: {
                        color: '#f1f5f9'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: { size: 11 }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 12,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const datasetLabel = context.dataset.label || '';
                            const value = context.parsed.y;
                            const formatted = typeof formatINR === 'function' ? formatINR(value) : `₹${value.toFixed(2)}`;
                            return ` ${datasetLabel}: ${formatted}`;
                        }
                    }
                }
            }
        }
    });
}
