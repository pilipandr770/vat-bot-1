// UI Translations for multiple languages
const translations = {
    de: {
        statuses: {
            valid: '✅ Gültig',
            warning: '⚠️ Warnung',
            error: '❌ Fehler',
            pending: '⏳ Ausstehend'
        },
        services: {
            vies: 'VIES USt-IdNr. Prüfung',
            handelsregister: 'Handelsregister',
            registry_cz: 'ARES Firmenregister (CZ)',
            registry_pl: 'Polnische White List',
            sanctions: 'Sanktionslisten'
        },
        labels: {
            overall_result: 'Gesamtergebnis:',
            trust_level: 'Vertrauensstufe',
            check_id: 'Prüfung ID',
            status: 'Status:',
            confidence: 'Vertrauen:',
            result: 'Ergebnis:',
            response_time: 'Antwortzeit:',
            error: 'Fehler:'
        },
        messages: {
            processing: 'Wird verarbeitet...',
            connection_error: 'Verbindungsfehler:',
            unknown_error: 'Unbekannter Fehler',
            field_required: 'Dieses Feld ist erforderlich',
            invalid_vat_format: 'Ungültiges USt-IdNr. Format für',
            fill_form: 'Füllen Sie die Formulare aus und klicken Sie auf "Prüfung starten"'
        }
    },
    uk: {
        statuses: {
            valid: '✅ Дійсний',
            warning: '⚠️ Попередження',
            error: '❌ Помилка',
            pending: '⏳ Очікує'
        },
        services: {
            vies: 'Перевірка ПДВ VIES',
            handelsregister: 'Торговельний реєстр',
            registry_cz: 'Реєстр компаній ARES (CZ)',
            registry_pl: 'Польський білий список',
            sanctions: 'Списки санкцій'
        },
        labels: {
            overall_result: 'Загальний результат:',
            trust_level: 'Рівень довіри',
            check_id: 'ID перевірки',
            status: 'Статус:',
            confidence: 'Довіра:',
            result: 'Результат:',
            response_time: 'Час відповіді:',
            error: 'Помилка:'
        },
        messages: {
            processing: 'Обробляється...',
            connection_error: 'Помилка з\'єднання:',
            unknown_error: 'Невідома помилка',
            field_required: 'Це поле обов\'язкове',
            invalid_vat_format: 'Недійсний формат ПДВ для',
            fill_form: 'Заповніть форми та натисніть "Почати перевірку"',
            quota_exceeded_title: 'Ліміт перевірок досягнуто',
            quota_exceeded_desc: 'Ви досягли місячного ліміту перевірок для плану',
            quota_upgrade_desc: 'Оновіть свій план, щоб виконати більше перевірок:',
            upgrade_plan: 'Оновити план',
            to_dashboard: 'До панелі',
            rate_limit_title: 'Забагато запитів',
            rate_limit_desc: 'Ви можете виконати наступну перевірку через',
            seconds: 'секунд',
            auto_verify_completed: 'Автоматична перевірка завершена!',
            auto_verify_saved: 'Дані були автоматично збагачені та збережені у вашій CRM базі даних.',
            auto_verify_id: 'ID перевірки:',
            auto_verify_overall: 'Загальний результат автоматичної перевірки:',
            enriched_data: 'Збагачені дані:',
            sources_used: 'використано джерел'
        }
    }
};

// Get current language from URL parameter or default to German
function getCurrentLang() {
    const urlParams = new URLSearchParams(window.location.search);
    const lang = urlParams.get('lang');
    return translations[lang] ? lang : 'de';
}

// Current language
const currentLang = getCurrentLang();

// Translation helper
function t(key) {
    const keys = key.split('.');
    let value = translations[currentLang];
    
    for (const k of keys) {
        value = value?.[k];
    }
    
    return value || key;
}
