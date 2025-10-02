// Deutsche Übersetzungen für UI
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
    }
};

// Current language
const currentLang = 'de';

// Translation helper
function t(key) {
    const keys = key.split('.');
    let value = translations[currentLang];
    
    for (const k of keys) {
        value = value?.[k];
    }
    
    return value || key;
}
