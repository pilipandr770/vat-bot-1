// Main application JavaScript

class CounterpartyVerification {
    constructor() {
        this.initializeEventListeners();
        this.initializeFormValidation();
    }

    initializeEventListeners() {
        // Country selection auto-fill VAT prefix
        const countrySelect = document.getElementById('counterparty_country');
        const vatInput = document.getElementById('counterparty_vat');
        
        if (countrySelect && vatInput) {
            countrySelect.addEventListener('change', (e) => {
                const country = e.target.value;
                const currentVat = vatInput.value;
                
                // Add country prefix if VAT field is empty or doesn't start with country code
                if (country && (!currentVat || !currentVat.startsWith(country))) {
                    vatInput.value = country;
                    vatInput.focus();
                }
            });
        }

        // Real-time VAT format validation
        if (vatInput) {
            vatInput.addEventListener('input', this.validateVATFormat.bind(this));
        }

        // Domain field auto-format
        const domainInput = document.getElementById('counterparty_domain');
        if (domainInput) {
            domainInput.addEventListener('blur', (e) => {
                let domain = e.target.value.trim();
                if (domain && !domain.includes('.')) {
                    domain = domain + '.com';
                }
                if (domain && !domain.startsWith('http') && !domain.startsWith('//')) {
                    domain = domain.replace(/^(https?:\/\/)?(www\.)?/, '');
                }
                e.target.value = domain;
            });
        }
    }

    initializeFormValidation() {
        const form = document.getElementById('verificationForm');
        if (form) {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        }
    }

    validateVATFormat(event) {
        const input = event.target;
        const value = input.value.toUpperCase();
        const country = document.getElementById('counterparty_country').value;
        
        let isValid = true;
        let message = '';

        if (value && country) {
            const vatPattern = this.getVATPattern(country);
            if (vatPattern && !vatPattern.test(value)) {
                isValid = false;
                message = `Невірний формат VAT для ${country}`;
            }
        }

        this.showValidationFeedback(input, isValid, message);
    }

    getVATPattern(country) {
        const patterns = {
            'DE': /^DE[0-9]{9}$/,
            'AT': /^ATU[0-9]{8}$/,
            'NL': /^NL[0-9]{9}B[0-9]{2}$/,
            'FR': /^FR[0-9A-Z]{2}[0-9]{9}$/,
            'IT': /^IT[0-9]{11}$/,
            'ES': /^ES[0-9A-Z][0-9]{7}[0-9A-Z]$/,
            'PL': /^PL[0-9]{10}$/,
            'CZ': /^CZ[0-9]{8,10}$/,
            'GB': /^GB([0-9]{9}([0-9]{3})?|[A-Z]{2}[0-9]{3})$/
        };
        return patterns[country];
    }

    showValidationFeedback(input, isValid, message) {
        // Remove existing feedback
        const existingFeedback = input.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        input.classList.remove('is-valid', 'is-invalid');

        if (input.value) {
            if (isValid) {
                input.classList.add('is-valid');
            } else {
                input.classList.add('is-invalid');
                
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = message;
                input.parentNode.appendChild(feedback);
            }
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        
        if (!this.validateForm()) {
            return;
        }

        const formData = new FormData(event.target);
        
        try {
            this.showLoading(true);
            const response = await this.submitVerification(formData);
            
            if (response.success) {
                this.displayResults(response);
                this.saveToLocalHistory(formData, response);
            } else {
                this.displayError(response.error || 'Невідома помилка');
            }
        } catch (error) {
            console.error('Verification error:', error);
            this.displayError('Помилка з\'єднання: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    validateForm() {
        const requiredFields = [
            'company_vat', 'company_name', 'company_address',
            'counterparty_name', 'counterparty_country'
        ];

        let isValid = true;
        
        requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field && !field.value.trim()) {
                this.showValidationFeedback(field, false, 'Це поле обов\'язкове');
                isValid = false;
            }
        });

        return isValid;
    }

