#!/usr/bin/env python3
"""
Enhance client-side validation and error handling in app.js
"""

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Enhancement 1: Improve submitVerification to handle rate limiting and validation errors
old_submit = '''    async submitVerification(formData) {
        const response = await fetch('/verify', {
            method: 'POST',
            body: formData
        });

        if (response.status === 401) {
            // User not authenticated, redirect to login
            const data = await response.json();
            if (data.redirect) {
                window.location.href = data.redirect;
                return;
            }
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }'''

new_submit = '''    async submitVerification(formData) {
        const response = await fetch('/verify', {
            method: 'POST',
            body: formData
        });

        if (response.status === 401) {
            // User not authenticated, redirect to login
            const data = await response.json();
            if (data.redirect) {
                window.location.href = data.redirect;
                return;
            }
        }

        // Handle 429 (Rate Limit)
        if (response.status === 429) {
            const data = await response.json();
            return {
                success: false,
                error: data.error || 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.',
                rate_limit: true,
                retry_after: data.retry_after
            };
        }

        // Handle 400 (Validation Error)
        if (response.status === 400) {
            const data = await response.json();
            if (data.field) {
                const field = document.querySelector(`[name="${data.field}"]`);
                if (field) {
                    this.showValidationFeedback(field, false, data.error);
                }
            }
            return {
                success: false,
                error: data.error || 'Validierungsfehler in einem Feld',
                validation_error: true
            };
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }'''

if old_submit in content:
    content = content.replace(old_submit, new_submit)
    print('✅ Enhanced submitVerification with error handling')
else:
    print('⚠️ Could not find submitVerification to enhance')

# Enhancement 2: Improve error display
old_error_display = '''        } else {
                // Handle quota exceeded error specially
                if (response.upgrade_required) {
                    this.displayQuotaExceededError(response);
                } else {
                    this.displayError(response.error || 'РќРµРІС–РґРѕРјР° РїРѕРјРёР»РєР°');
                }
            }'''

new_error_display = '''        } else {
                // Handle specific error types
                if (response.upgrade_required) {
                    this.displayQuotaExceededError(response);
                } else if (response.rate_limit) {
                    this.displayRateLimitError(response);
                } else if (response.validation_error) {
                    // Validation error already displayed on field
                    this.displayError(response.error);
                } else {
                    this.displayError(response.error || 'Unbekannter Fehler bei der Überprüfung. Bitte versuchen Sie es später erneut.');
                }
            }'''

if old_error_display in content:
    content = content.replace(old_error_display, new_error_display)
    print('✅ Enhanced error handling in handleFormSubmit')
else:
    print('⚠️ Could not find error handling section')

# Enhancement 3: Add displayRateLimitError method  
insert_point = 'displayQuotaExceededError(response) {'
if insert_point in content:
    # Find the closing brace of displayQuotaExceededError
    start_idx = content.find(insert_point)
    brace_count = 0
    in_method = False
    end_idx = start_idx
    
    for i in range(start_idx, len(content)):
        if content[i] == '{':
            brace_count += 1
            in_method = True
        elif content[i] == '}' and in_method:
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    
    # Insert new method after displayQuotaExceededError
    new_method = '''

    displayRateLimitError(response) {
        const resultsPanel = document.getElementById('resultsPanel');
        if (!resultsPanel) return;

        const retryAfter = response.retry_after || 60;
        const html = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong><i class="bi bi-exclamation-triangle"></i> Zu viele Anfragen</strong>
                <p class="mb-0">${response.error}</p>
                <p class="mb-0 small mt-2">Sie können die nächste Überprüfung in ${retryAfter} Sekunden durchführen.</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        resultsPanel.innerHTML = html;
        resultsPanel.classList.add('fade-in');
    }'''
    
    content = content[:end_idx] + new_method + content[end_idx:]
    print('✅ Added displayRateLimitError method')
else:
    print('⚠️ Could not find insertion point for displayRateLimitError')

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ All enhancements to app.js completed!')
print('📋 Updated:')
print('  - Better error handling for validation errors')
print('  - Rate limiting feedback to users')
print('  - Field-specific error messages')
