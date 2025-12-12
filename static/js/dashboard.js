// Dashboard JavaScript

// API base URL
const API_BASE = '/api';

// Load buy recommendations
async function loadBuyRecommendations() {
    const contentDiv = document.getElementById('buy-recommendations-content');
    if (!contentDiv) {
        console.error('Buy recommendations content div not found');
        return;
    }
    
    try {
        contentDiv.innerHTML = '<p class="loading">Loading buy recommendations...</p>';
        // Add cache-busting parameter to force fresh data
        const response = await fetch(`${API_BASE}/buy-recommendations?_t=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.error) {
            contentDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            return;
        }
        
        const buyRecs = data.buy_recommendations || [];
        const sellRecs = data.sell_recommendations || [];
        const availableFunds = data.available_funds || 0;
        
        let html = '';
        
        if (sellRecs.length > 0) {
            html += '<div class="sell-summary">';
            html += `<h3>Sell Recommendations (Available Funds: £${availableFunds.toFixed(2)})</h3>`;
            html += '<ul>';
            sellRecs.forEach(rec => {
                html += `<li>${rec.ticker}: ${rec.action} - ${rec.action_reason}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (buyRecs.length > 0) {
            html += '<div class="buy-list">';
            html += '<h3>Buy Opportunities (Multi-Factor Analysis)</h3>';
            
            // Check if using v2 format (has score_breakdown)
            const isV2Format = buyRecs[0].score_breakdown !== undefined;
            
            if (isV2Format) {
                // Multi-factor table format
                html += '<table class="buy-table"><thead><tr>';
                html += '<th>Symbol</th><th>Rec</th><th>Total Score</th>';
                html += '<th>Early Signals</th><th>Technical</th><th>Risk/Reward</th><th>Market</th>';
                html += '<th>Risk</th><th>Reward</th><th>Price</th><th>Insider Value</th><th>Allocation</th>';
                html += '</tr></thead><tbody>';
                
                buyRecs.slice(0, 15).forEach(rec => {
                    const price = rec.current_price_gbp ? `£${rec.current_price_gbp.toFixed(2)}` : 'N/A';
                    const insiderValue = rec.insider_buying_value_gbp && rec.insider_buying_value_gbp > 0 
                        ? `£${rec.insider_buying_value_gbp.toLocaleString('en-GB', {minimumFractionDigits: 0, maximumFractionDigits: 0})}` 
                        : 'N/A';
                    const allocation = rec.suggested_allocation_gbp ? `£${rec.suggested_allocation_gbp.toFixed(2)}` : 'N/A';
                    
                    const scoreBreakdown = rec.score_breakdown || {};
                    const earlyScore = scoreBreakdown.early_signals || 0;
                    const techScore = scoreBreakdown.technical || 0;
                    const riskRewardScore = scoreBreakdown.risk_reward || 0;
                    const marketScore = scoreBreakdown.market_conditions || 0;
                    const totalScore = rec.total_score || rec.confidence_score || 0;
                    
                    html += '<tr>';
                    html += `<td><strong>${rec.symbol}</strong></td>`;
                    html += `<td><span class="rec-badge rec-${rec.recommendation.toLowerCase().replace(' ', '-')}">${rec.recommendation}</span></td>`;
                    html += `<td><strong>${totalScore}/100</strong></td>`;
                    html += `<td>${earlyScore}/30</td>`;
                    html += `<td>${techScore}/30</td>`;
                    html += `<td>${riskRewardScore}/25</td>`;
                    html += `<td>${marketScore}/15</td>`;
                    html += `<td><span class="risk-badge risk-${(rec.risk_level || 'UNKNOWN').toLowerCase().replace('-', '')}">${rec.risk_level || 'N/A'}</span></td>`;
                    html += `<td><span class="reward-badge reward-${(rec.reward_potential || 'UNKNOWN').toLowerCase().replace(' ', '-')}">${rec.reward_potential || 'N/A'}</span></td>`;
                    html += `<td>${price}</td>`;
                    html += `<td>${insiderValue}</td>`;
                    html += `<td>${allocation}</td>`;
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                
                // Add expandable details section
                html += '<div class="buy-details-section">';
                html += '<h4>Detailed Signal Breakdown</h4>';
                buyRecs.slice(0, 10).forEach(rec => {
                    const reasons = rec.reasons || [];
                    const factors = rec.factors || {};
                    html += `<div class="buy-detail-item">`;
                    html += `<strong>${rec.symbol}</strong> - ${rec.recommendation} (${rec.total_score || rec.confidence_score}/100)`;
                    html += `<ul>`;
                    reasons.forEach(reason => {
                        html += `<li>${reason}</li>`;
                    });
                    if (factors.early_signals && factors.early_signals.recent_insider_buying) {
                        const details = factors.early_signals.insider_details || {};
                        html += `<li>Insider: ${details.count || 0} transaction(s), ${details.most_recent_days_ago || 'N/A'} days ago</li>`;
                    }
                    if (factors.technical) {
                        const tech = factors.technical;
                        if (tech.momentum) {
                            html += `<li>Momentum: 5d=${tech.momentum['5d']?.toFixed(1) || 'N/A'}%, 20d=${tech.momentum['20d']?.toFixed(1) || 'N/A'}%</li>`;
                        }
                        if (rec.rsi) {
                            html += `<li>RSI: ${rec.rsi.toFixed(1)}</li>`;
                        }
                    }
                    if (rec.upside_potential_pct) {
                        html += `<li>Upside Potential: ${rec.upside_potential_pct.toFixed(1)}%</li>`;
                    }
                    html += `</ul>`;
                    html += `</div>`;
                });
                html += '</div>';
            } else {
                // Legacy v1 format
                html += '<table class="buy-table"><thead><tr>';
                html += '<th>Symbol</th><th>Recommendation</th><th>Confidence</th>';
                html += '<th>Price</th><th>Insider Buying Value</th><th>Suggested Allocation</th><th>Signals</th>';
                html += '</tr></thead><tbody>';
                
                buyRecs.slice(0, 10).forEach(rec => {
                    const price = rec.current_price_gbp ? `£${rec.current_price_gbp.toFixed(2)}` : 'N/A';
                    const insiderValue = rec.insider_buying_value_gbp && rec.insider_buying_value_gbp > 0 
                        ? `£${rec.insider_buying_value_gbp.toLocaleString('en-GB', {minimumFractionDigits: 0, maximumFractionDigits: 0})}` 
                        : 'N/A';
                    const allocation = rec.suggested_allocation_gbp ? `£${rec.suggested_allocation_gbp.toFixed(2)}` : 'N/A';
                    const signals = rec.reasons ? rec.reasons.slice(0, 2).join('; ') : '';
                    const score = rec.total_score || rec.confidence_score || 0;
                    
                    html += '<tr>';
                    html += `<td><strong>${rec.symbol}</strong></td>`;
                    html += `<td><span class="rec-badge rec-${rec.recommendation.toLowerCase().replace(' ', '-')}">${rec.recommendation}</span></td>`;
                    html += `<td>${score}/100</td>`;
                    html += `<td>${price}</td>`;
                    html += `<td>${insiderValue}</td>`;
                    html += `<td>${allocation}</td>`;
                    html += `<td class="signals">${signals}</td>`;
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
            }
            
            html += '</div>';
            
            // Add discussion format text
            if (data.recommendations_text) {
                html += '<div class="recommendations-text">';
                html += '<h3>Discussion Format</h3>';
                html += '<pre>' + data.recommendations_text + '</pre>';
                html += '</div>';
            }
        } else {
            html = '<p>No buy recommendations at this time. ';
            if (availableFunds > 0) {
                html += `You have £${availableFunds.toFixed(2)} available from sell recommendations.</p>`;
            } else {
                html += 'Run an evaluation to see recommendations.</p>';
            }
        }
        
        contentDiv.innerHTML = html;
    } catch (error) {
        console.error('Error loading buy recommendations:', error);
        contentDiv.innerHTML = '<p class="error">Error loading buy recommendations. Check console for details.</p>';
    }
}

// Status bar functions
function showStatus(message, isLoading = false) {
    const statusBar = document.getElementById('status-bar');
    const statusText = document.getElementById('status-text');
    const statusSpinner = document.getElementById('status-spinner');
    
    statusText.textContent = message;
    statusBar.style.display = 'block';
    
    if (isLoading) {
        statusSpinner.style.display = 'inline-block';
        statusBar.className = 'status-bar status-loading';
    } else {
        statusSpinner.style.display = 'none';
        statusBar.className = 'status-bar status-success';
    }
}

function hideStatus() {
    const statusBar = document.getElementById('status-bar');
    statusBar.style.display = 'none';
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Load portfolio data
async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/portfolio`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading portfolio:', error);
        showToast('Error loading portfolio', 'error');
        return null;
    }
}

// Update holding
async function updateHolding(ticker, data) {
    try {
        const response = await fetch(`${API_BASE}/holding/${ticker}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast(result.message || 'Holding updated successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Error updating holding', 'error');
        }
    } catch (error) {
        console.error('Error updating holding:', error);
        showToast('Error updating holding', 'error');
    }
}

// Add holding
async function addHolding(data) {
    try {
        const response = await fetch(`${API_BASE}/holding`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast(result.message || 'Holding added successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Error adding holding', 'error');
        }
    } catch (error) {
        console.error('Error adding holding:', error);
        showToast('Error adding holding', 'error');
    }
}

// Delete holding
async function deleteHolding(ticker) {
    if (!confirm(`Are you sure you want to delete holding ${ticker}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/holding/${ticker}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast(result.message || 'Holding deleted successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Error deleting holding', 'error');
        }
    } catch (error) {
        console.error('Error deleting holding:', error);
        showToast('Error deleting holding', 'error');
    }
}

// Trigger evaluation
async function triggerEvaluation() {
    const btn = document.getElementById('btn-evaluate');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    showStatus('Running risk evaluation... This may take 1-2 minutes.', true);
    
    try {
        const response = await fetch(`${API_BASE}/evaluate?_t=${Date.now()}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus('✅ Evaluation completed successfully! Refreshing page...', false);
            setTimeout(() => {
                // Force COMPLETE hard reload - clear all caches
                // Use location.replace to prevent back button issues
                const url = new URL(window.location);
                url.searchParams.set('_t', Date.now());
                url.searchParams.set('_nocache', Date.now());
                // Force reload from server, bypassing all caches
                window.location.replace(url.toString() + '&_reload=' + Date.now());
            }, 2000);
        } else {
            showStatus('❌ Evaluation failed: ' + (result.error || 'Unknown error'), false);
            btn.disabled = false;
            btn.textContent = originalText;
            setTimeout(() => hideStatus(), 5000);
        }
    } catch (error) {
        console.error('Error running evaluation:', error);
        showStatus('❌ Error running evaluation: ' + error.message, false);
        btn.disabled = false;
        btn.textContent = originalText;
        setTimeout(() => hideStatus(), 5000);
    }
}

// Refresh page
function refreshPage() {
    const btn = document.getElementById('btn-refresh');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Refreshing...';
    
    showStatus('Refreshing portfolio data...', true);
    
    // Reload the page with cache-busting parameter
    setTimeout(() => {
        // Add timestamp to force fresh data
        const url = new URL(window.location);
        url.searchParams.set('_t', Date.now());
        window.location.href = url.toString();
    }, 500);
}

// Modal handling
const editModal = document.getElementById('edit-modal');
const addModal = document.getElementById('add-modal');
const editForm = document.getElementById('edit-form');
const addForm = document.getElementById('add-form');

// Close modals
document.querySelectorAll('.close').forEach(closeBtn => {
    closeBtn.addEventListener('click', () => {
        editModal.style.display = 'none';
        addModal.style.display = 'none';
    });
});

document.getElementById('btn-cancel').addEventListener('click', () => {
    editModal.style.display = 'none';
});

document.getElementById('btn-cancel-add').addEventListener('click', () => {
    addModal.style.display = 'none';
});

// Close on outside click
window.addEventListener('click', (e) => {
    if (e.target === editModal) {
        editModal.style.display = 'none';
    }
    if (e.target === addModal) {
        addModal.style.display = 'none';
    }
});

// Edit holding button
document.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', async () => {
        const ticker = btn.dataset.ticker;
        const portfolio = await loadPortfolio();
        
        if (portfolio && portfolio.holdings[ticker]) {
            const holding = portfolio.holdings[ticker];
            
            document.getElementById('edit-ticker').value = ticker;
            document.getElementById('edit-symbol').value = holding.symbol;
            document.getElementById('edit-shares').value = holding.shares;
            document.getElementById('edit-baseline').value = holding.baseline_value_gbp;
            document.getElementById('edit-type').value = holding.type || 'equity';
            document.getElementById('edit-risk-bucket').value = holding.risk_bucket || 'unknown';
            
            editModal.style.display = 'block';
        }
    });
});

