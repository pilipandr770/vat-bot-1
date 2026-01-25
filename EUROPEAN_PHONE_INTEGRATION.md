# European Scam Phone Databases Integration

## Overview
The VAT Bot Phone Intelligence service now supports European scam phone databases in addition to the US BlockGuard database. This expands coverage beyond US-only numbers to include European countries like France.

## Supported Countries

### 🇫🇷 France
- **Database Size**: 16 spam prefixes
- **Sources**:
  - `Esdayl/NoPhoneSpam_FR` - Prefix patterns for telemarketing numbers
  - `gitbra/spam` - Individual spam numbers (when available)
  - `alexdyas/spamnumbers-france` - Community-reported spam numbers
- **Format**: Pattern matching (e.g., `+33162?` matches all numbers starting with 0162)
- **Update Frequency**: Manual updates via script

### 🇺🇸 United States
- **Database Size**: 937 numbers
- **Source**: BlockGuard FTC complaints database
- **Format**: Individual E164 numbers
- **Update Frequency**: Automated via `update_scam_db.py`

## Technical Implementation

### Database Structure
```python
# Multiple country databases
scam_databases = {
    'us': {'+12015551234', '+12015556789', ...},  # Individual numbers
    'fr': {'+33162?', '+33163?', '+339476?', ...}  # Pattern prefixes
}
```

### Pattern Matching Logic
- **US**: Exact E164 number matching
- **France**: Prefix pattern matching (e.g., `+33162?` matches `+33162XXXXXXX`)

### Risk Scoring
- **US scam match**: +70 points
- **French pattern match**: +70 points (same as US)
- **Combined heuristics**: Up to +30 additional points
- **Verdict levels**: low (<30), medium (30-69), high (≥70)

## Usage Examples

### French Numbers
```python
service = get_service()

# Telemarketing prefix - HIGH RISK
result = service.analyze("+33162234567")
# Result: risk_score=80, verdict='high', seen_in_scam_db=True

# Regular number - LOW RISK
result = service.analyze("+33123456789")
# Result: risk_score=0, verdict='low', seen_in_scam_db=False
```

### US Numbers (unchanged)
```python
result = service.analyze("+12015551234")
# Works exactly as before
```

## Database Update Scripts

### Update European Databases
```bash
python update_scam_db_eu.py
```
- Downloads latest data from community repositories
- Merges multiple sources
- Saves to `spam_database_fr.txt`

### Update US Database
```bash
python update_scam_db.py
```
- Downloads from BlockGuard repository
- Saves to `spam_database.txt`

## Adding New Countries

To add support for another European country:

1. **Find Data Sources**: Look for community repositories on GitHub
2. **Update Service**: Add country code mapping in `PhoneIntelService.analyze()`
3. **Create Database File**: Add to `_load_scam_databases()`
4. **Update Script**: Add download logic to `update_scam_db_eu.py`

Example for Germany:
```python
# In analyze() method
elif country_code == 49:  # Germany
    country_key = 'de'

# In _load_scam_databases()
databases['de'] = self._load_single_database(german_db_path, 'German scam database')
```

## Data Quality Assessment

### France Database Quality
- ✅ **Coverage**: Good coverage of known telemarketing prefixes
- ✅ **Format**: Consistent pattern-based blocking
- ✅ **Updates**: Community-maintained, regular updates
- ⚠️ **Limitations**: Pattern-based (not individual numbers), may have false positives

### Comparison with US Database
| Aspect | US (BlockGuard) | France (Community) |
|--------|----------------|-------------------|
| **Data Source** | Official FTC complaints | Community reports |
| **Format** | Individual numbers | Prefix patterns |
| **Update Frequency** | Automated | Manual |
| **Accuracy** | High (verified complaints) | Medium (community reports) |
| **Coverage** | Comprehensive | Good for telemarketing |

## Future Enhancements

### Planned Countries
- 🇩🇪 Germany - Search for German spam repositories
- 🇬🇧 United Kingdom - UK telecom authority data
- 🇮🇹 Italy - Italian spam databases
- 🇪🇸 Spain - Spanish telemarketing blacklists

### Paid API Integration
For production use, consider paid APIs:
- **SecurityTrails** ($99/month) - Phone number intelligence
- **Hunter.io** ($49/month) - Phone verification
- **Clearbit** ($99/month) - Business phone validation

## Files Modified

- `app/services/phoneintel.py` - Added multi-country database support
- `update_scam_db_eu.py` - New script for European database updates
- `spam_database_fr.txt` - French scam number database
- `test_european_phoneintel.py` - Test script for European functionality

## Testing

Run the test script to verify European integration:
```bash
python test_european_phoneintel.py
```

Expected output shows French telemarketing prefixes detected as high risk, while regular numbers remain low risk.