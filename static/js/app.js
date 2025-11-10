// Main application JavaScript

class CounterpartyVerification {
    constructor() {
        this.prefillAbortController = null;
        this.lastPrefillVat = null;
        this.initializeEventListeners();
        this.initializeFormValidation();
    }

    initializeEventListeners() {
        // Country selection auto-fill VAT prefix
        const countrySelect = document.getElementById('counterparty_country');
        const vatInput = document.getElementById('counterparty_vat');
        
        if (countrySelect && vatInput) {
            countrySelect.addEventListener('change', (e) => {
                if (e.target.dataset.prefillApplying === 'true') {
                    return;
                }

                const country = e.target.value;
                const currentVat = vatInput.value;
                
                // Add country prefix if VAT field is empty or doesn't start with country code
                if (country && (!currentVat || !currentVat.startsWith(country))) {
                    vatInput.value = country;
                    vatInput.focus();
                }

                // Allow VAT lookup for same VAT with different country selection
                this.lastPrefillVat = null;
            });
        }

        // Real-time VAT format validation
        if (vatInput) {
            vatInput.addEventListener('input', this.validateVATFormat.bind(this));
            vatInput.addEventListener('blur', this.handleVatPrefill.bind(this));
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

        this.registerPrefillWatchers();
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
                // Handle quota exceeded error specially
                if (response.upgrade_required) {
                    this.displayQuotaExceededError(response);
                } else {
                    this.displayError(response.error || 'Невідома помилка');
                }
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
                this.showValidationFeedback(field, false, 'Dieses Feld ist erforderlich');
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
                submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Prüfung läuft...';
            } else {
                submitButton.innerHTML = '<i class="bi bi-search"></i> Prüfung starten';
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
                    <h6 class="mb-0">Gesamtergebnis:</h6>
                    <span class="badge ${overallStatusClass}">${this.getStatusText(data.overall_status)}</span>
                </div>
                <div class="progress">
                    <div class="progress-bar ${this.getProgressBarClass(data.confidence_score)}" 
                         style="width: ${confidencePercentage}%" 
                         title="Konfidenz: ${confidencePercentage}%">
                        ${confidencePercentage}%
                    </div>
                </div>
                <small class="text-muted">Prüfung ID: ${data.check_id}</small>
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

        // Service-specific formatted data display
        if (result.data) {
            html += '<div class="mt-3">';
            html += this.formatServiceData(service, result.data);
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

    formatServiceData(service, data) {
        switch(service) {
            case 'vies':
                return this.formatVIESData(data);
            case 'handelsregister':
                return this.formatHandelsregisterData(data);
            case 'registry_cz':
                return this.formatCzechRegistryData(data);
            case 'registry_pl':
                return this.formatPolishRegistryData(data);
            case 'sanctions':
                return this.formatSanctionsData(data);
            case 'whois':
            case 'dns':
            case 'ssllabs':
            case 'security_headers':
            case 'robots':
            case 'social_links':
            case 'email_basic':
                return this.formatOSINTData(service, data);
            default:
                // Fallback to formatted JSON for unknown services
                return `<strong>Результат:</strong><pre class="bg-light p-2 mt-2 rounded small">${JSON.stringify(data, null, 2)}</pre>`;
        }
    }

    formatVIESData(data) {
        let html = '<strong>VAT перевірка (VIES):</strong>';
        html += '<div class="mt-2">';

        // Main validation result
        const validIcon = data.valid ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>';
        const validText = data.valid ? 'Дійсний' : 'Недійсний';

        html += `
            <div class="mb-2">
                <strong>Статус VAT:</strong> ${validIcon} ${validText}
            </div>
        `;

        // VAT details
        if (data.country_code && data.vat_number) {
            html += `
                <div class="mb-2">
                    <strong>VAT номер:</strong> ${data.country_code}${data.vat_number}
                </div>
            `;
        }

        // Company information
        if (data.company_name) {
            html += `
                <div class="mb-2">
                    <strong>Назва компанії:</strong> ${data.company_name}
                </div>
            `;
        }

        if (data.company_address) {
            html += `
                <div class="mb-2">
                    <strong>Адреса:</strong> ${data.company_address.replace(/\n/g, '<br>')}
                </div>
            `;
        }

        if (data.request_date) {
            html += `
                <div class="mb-2">
                    <strong>Дата перевірки:</strong> ${new Date(data.request_date).toLocaleString()}
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    formatCzechRegistryData(data) {
        let html = '<strong>ARES Unternehmensregister (Tschechien):</strong>';
        html += '<div class="mt-2">';

        if (data.message) {
            html += `<div class="alert alert-info">${data.message}</div>`;
        }

        if (data.company_name) {
            html += `<div class="mb-2"><strong>Firma:</strong> ${data.company_name}</div>`;
        }

        if (data.ico) {
            html += `<div class="mb-2"><strong>IČO:</strong> ${data.ico}</div>`;
        }

        if (data.legal_form) {
            html += `<div class="mb-2"><strong>Rechtsform:</strong> ${data.legal_form}</div>`;
        }

        if (data.address) {
            const address = typeof data.address === 'string' ? data.address : JSON.stringify(data.address, null, 2);
            html += `<div class="mb-2"><strong>Sitz:</strong> ${address}</div>`;
        }

        if (data.status) {
            html += `<div class="mb-2"><strong>Status:</strong> ${data.status}</div>`;
        }

        html += '</div>';
        return html;
    }

    formatPolishRegistryData(data) {
        let html = '<strong>Biała lista podatników VAT (Polen):</strong>';
        html += '<div class="mt-2">';

        if (data.message) {
            html += `<div class="alert alert-info">${data.message}</div>`;
        }

        if (data.company_name) {
            html += `<div class="mb-2"><strong>Nazwa:</strong> ${data.company_name}</div>`;
        }

        if (data.nip) {
            html += `<div class="mb-2"><strong>NIP:</strong> ${data.nip}</div>`;
        }

        if (data.regon) {
            html += `<div class="mb-2"><strong>REGON:</strong> ${data.regon}</div>`;
        }

        if (data.status_vat) {
            html += `<div class="mb-2"><strong>Status VAT:</strong> ${data.status_vat}</div>`;
        }

        if (Array.isArray(data.account_numbers) && data.account_numbers.length) {
            html += '<div class="mb-2"><strong>Konto bankowe:</strong><ul class="mb-0">';
            data.account_numbers.forEach(account => {
                html += `<li><code>${account}</code></li>`;
            });
            html += '</ul></div>';
        }

        html += '</div>';
        return html;
    }

    formatHandelsregisterData(data) {
        let html = '<strong>Handelsregister (Німеччина):</strong>';
        html += '<div class="mt-2">';

        if (data.message) {
            html += `<div class="alert alert-info">${data.message}</div>`;
        }

        if (data.total_matches !== undefined) {
            html += `<div class="mb-2"><strong>Знайдено записів:</strong> ${data.total_matches}</div>`;
        }

        if (data.best_match) {
            const match = data.best_match;
            html += '<div class="mb-3"><strong>Найкраще співпадіння:</strong></div>';
            html += '<div class="ms-3">';

            if (match.name) html += `<div><strong>Назва:</strong> ${match.name}</div>`;
            if (match.registration_number) html += `<div><strong>Реєстраційний номер:</strong> ${match.registration_number}</div>`;
            if (match.legal_form) html += `<div><strong>Правова форма:</strong> ${match.legal_form}</div>`;
            if (match.address) html += `<div><strong>Адреса:</strong> ${match.address}</div>`;
            if (match.active !== undefined) {
                const activeIcon = match.active ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>';
                html += `<div><strong>Активна:</strong> ${activeIcon} ${match.active ? 'Так' : 'Ні'}</div>`;
            }
            if (match.match_confidence) {
                const confidence = Math.round(match.match_confidence * 100);
                html += `<div><strong>Точність співпадіння:</strong> ${confidence}%</div>`;
            }

            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    formatSanctionsData(data) {
        let html = '<strong>Санкційні списки (EU/OFAC/UK):</strong>';
        html += '<div class="mt-2">';

        if (data.checked_lists) {
            html += `<div class="mb-2"><strong>Перевірені списки:</strong> ${data.checked_lists.join(', ')}</div>`;
        }

        if (data.matches && data.matches.length > 0) {
            html += '<div class="alert alert-danger"><strong>⚠️ Знайдені співпадіння в санкційних списках!</strong></div>';
            data.matches.forEach(match => {
                html += '<div class="ms-3 mb-2 p-2 border-start border-danger border-3">';
                if (match.name) html += `<div><strong>Ім'я:</strong> ${match.name}</div>`;
                if (match.list) html += `<div><strong>Список:</strong> ${match.list}</div>`;
                if (match.reason) html += `<div><strong>Причина:</strong> ${match.reason}</div>`;
                html += '</div>';
            });
        } else {
            html += '<div class="alert alert-success"><strong>✅ Співпадінь у санкційних списках не знайдено</strong></div>';
        }

        if (data.last_updated) {
            html += `<div class="mt-2"><small class="text-muted">Останнє оновлення: ${new Date(data.last_updated).toLocaleString()}</small></div>`;
        }

        html += '</div>';
        return html;
    }

    formatOSINTData(service, data) {
        const serviceNames = {
            'whois': 'WHOIS інформація',
            'dns': 'DNS записи',
            'ssllabs': 'SSL сертифікат',
            'security_headers': 'Заголовки безпеки',
            'robots': 'Robots.txt',
            'social_links': 'Соціальні мережі',
            'email_basic': 'Email перевірка'
        };

        const displayName = serviceNames[service] || service.toUpperCase();
        let html = `<strong>${displayName}:</strong>`;
        html += '<div class="mt-2">';

        if (data.status === 'ok' || data.status === 'success') {
            html += '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Дані отримані успішно</div>';
        } else if (data.status === 'warn' || data.status === 'warning') {
            html += '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Неповні дані</div>';
        } else if (data.status === 'error') {
            html += '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Помилка отримання даних</div>';
        }

        // Format specific data based on service type
        if (service === 'whois' && data.domain_name) {
            html += '<div class="row">';
            html += '<div class="col-md-6">';
            if (data.domain_name) html += `<div><strong>Домен:</strong> ${Array.isArray(data.domain_name) ? data.domain_name[0] : data.domain_name}</div>`;
            if (data.registrar) html += `<div><strong>Реєстратор:</strong> ${data.registrar}</div>`;
            html += '</div>';
            html += '<div class="col-md-6">';
            if (data.creation_date) html += `<div><strong>Створений:</strong> ${new Date(data.creation_date).toLocaleDateString()}</div>`;
            if (data.expiration_date) html += `<div><strong>Закінчується:</strong> ${new Date(data.expiration_date).toLocaleDateString()}</div>`;
            html += '</div>';
            html += '</div>';
        }

        else if (service === 'dns' && data.records) {
            html += '<div><strong>DNS записи:</strong></div>';
            html += '<div class="ms-3">';
            Object.entries(data.records).forEach(([type, records]) => {
                html += `<div><strong>${type}:</strong> ${Array.isArray(records) ? records.join(', ') : records}</div>`;
            });
            html += '</div>';
        }

        else if (service === 'ssllabs' && data.grade) {
            const gradeColor = data.grade === 'A+' || data.grade === 'A' ? 'success' :
                             data.grade === 'B' ? 'warning' : 'danger';
            html += `<div><strong>SSL оцінка:</strong> <span class="badge bg-${gradeColor}">${data.grade}</span></div>`;
            if (data.valid_from) html += `<div><strong>Дійсний з:</strong> ${new Date(data.valid_from).toLocaleDateString()}</div>`;
            if (data.valid_until) html += `<div><strong>Дійсний до:</strong> ${new Date(data.valid_until).toLocaleDateString()}</div>`;
        }

        else if (service === 'security_headers') {
            const headers = data.headers || {};
            const securityScore = data.security_score || 0;
            const scoreColor = securityScore >= 80 ? 'success' : securityScore >= 60 ? 'warning' : 'danger';

            html += `<div><strong>Рівень безпеки:</strong> <span class="badge bg-${scoreColor}">${securityScore}/100</span></div>`;

            if (Object.keys(headers).length > 0) {
                html += '<div class="mt-2"><strong>Заголовки:</strong></div>';
                html += '<div class="ms-3 small">';
                Object.entries(headers).forEach(([key, value]) => {
                    html += `<div><code>${key}: ${value}</code></div>`;
                });
                html += '</div>';
            }
        }

        else if (service === 'email_basic' && data.valid !== undefined) {
            const validIcon = data.valid ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>';
            const validText = data.valid ? 'Дійсний' : 'Недійсний';
            html += `<div><strong>Статус email:</strong> ${validIcon} ${validText}</div>`;

            if (data.mx_records) {
                html += `<div><strong>MX сервери:</strong> ${data.mx_records.join(', ')}</div>`;
            }
        }

        else if (service === 'robots' && data.allowed) {
            html += '<div><strong>Доступність для пошукових систем:</strong></div>';
            html += '<div class="ms-3">';
            html += `<div><strong>Дозволені шляхи:</strong> ${data.allowed.join(', ')}</div>`;
            if (data.disallowed && data.disallowed.length > 0) {
                html += `<div><strong>Заборонені шляхи:</strong> ${data.disallowed.join(', ')}</div>`;
            }
            html += '</div>';
        }

        else if (service === 'social_links' && data.profiles) {
            html += '<div><strong>Знайдені профілі в соцмережах:</strong></div>';
            html += '<div class="ms-3">';
            data.profiles.forEach(profile => {
                html += `<div><i class="bi bi-${profile.platform}"></i> <a href="${profile.url}" target="_blank">${profile.platform}</a></div>`;
            });
            html += '</div>';
        }

        // Show notes if available
        if (data.notes) {
            html += `<div class="mt-2"><small class="text-muted">${data.notes}</small></div>`;
        }

        // Fallback: show raw data if no specific formatting
        if (html === `<strong>${displayName}:</strong><div class="mt-2">` + (data.status ? (data.status === 'ok' || data.status === 'success' ?
            '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Дані отримані успішно</div>' :
            data.status === 'warn' || data.status === 'warning' ?
            '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Неповні дані</div>' :
            '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Помилка отримання даних</div>') : '')) {
            html += `<pre class="bg-light p-2 mt-2 rounded small">${JSON.stringify(data, null, 2)}</pre>`;
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
                <strong>Fehler:</strong> ${message}
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
            case 'valid': return '✅ Gültig';
            case 'warning': return '⚠️ Warnung';
            case 'error': return '❌ Problem';
            case 'ok': return '✅ OK';
            case 'success': return '✅ Erfolgreich';
            case 'warn': return '⚠️ Warnung';
            default: return '⏳ Warten';
        }
    }

    getProgressBarClass(score) {
        if (score >= 0.8) return 'bg-success';
        if (score >= 0.6) return 'bg-warning';
        return 'bg-danger';
    }

    getServiceDisplayName(service) {
        const names = {
            'vies': 'VIES VAT Überprüfung',
            'handelsregister': 'Handelsregister DE',
            'registry_cz': 'ARES Firmenregister CZ',
            'registry_pl': 'Polen VAT-White-List',
            'sanctions': 'Sanktionslisten EU/OFAC/UK',
            'insolvency': 'Insolvenzbekanntmachungen',
            'opencorporates': 'OpenCorporates',
            'whois': 'WHOIS Domain-Info',
            'dns': 'DNS Records',
            'ssllabs': 'SSL Zertifikat Analyse',
            'security_headers': 'Sicherheits-Header',
            'robots': 'Robots.txt Analyse',
            'social_links': 'Soziale Netzwerke',
            'email_basic': 'E-Mail Validierung'
        };
        return names[service] || service.toUpperCase();
    }

    getServiceIcon(service) {
        const icons = {
            'vies': 'bi-patch-check',
            'handelsregister': 'bi-building',
            'registry_cz': 'bi-bank',
            'registry_pl': 'bi-bank2',
            'sanctions': 'bi-shield-exclamation',
            'insolvency': 'bi-exclamation-triangle',
            'opencorporates': 'bi-globe'
        };
        return icons[service] || 'bi-gear';
    }

    registerPrefillWatchers() {
        const fields = document.querySelectorAll('[data-prefill-watch="true"]');
        fields.forEach((field) => {
            if (!field.dataset.autofilled) {
                field.dataset.autofilled = 'false';
            }
            if (!field.dataset.userEdited) {
                field.dataset.userEdited = field.value ? 'true' : 'false';
            }

            const handler = () => {
                if (field.dataset.prefillApplying === 'true') {
                    field.dataset.prefillApplying = 'false';
                    return;
                }
                this.markManualEdit(field);
            };

            if (field.tagName === 'SELECT') {
                field.addEventListener('change', handler);
            } else {
                field.addEventListener('input', handler);
            }
        });
    }

    markManualEdit(field) {
        field.dataset.userEdited = 'true';
        field.dataset.autofilled = 'false';
        field.classList.remove('autofill-highlight');
        const group = field.closest('.mb-3, .form-group');
        if (group) {
            group.querySelectorAll('.autofill-highlight').forEach((el) => {
                el.classList.remove('autofill-highlight');
            });
        }
    }

    async handleVatPrefill(event) {
        const vatRaw = (event.target.value || '').trim().toUpperCase();
        if (!vatRaw || vatRaw.length < 4) {
            this.lastPrefillVat = null;
            this.showVatPrefillMessages({ messages: [] }, true);
            return;
        }

        if (vatRaw === this.lastPrefillVat) {
            return;
        }

        if (this.prefillAbortController) {
            this.prefillAbortController.abort();
        }

        this.prefillAbortController = new AbortController();

        const payload = { vat_number: vatRaw };
        const countrySelect = document.getElementById('counterparty_country');
        if (countrySelect && countrySelect.value) {
            payload.country_code = countrySelect.value;
        }

        this.showVatPrefillMessages('search');

        try {
            const response = await fetch('/api/vat-lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: this.prefillAbortController.signal
            });

            if (response.status === 401) {
                const data = await response.json();
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
                return;
            }

            const data = await response.json();

            if (response.ok && data.success) {
                this.lastPrefillVat = vatRaw;
                this.applyPrefill(data.prefill || {});
                this.showVatPrefillMessages(data);
            } else {
                this.lastPrefillVat = null;
                this.showVatPrefillMessages(data, true);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            this.lastPrefillVat = null;
            this.showVatPrefillMessages({
                messages: [{ level: 'danger', text: error.message || 'Unbekannter Fehler beim VAT-Lookup' }]
            }, true);
        } finally {
            this.prefillAbortController = null;
        }
    }

    applyPrefill(prefill) {
        if (!prefill) return;

        const vatInput = document.getElementById('counterparty_vat');
        if (prefill.counterparty_vat && vatInput) {
            this.setFieldValue(vatInput, prefill.counterparty_vat.toUpperCase());
        }

        if (prefill.counterparty_name) {
            const nameField = document.getElementById('counterparty_name');
            this.setFieldValue(nameField, prefill.counterparty_name);
        }

        if (prefill.counterparty_address) {
            const addressField = document.getElementById('counterparty_address');
            this.setFieldValue(addressField, prefill.counterparty_address);
        }

        if (prefill.counterparty_country) {
            this.setSelectValue(document.getElementById('counterparty_country'), prefill.counterparty_country);
        }

        if (prefill.counterparty_domain) {
            const domainField = document.getElementById('counterparty_domain');
            this.setFieldValue(domainField, prefill.counterparty_domain);
        }
    }

    setFieldValue(field, value) {
        if (!field || value === undefined || value === null) {
            return;
        }
        if (field.dataset.userEdited === 'true' && field.value) {
            return;
        }
        field.dataset.prefillApplying = 'true';
        field.value = value;
        field.dataset.autofilled = 'true';
        field.dataset.userEdited = 'false';
        field.classList.add('autofill-highlight');
        setTimeout(() => field.classList.remove('autofill-highlight'), 3500);
        field.dataset.prefillApplying = 'false';
    }

    setSelectValue(select, value) {
        if (!select || !value) {
            return;
        }

        if (select.dataset.userEdited === 'true' && select.value) {
            return;
        }

        let option = Array.from(select.options).find(opt => opt.value === value);
        if (!option) {
            option = new Option(value, value, true, true);
            select.add(option);
        } else {
            option.selected = true;
        }

        select.dataset.prefillApplying = 'true';
        select.dataset.autofilled = 'true';
        select.dataset.userEdited = 'false';
        select.classList.add('autofill-highlight');
        setTimeout(() => select.classList.remove('autofill-highlight'), 3500);
        select.dispatchEvent(new Event('change', { bubbles: true }));
        select.dataset.prefillApplying = 'false';
    }

    showVatPrefillMessages(payload, isError = false) {
        const hintEl = document.getElementById('vatPrefillHint');
        if (!hintEl) return;

        if (payload === 'search') {
            hintEl.innerHTML = '<span class="text-primary"><span class="spinner-border spinner-border-sm me-2"></span>Daten werden anhand der VAT-Nummer gesucht...</span>';
            return;
        }

        const messages = (payload && payload.messages) ? [...payload.messages] : [];
        if ((!messages.length) && payload && payload.error) {
            messages.push({ level: 'danger', text: payload.error });
        }

        if (!messages.length) {
            hintEl.innerHTML = isError ? '' : '<span class="text-success"><i class="bi bi-check-circle"></i> VAT-Daten geladen</span>';
            return;
        }

        const levelClass = {
            success: 'text-success',
            info: 'text-primary',
            warning: 'text-warning',
            danger: 'text-danger',
            error: 'text-danger'
        };

        const levelIcon = {
            success: 'bi-check-circle',
            info: 'bi-info-circle',
            warning: 'bi-exclamation-triangle',
            danger: 'bi-exclamation-octagon',
            error: 'bi-exclamation-octagon'
        };

        hintEl.innerHTML = messages.map((msg) => {
            const level = msg.level || 'info';
            const css = levelClass[level] || 'text-primary';
            const icon = levelIcon[level] || 'bi-info-circle';
            return `<span class="d-block ${css}"><i class="bi ${icon} me-1"></i>${msg.text}</span>`;
        }).join('');
    }

    displayQuotaExceededError(response) {
        const resultsPanel = document.getElementById('resultsPanel');
        if (!resultsPanel) return;

        const planName = response.current_plan || 'Free';
        const currentUsage = response.current_usage || 0;
        const limit = response.limit || 5;

        let html = `
            <div class="alert alert-warning" role="alert">
                <h5 class="alert-heading">
                    <i class="bi bi-exclamation-triangle-fill"></i> Prüfungslimit erreicht
                </h5>
                <p>Sie haben Ihr monatliches Prüfungslimit für den ${planName}-Plan erreicht.</p>
                <div class="mb-3">
                    <div class="progress">
                        <div class="progress-bar bg-warning" role="progressbar" 
                             style="width: 100%" 
                             aria-valuenow="${currentUsage}" 
                             aria-valuemin="0" 
                             aria-valuemax="${limit}">
                            ${currentUsage} / ${limit === 'unlimited' ? '∞' : limit}
                        </div>
                    </div>
                </div>
                <p class="mb-3">Upgraden Sie Ihren Plan, um weitere Prüfungen durchzuführen:</p>
                <div class="d-flex gap-2">
                    <a href="/payments" class="btn btn-primary">
                        <i class="bi bi-credit-card"></i> Plan upgraden
                    </a>
                    <a href="/dashboard" class="btn btn-outline-secondary">
                        <i class="bi bi-house"></i> Zum Dashboard
                    </a>
                </div>
            </div>
        `;

        resultsPanel.innerHTML = html;
        resultsPanel.classList.add('fade-in');
    }
}