// Delete holding button
document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () => {
        const ticker = btn.dataset.ticker;
        deleteHolding(ticker);
    });
});

// Edit form submit
editForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const ticker = document.getElementById('edit-ticker').value;
    const data = {
        symbol: document.getElementById('edit-symbol').value,
        shares: parseFloat(document.getElementById('edit-shares').value),
        baseline_value_gbp: parseFloat(document.getElementById('edit-baseline').value),
        type: document.getElementById('edit-type').value,
        risk_bucket: document.getElementById('edit-risk-bucket').value
    };
    
    updateHolding(ticker, data);
    editModal.style.display = 'none';
});

// Add form submit
addForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const data = {
        ticker: document.getElementById('add-ticker').value,
        symbol: document.getElementById('add-symbol').value,
        shares: parseFloat(document.getElementById('add-shares').value),
        baseline_value_gbp: parseFloat(document.getElementById('add-baseline').value),
        type: document.getElementById('add-type').value,
        risk_bucket: document.getElementById('add-risk-bucket').value
    };
    
    addHolding(data);
    addModal.style.display = 'none';
});

// Add holding button
document.getElementById('btn-add-holding').addEventListener('click', () => {
    addForm.reset();
    addModal.style.display = 'block';
});

// Evaluate button
document.getElementById('btn-evaluate').addEventListener('click', () => {
    // Non-blocking: avoid confirm() modal which blocks the UI.
    // If users click by accident, they can just ignore the status bar while it runs.
    triggerEvaluation();
});

