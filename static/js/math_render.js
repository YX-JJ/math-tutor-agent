function renderMathInElement(element) {
    if (!element) return;
    try {
        if (typeof katex !== 'undefined') {
            renderMathDelimiters(element);
        }
    } catch (e) {
        console.warn('KaTeX render failed:', e);
    }
}

function renderMathDelimiters(element) {
    var html = element.innerHTML;
    // $$...$$ display math
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, function(match, formula) {
        try {
            return katex.renderToString(formula.trim(), { displayMode: true, throwOnError: false });
        } catch (e) { return match; }
    });
    // $...$ inline math
    html = html.replace(/\$(.+?)\$/g, function(match, formula) {
        try {
            return katex.renderToString(formula.trim(), { displayMode: false, throwOnError: false });
        } catch (e) { return match; }
    });
    element.innerHTML = html;
}

// Math rendering is done per-element by page scripts (e.g., renderMathInElement on new messages).
// Do NOT call renderMathDelimiters(document.body) — it replaces innerHTML and destroys event handlers.
