<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LexSarthi – AI-Native Law Firm OS</title>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        /* ... (same styles as before) ... */
        /* I'll keep the same CSS; for brevity, assume it's unchanged */
    </style>
</head>
<body>
<!-- ... (same HTML structure) ... -->

<!-- Add navigation links to test page and court comments -->
<div style="margin: 10px 0; text-align: center; gap: 20px;">
    <a href="/test-agents.html" style="color:#1a4a6e; text-decoration:underline;">🧪 Test Agents (Development)</a>
    <a href="/ai-court-comments.html" style="color:#1a4a6e; text-decoration:underline;">⚖️ AI Court Comments</a>
</div>

<!-- Rest of the page ... -->

<script>
    // ========== CONFIGURATION ==========
    const API_BASE = "https://upamnyu12-LEX.hf.space";
    const RAZORPAY_KEY = "rzp_live_T1H8xhuwL0oHhD";  // ✅ YOUR LIVE KEY

    // ========== FIXED escapeHtml ==========
    function escapeHtml(str) {
        if (str === null || str === undefined) return "";
        return String(str).replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
    }

    // ========== FIXED Oral Arguments Display ==========
    // In the handler for oralBtn, replace the display logic with this corrected version:

    // (Inside the oralBtn click handler, after getting data)
    let html = `<div class="summary"><strong>Case Summary:</strong><br>${escapeHtml(data.case_summary)}</div>`;
    if (data.issues && data.issues.length) {
        html += "<h4>📌 Legal Issues & Arguments</h4>";
        data.issues.forEach((issue, i) => {
            html += `<div class="clause-card">
                        <strong>Issue ${i+1}:</strong> ${escapeHtml(issue.issue)}<br>
                        <em>Argument:</em> ${escapeHtml(issue.argument)}<br>
                        <em>Supporting Laws:</em> ${(issue.supporting_laws || []).map(l => escapeHtml(l)).join(", ")}<br>
                        <em>Counterarguments:</em> ${(issue.counterarguments || []).map(c => escapeHtml(c)).join("; ")}<br>
                        <em>Responses:</em> ${(issue.responses || []).map(r => escapeHtml(r)).join("; ")}<br>
                        <em>Key Precedents:</em> ${(issue.key_precedents || []).map(p => escapeHtml(p)).join("; ")}
                     </div>`;
        });
    }
    if (data.likely_questions && data.likely_questions.length) {
        html += "<h4>❓ Likely Questions from the Bench</h4>";
        data.likely_questions.forEach(q => {
            html += `<div class="clause-card"><strong>Q:</strong> ${escapeHtml(q.question)}<br><strong>A:</strong> ${escapeHtml(q.suggested_answer)}</div>`;
        });
    }
    html += `<div class="summary"><strong>🎯 Opening Statement:</strong> ${escapeHtml(data.opening_statement)}</div>`;
    html += `<div class="summary"><strong>📌 Closing Statement:</strong> ${escapeHtml(data.closing_statement)}</div>`;
    if (data.red_flags && data.red_flags.length) {
        html += "<h4>⚠️ Red Flags</h4><ul>" + data.red_flags.map(f => `<li>${escapeHtml(f)}</li>`).join("") + "</ul>";
    }
    if (data.must_cite && data.must_cite.length) {
        html += "<h4>📖 Must-Cite Precedents</h4><ul>" + data.must_cite.map(c => `<li>${escapeHtml(c)}</li>`).join("") + "</ul>";
    }
    html += displayLawyerReview(data);
    // Then set resultDiv.innerHTML = html;

    // ... (rest of the script unchanged)
</script>
</body>
</html>