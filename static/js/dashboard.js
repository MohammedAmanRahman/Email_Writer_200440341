/* ============================================================
   Consumer Complaint Assistant - Dashboard JavaScript
   ============================================================ */

(function () {
    'use strict';

    /* ---------- Colour Palettes ---------- */
    const PALETTE = [
        '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
        '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0',
        '#0a58ca', '#8540f5', '#e685b5', '#b02a37', '#cc9a06',
        '#146c43', '#3dd5f3', '#adb5bd'
    ];

    const SENTIMENT_COLOURS = {
        positive: '#198754',
        neutral:  '#6c757d',
        negative: '#dc3545'
    };

    const URGENCY_COLOURS = {
        critical: '#dc3545',
        high:     '#fd7e14',
        medium:   '#ffc107',
        low:      '#198754'
    };

    /* ---------- Chart.js Global Defaults ---------- */
    Chart.defaults.font.family = "'Segoe UI', system-ui, -apple-system, sans-serif";
    Chart.defaults.responsive = true;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.padding = 16;

    /* ---------- State ---------- */
    let charts = {};

    /* ---------- Utilities ---------- */

    function showElement(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = '';
    }

    function hideElement(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    }

    function hasData(arr) {
        return Array.isArray(arr) && arr.length > 0;
    }

    function destroyChart(name) {
        if (charts[name]) {
            charts[name].destroy();
            charts[name] = null;
        }
    }

    /* ---------- Stat Cards ---------- */

    function updateStatCards(data) {
        const totalEl = document.getElementById('statTotalComplaints');
        const sentEl  = document.getElementById('statAvgSentiment');
        const catEl   = document.getElementById('statTopCategory');
        const resEl   = document.getElementById('statResolutionRate');

        if (totalEl) {
            totalEl.textContent = (data.total_complaints != null)
                ? Number(data.total_complaints).toLocaleString()
                : '0';
        }

        if (sentEl) {
            if (data.average_sentiment != null) {
                const val = parseFloat(data.average_sentiment);
                sentEl.textContent = val.toFixed(2);
                // Update icon based on sentiment
                const iconEl = sentEl.closest('.stat-card').querySelector('.bi');
                if (iconEl) {
                    iconEl.className = iconEl.className.replace(/bi-emoji-\S+/, '');
                    if (val > 0.2) iconEl.classList.add('bi-emoji-smile');
                    else if (val < -0.2) iconEl.classList.add('bi-emoji-frown');
                    else iconEl.classList.add('bi-emoji-neutral');
                }
            } else {
                sentEl.innerHTML = '&mdash;';
            }
        }

        if (catEl) {
            catEl.textContent = data.most_common_category || '\u2014';
        }

        if (resEl) {
            if (data.resolution_rate != null) {
                resEl.textContent = parseFloat(data.resolution_rate).toFixed(1) + '%';
            } else {
                resEl.innerHTML = '&mdash;';
            }
        }
    }

    /* ---------- Category Chart (Doughnut) ---------- */

    function buildCategoryChart(categories) {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) return;

        destroyChart('category');

        if (!hasData(categories)) {
            ctx.style.display = 'none';
            showElement('categoryEmpty');
            return;
        }

        hideElement('categoryEmpty');
        ctx.style.display = '';

        const labels = categories.map(c => c.name || c.category);
        const values = categories.map(c => c.count);

        charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: PALETTE.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverOffset: 8
                }]
            },
            options: {
                cutout: '55%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((ctx.parsed / total) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /* ---------- Sentiment Chart (Pie) ---------- */

    function buildSentimentChart(sentiment) {
        const ctx = document.getElementById('sentimentChart');
        if (!ctx) return;

        destroyChart('sentiment');

        if (!sentiment || Object.keys(sentiment).length === 0) {
            ctx.style.display = 'none';
            showElement('sentimentEmpty');
            return;
        }

        hideElement('sentimentEmpty');
        ctx.style.display = '';

        // Normalise: accept object {positive: N, neutral: N, negative: N} or array
        let labels, values, colours;
        if (Array.isArray(sentiment)) {
            labels  = sentiment.map(s => s.name || s.sentiment);
            values  = sentiment.map(s => s.count);
            colours = labels.map(l => SENTIMENT_COLOURS[l.toLowerCase()] || '#adb5bd');
        } else {
            labels  = Object.keys(sentiment);
            values  = Object.values(sentiment);
            colours = labels.map(l => SENTIMENT_COLOURS[l.toLowerCase()] || '#adb5bd');
        }

        charts.sentiment = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
                datasets: [{
                    data: values,
                    backgroundColor: colours,
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverOffset: 8
                }]
            },
            options: {
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((ctx.parsed / total) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /* ---------- Monthly Trends Chart (Line) ---------- */

    function buildTrendsChart(trends) {
        const ctx = document.getElementById('trendsChart');
        if (!ctx) return;

        destroyChart('trends');

        if (!hasData(trends)) {
            ctx.style.display = 'none';
            showElement('trendsEmpty');
            return;
        }

        hideElement('trendsEmpty');
        ctx.style.display = '';

        const labels = trends.map(t => t.month || t.label || t.date);
        const values = trends.map(t => t.count);

        charts.trends = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Complaints',
                    data: values,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#0d6efd',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    borderWidth: 2.5
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    /* ---------- Urgency Chart (Bar) ---------- */

    function buildUrgencyChart(urgency) {
        const ctx = document.getElementById('urgencyChart');
        if (!ctx) return;

        destroyChart('urgency');

        if (!urgency || Object.keys(urgency).length === 0) {
            ctx.style.display = 'none';
            showElement('urgencyEmpty');
            return;
        }

        hideElement('urgencyEmpty');
        ctx.style.display = '';

        let labels, values, colours;
        if (Array.isArray(urgency)) {
            labels  = urgency.map(u => u.name || u.level);
            values  = urgency.map(u => u.count);
            colours = labels.map(l => URGENCY_COLOURS[l.toLowerCase()] || '#adb5bd');
        } else {
            labels  = Object.keys(urgency);
            values  = Object.values(urgency);
            colours = labels.map(l => URGENCY_COLOURS[l.toLowerCase()] || '#adb5bd');
        }

        charts.urgency = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
                datasets: [{
                    label: 'Complaints',
                    data: values,
                    backgroundColor: colours,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 60
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    /* ---------- Company Chart (Horizontal Bar) ---------- */

    function buildCompanyChart(companies) {
        const ctx = document.getElementById('companyChart');
        if (!ctx) return;

        destroyChart('company');

        if (!hasData(companies)) {
            ctx.style.display = 'none';
            showElement('companyEmpty');
            return;
        }

        hideElement('companyEmpty');
        ctx.style.display = '';

        // Take top 10
        const top = companies.slice(0, 10);
        const labels = top.map(c => c.name || c.company);
        const values = top.map(c => c.count);

        charts.company = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Complaints',
                    data: values,
                    backgroundColor: PALETTE.slice(0, labels.length),
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 36
                }]
            },
            options: {
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 12 },
                            autoSkip: false
                        }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    /* ---------- Keyword Cloud ---------- */

    function buildKeywordCloud(keywords) {
        const container = document.getElementById('keywordCloud');
        const emptyEl   = document.getElementById('keywordEmpty');
        if (!container) return;

        // Clear existing
        container.innerHTML = '';

        if (!hasData(keywords)) {
            container.innerHTML = '<p class="text-muted">No keywords available</p>';
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        // Determine min/max frequency for scaling
        const freqs = keywords.map(k => k.count || k.frequency || 1);
        const minFreq = Math.min(...freqs);
        const maxFreq = Math.max(...freqs);
        const range = maxFreq - minFreq || 1;

        keywords.forEach(function (kw) {
            const word = kw.word || kw.keyword || kw.name;
            const freq = kw.count || kw.frequency || 1;

            const span = document.createElement('span');
            span.classList.add('keyword');
            span.textContent = word;

            // Scale font size between 0.75rem and 2rem
            const normalized = (freq - minFreq) / range;   // 0..1
            const fontSize = 0.75 + normalized * 1.25;     // 0.75..2.0
            span.style.fontSize = fontSize.toFixed(2) + 'rem';

            // Add size class for additional styling
            if (normalized > 0.75) span.classList.add('keyword-xl');
            else if (normalized > 0.5) span.classList.add('keyword-lg');
            else if (normalized > 0.25) span.classList.add('keyword-md');
            else span.classList.add('keyword-sm');

            span.title = word + ': ' + freq;
            container.appendChild(span);
        });
    }

    /* ---------- Fetch & Render ---------- */

    function loadDashboard() {
        hideElement('dashboardContent');
        showElement('loadingSpinner');

        fetch(DASHBOARD_API_URL, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
        .then(function (response) {
            if (!response.ok) throw new Error('Network response ' + response.status);
            return response.json();
        })
        .then(function (data) {
            hideElement('loadingSpinner');
            showElement('dashboardContent');

            updateStatCards(data);
            buildCategoryChart(data.categories || data.category_distribution || []);
            buildSentimentChart(data.sentiment || data.sentiment_distribution || {});
            buildTrendsChart(data.trends || data.monthly_trends || []);
            buildUrgencyChart(data.urgency || data.urgency_levels || {});
            buildCompanyChart(data.companies || data.top_companies || []);
            buildKeywordCloud(data.keywords || data.top_keywords || []);
        })
        .catch(function (err) {
            hideElement('loadingSpinner');
            showElement('dashboardContent');

            console.error('Dashboard fetch error:', err);

            // Show empty states for every section
            updateStatCards({});
            buildCategoryChart([]);
            buildSentimentChart({});
            buildTrendsChart([]);
            buildUrgencyChart({});
            buildCompanyChart([]);
            buildKeywordCloud([]);
        });
    }

    /* ---------- Init ---------- */

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof DASHBOARD_API_URL !== 'undefined') {
            loadDashboard();

            // Refresh button
            const refreshBtn = document.getElementById('refreshBtn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function () {
                    loadDashboard();
                });
            }
        }
    });

})();