// Refresh button
document.getElementById('btn-refresh').addEventListener('click', () => {
    refreshPage();
});

// Refresh buy recommendations button
const btnRefreshBuys = document.getElementById('btn-refresh-buys');
if (btnRefreshBuys) {
    btnRefreshBuys.addEventListener('click', () => {
        showStatus('Refreshing buy recommendations...', true);
        loadBuyRecommendations().then(() => {
            showStatus('Buy recommendations refreshed', false);
            setTimeout(() => hideStatus(), 2000);
        }).catch(() => {
            showStatus('Error refreshing buy recommendations', false);
            setTimeout(() => hideStatus(), 3000);
        });
    });
}

// Load buy recommendations on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadBuyRecommendations);
} else {
    loadBuyRecommendations();
}

// Make table cells editable on double-click
document.querySelectorAll('.editable').forEach(cell => {
    cell.addEventListener('dblclick', async () => {
        const row = cell.closest('tr');
        const ticker = row.dataset.ticker;
        const field = cell.dataset.field;
        const currentValue = cell.textContent.replace('£', '').trim();
        
        const newValue = prompt(`Enter new value for ${field}:`, currentValue);
        
        if (newValue !== null && newValue !== currentValue) {
            const data = {};
            if (field === 'shares') {
                data[field] = parseFloat(newValue);
            } else if (field === 'baseline_value_gbp') {
                data[field] = parseFloat(newValue);
            }
            
            await updateHolding(ticker, data);
        }
    });
});

