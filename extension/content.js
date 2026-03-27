/**
 * Sentinel Shield — Chrome Interceptor (Content Script)
 * Intercepts user prompts from ChatGPT/Claude and redacts via Sentinel API.
 */

console.log("🛡️ Sentinel Shield: Active and Protecting your Data on this page.");

// Configuration for common AI search bars (CSS selectors)
const SEARCH_BARS = [
    '#prompt-textarea',           // ChatGPT
    '[contenteditable="true"]',    // Claude / Generic
    'textarea[name="q"]'          // Gemini
];

/**
 * Intercepts the submit event (Enter or click)
 */
document.addEventListener('keydown', async (e) => {
    // Only intercept if Enter is pressed without Shift
    if (e.key === 'Enter' && !e.shiftKey) {
        const target = e.target;
        
        // Is this a known AI search bar?
        if (target && (target.id === 'prompt-textarea' || target.getAttribute('contenteditable') === 'true')) {
            const rawPrompt = target.innerText || target.value;
            
            if (rawPrompt.trim().length > 0) {
                console.log("🛡️ Sentinel: Intercepting prompt for redaction check...");
                
                // 🛑 STOP the original submission
                e.preventDefault();
                e.stopImmediatePropagation();
                
                try {
                    // Call the local Sentinel API to scan/redact
                    const response = await fetch('http://localhost:8000/api/scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text: rawPrompt, department: 'GLOBAL_EXTENSION'})
                    });
                    
                    const data = await response.json();
                    
                    // Update the text area with the REDACTED version
                    if (target.value !== undefined) {
                        target.value = data.redacted_text;
                    } else {
                        target.innerText = data.redacted_text;
                    }
                    
                    console.log(`🛡️ Sentinel: Redacted ${data.redactions_count} sensitive entities. Resuming submission...`);
                    
                    // Optional: Auto-click the submit button for them if you want!
                } catch (err) {
                    console.error("🛡️ Sentinel ERROR: Local engine offline. Data LEAK risk detected!", err);
                    alert("Sentinel Security ERROR: Local protection engine is offline. Please start Sentinel Shield before browsing.");
                }
            }
        }
    }
}, true); // Use capture phase to intercept before ChatGPT sees it.