    async submitVerification(formData) {
        const response = await fetch('/verify', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    showLoading(show) {
        const loadingPanel = document.getElementById('loadingPanel');
        const submitButton = document.querySelector('button[type="submit"]');
        
        if (loadingPanel) {
            loadingPanel.style.display = show ? 'block' : 'none';
        }
        
        if (submitButton) {
            submitButton.disabled = show;
            if (show) {
                submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Перевірка...';
            } else {
                submitButton.innerHTML = '<i class="bi bi-search"></i> Запустити перевірку';
            }
        }
    }

    displayResults(data) {
        const resultsPanel = document.getElementById('resultsPanel');
        if (!resultsPanel) return;

        let html = this.generateResultsHTML(data);
        resultsPanel.innerHTML = html;
        resultsPanel.classList.add('fade-in');

        // Initialize tooltips and other interactive elements
        this.initializeResultsInteractivity();
    }

    generateResultsHTML(data) {
        const overallStatusClass = this.getStatusClass(data.overall_status);
        const confidencePercentage = Math.round(data.confidence_score * 100);
        
        let html = `
            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">Загальний результат:</h6>
                    <span class="badge ${overallStatusClass}">${this.getStatusText(data.overall_status)}</span>
                </div>
                <div class="progress">
                    <div class="progress-bar ${this.getProgressBarClass(data.confidence_score)}" 
                         style="width: ${confidencePercentage}%" 
                         title="Рівень довіри: ${confidencePercentage}%">
                        ${confidencePercentage}%
                    </div>
                </div>
                <small class="text-muted">Перевірка ID: ${data.check_id}</small>
            </div>
        `;

        // Services results
        if (data.results && Object.keys(data.results).length > 0) {
            html += '<div class="accordion" id="resultsAccordion">';
            
            let index = 0;
            for (const [service, result] of Object.entries(data.results)) {
                html += this.generateServiceResult(service, result, index);
                index++;
            }
            
            html += '</div>';
        }

        return html;
    }

    generateServiceResult(service, result, index) {
        const serviceName = this.getServiceDisplayName(service);
        const serviceIcon = this.getServiceIcon(service);
        const statusClass = this.getStatusClass(result.status);
        const isExpanded = index === 0 ? 'show' : '';
        const isCollapsed = index === 0 ? '' : 'collapsed';

        return `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${isCollapsed}" type="button" 
                            data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                        <i class="bi ${serviceIcon} me-2"></i>
                        ${serviceName}
                        <span class="badge ${statusClass} ms-auto me-2">
                            ${this.getStatusText(result.status)}
                        </span>
                    </button>
                </h2>
                <div id="collapse${index}" class="accordion-collapse collapse ${isExpanded}" 
                     data-bs-parent="#resultsAccordion">
                    <div class="accordion-body">
                        ${this.formatServiceDetails(service, result)}
                    </div>
                </div>
            </div>
        `;
    }

    formatServiceDetails(service, result) {
        let html = `<div class="mb-3">`;
        
        // Status and confidence
        const confidence = result.confidence || result.confidence_score || 0;
        const confidencePercent = Math.round(confidence * 100);
        
        html += `
            <div class="row mb-2">
                <div class="col-6">
                    <strong>Статус:</strong> ${this.getStatusText(result.status)}
                </div>
                <div class="col-6">
                    <strong>Довіра:</strong> ${confidencePercent}%
                </div>
            </div>
        `;

        // Service-specific data formatting
        if (result.data) {
            html += '<div class="mt-3">';
            html += `<strong>Результат:</strong>`;
            html += `<pre class="bg-light p-2 mt-2 rounded small">${JSON.stringify(result.data, null, 2)}</pre>`;
            html += '</div>';
        }

        // Error message
        if (result.error_message) {
            html += `
                <div class="alert alert-warning mt-3">
                    <i class="bi bi-exclamation-triangle"></i>
                    ${result.error_message}
                </div>
            `;
        }

        // Response time
        if (result.response_time_ms) {
            html += `<small class="text-muted">Час відповіді: ${result.response_time_ms}ms</small>`;
        }

        html += '</div>';
        return html;
    }

    displayError(message) {
        const resultsPanel = document.getElementById('resultsPanel');
        if (!resultsPanel) return;

        resultsPanel.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Помилка:</strong> ${message}
            </div>
        `;
    }

    initializeResultsInteractivity() {
        // Initialize Bootstrap tooltips
        const tooltips = document.querySelectorAll('[title]');
        tooltips.forEach(element => {
            new bootstrap.Tooltip(element);
        });
    }

    saveToLocalHistory(formData, result) {
        try {
            const history = JSON.parse(localStorage.getItem('verificationHistory') || '[]');
            
            const entry = {
                timestamp: new Date().toISOString(),
                company_name: formData.get('company_name'),
                counterparty_name: formData.get('counterparty_name'),
                counterparty_country: formData.get('counterparty_country'),
                overall_status: result.overall_status,
                confidence_score: result.confidence_score,
                check_id: result.check_id
            };
            
            history.unshift(entry);
            history.splice(10); // Keep only last 10 entries
            
            localStorage.setItem('verificationHistory', JSON.stringify(history));
        } catch (error) {
            console.warn('Could not save to local history:', error);
        }
    }

    // Utility methods
    getStatusClass(status) {
        switch(status) {
            case 'valid': return 'bg-success';
            case 'warning': return 'bg-warning text-dark';
            case 'error': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }

    getStatusText(status) {
        switch(status) {
            case 'valid': return '✅ Валідно';
            case 'warning': return '⚠️ Попередження';
            case 'error': return '❌ Проблема';
            default: return '⏳ Очікування';
        }
    }

    getProgressBarClass(score) {
        if (score >= 0.8) return 'bg-success';
        if (score >= 0.6) return 'bg-warning';
        return 'bg-danger';
    }

    getServiceDisplayName(service) {
        const names = {
            'vies': 'VIES VAT Перевірка',
            'handelsregister': 'Handelsregister DE',
            'sanctions': 'Санкційні списки',
            'insolvency': 'Банкрутства',
            'opencorporates': 'OpenCorporates'
        };
        return names[service] || service.toUpperCase();
    }

    getServiceIcon(service) {
        const icons = {
            'vies': 'bi-patch-check',
            'handelsregister': 'bi-building',
            'sanctions': 'bi-shield-exclamation',
            'insolvency': 'bi-exclamation-triangle',
            'opencorporates': 'bi-globe'
        };
        return icons[service] || 'bi-gear';
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new CounterpartyVerification();
});