// ==========================
// Holding analysis tooltips
// ==========================

(function setupHoldingTooltips() {
    const rows = document.querySelectorAll('#holdings-tbody tr[data-ticker]');
    if (!rows.length) {
        console.debug('Holding tooltips: no rows with data-ticker found');
        return;
    }

    // Create a single tooltip element we reuse for all rows
    let tooltip = document.getElementById('holding-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'holding-tooltip';
        tooltip.className = 'holding-tooltip';
        tooltip.style.position = 'fixed';
        tooltip.style.maxWidth = '420px';
        tooltip.style.padding = '8px 10px';
        tooltip.style.borderRadius = '6px';
        tooltip.style.background = 'rgba(15, 23, 42, 0.96)'; // dark slate
        tooltip.style.color = '#f9fafb';
        tooltip.style.fontSize = '12px';
        tooltip.style.lineHeight = '1.4';
        tooltip.style.boxShadow = '0 6px 18px rgba(15, 23, 42, 0.45)';
        tooltip.style.zIndex = '9999';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.display = 'none';
        document.body.appendChild(tooltip);
    }

    function showTooltip(text, x, y) {
        if (!text) return;
        tooltip.textContent = text;
        tooltip.style.display = 'block';

        // Basic positioning with viewport bounds check
        const padding = 12;
        const rect = tooltip.getBoundingClientRect();
        let left = x + 16;
        let top = y + 16;

        if (left + rect.width + padding > window.innerWidth) {
            left = x - rect.width - 16;
        }
        if (top + rect.height + padding > window.innerHeight) {
            top = y - rect.height - 16;
        }

        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    }

    function hideTooltip() {
        tooltip.style.display = 'none';
    }

    console.debug(`Holding tooltips: found ${rows.length} rows`);

    rows.forEach(row => {
        const summary = row.dataset.analysisSummary;
        if (!summary) {
            console.debug('Holding tooltips: missing analysisSummary for row', row.dataset.ticker);
            return;
        }

        console.debug('Holding tooltips: attaching tooltip for', row.dataset.ticker);

        row.addEventListener('mouseenter', (e) => {
            showTooltip(summary, e.clientX, e.clientY);
        });

        row.addEventListener('mousemove', (e) => {
            if (tooltip.style.display === 'block') {
                showTooltip(summary, e.clientX, e.clientY);
            }
        });

        row.addEventListener('mouseleave', () => {
            hideTooltip();
        });
    });
})();

