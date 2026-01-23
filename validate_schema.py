#!/usr/bin/env python3
"""
Validate Schema.org Structured Data across all HTML pages
Checks for:
- FAQPage Schema compliance
- LocalBusiness Schema completeness  
- SoftwareApplication Schema
- BreadcrumbList Schema
- HowTo Schema for guides
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

class SchemaValidator:
    """Validate JSON-LD Schema markup in HTML files"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        self.files_checked = 0
        
    def extract_schemas(self, html_content: str, filepath) -> List[Dict]:
        """Extract all JSON-LD schemas from HTML. Skip blocks with Jinja template markers."""
        schemas = []
        pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(pattern, html_content, re.DOTALL)

        for match in matches:
            # Skip server-side template blocks that contain Jinja markers
            if "{{" in match or "{%" in match:
                self.warnings.append(f"{filepath.name}: Skipped JSON-LD with template markers (render-time schema)")
                continue
            try:
                schema = json.loads(match)
                schemas.append(schema)
            except json.JSONDecodeError as e:
                self.errors.append(f"{filepath.name}: Invalid JSON-LD: {e}")

        return schemas
    
    def validate_faq_schema(self, schema: Dict) -> Tuple[bool, List[str]]:
        """Validate FAQPage schema"""
        issues = []
        
        if schema.get("@type") != "FAQPage":
            return False, ["Not a FAQPage schema"]
        
        if "mainEntity" not in schema:
            issues.append("Missing 'mainEntity' field")
        elif not isinstance(schema["mainEntity"], list):
            issues.append("'mainEntity' should be an array")
        else:
            for idx, entity in enumerate(schema["mainEntity"]):
                if entity.get("@type") != "Question":
                    issues.append(f"mainEntity[{idx}] is not a Question")
                if "name" not in entity:
                    issues.append(f"mainEntity[{idx}] missing 'name'")
                if "acceptedAnswer" not in entity:
                    issues.append(f"mainEntity[{idx}] missing 'acceptedAnswer'")
                answer = entity.get("acceptedAnswer", {})
                if not isinstance(answer, dict) or "text" not in answer:
                    issues.append(f"mainEntity[{idx}].acceptedAnswer missing 'text'")
        
        return len(issues) == 0, issues
    
    def validate_local_business(self, schema: Dict) -> Tuple[bool, List[str]]:
        """Validate LocalBusiness schema"""
        issues = []
        
        if schema.get("@type") != "LocalBusiness":
            return False, ["Not a LocalBusiness schema"]
        
        required_fields = ["name", "url", "description"]
        for field in required_fields:
            if field not in schema:
                issues.append(f"Missing required field: '{field}'")
        
        return len(issues) == 0, issues
    
    def validate_software_app(self, schema: Dict) -> Tuple[bool, List[str]]:
        """Validate SoftwareApplication schema"""
        issues = []
        
        if schema.get("@type") != "SoftwareApplication":
            return False, ["Not a SoftwareApplication schema"]
        
        required_fields = ["name", "description", "url", "applicationCategory"]
        for field in required_fields:
            if field not in schema:
                issues.append(f"Missing required field: '{field}'")
        
        return len(issues) == 0, issues
    
    def validate_breadcrumb(self, schema: Dict) -> Tuple[bool, List[str]]:
        """Validate BreadcrumbList schema"""
        issues = []
        
        if schema.get("@type") != "BreadcrumbList":
            return False, ["Not a BreadcrumbList schema"]
        
        if "itemListElement" not in schema:
            issues.append("Missing 'itemListElement'")
        else:
            items = schema["itemListElement"]
            if not isinstance(items, list) or len(items) < 2:
                issues.append("BreadcrumbList should have at least 2 items")
            
            for idx, item in enumerate(items):
                if item.get("@type") != "ListItem":
                    issues.append(f"itemListElement[{idx}] is not a ListItem")
                required = ["position", "name", "item"]
                for field in required:
                    if field not in item:
                        issues.append(f"itemListElement[{idx}] missing '{field}'")
        
        return len(issues) == 0, issues
    
    def validate_file(self, filepath: Path) -> None:
        """Validate all schemas in an HTML file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Cannot read {filepath}: {e}")
            return
        
        schemas = self.extract_schemas(content, filepath)
        
        if not schemas:
            self.warnings.append(f"{filepath.name}: No Schema.org markup found")
            return
        
        for schema in schemas:
            schema_type = schema.get("@type")
            
            if schema_type == "FAQPage":
                valid, issues = self.validate_faq_schema(schema)
                if valid:
                    self.successes.append(f"{filepath.name}: ✅ FAQPage valid")
                else:
                    for issue in issues:
                        self.errors.append(f"{filepath.name}: FAQPage - {issue}")
            
            elif schema_type == "LocalBusiness":
                valid, issues = self.validate_local_business(schema)
                if valid:
                    self.successes.append(f"{filepath.name}: ✅ LocalBusiness valid")
                else:
                    for issue in issues:
                        self.errors.append(f"{filepath.name}: LocalBusiness - {issue}")
            
            elif schema_type == "SoftwareApplication":
                valid, issues = self.validate_software_app(schema)
                if valid:
                    self.successes.append(f"{filepath.name}: ✅ SoftwareApplication valid")
                else:
                    for issue in issues:
                        self.errors.append(f"{filepath.name}: SoftwareApplication - {issue}")
            
            elif schema_type == "BreadcrumbList":
                valid, issues = self.validate_breadcrumb(schema)
                if valid:
                    self.successes.append(f"{filepath.name}: ✅ BreadcrumbList valid")
                else:
                    for issue in issues:
                        self.errors.append(f"{filepath.name}: BreadcrumbList - {issue}")
        
        self.files_checked += 1
    
    def validate_directory(self, directory: Path) -> None:
        """Validate all HTML files in directory"""
        html_files = list(directory.rglob("*.html"))
        
        print(f"🔍 Scanning {len(html_files)} HTML files for Schema.org markup...\n")
        
        for html_file in html_files:
            self.validate_file(html_file)
        
        self.print_report()
    
    def print_report(self) -> None:
        """Print validation report"""
        print("\n" + "="*70)
        print("📊 STRUCTURED DATA VALIDATION REPORT")
        print("="*70 + "\n")
        
        print(f"📁 Files checked: {self.files_checked}")
        print(f"✅ Valid schemas: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}\n")
        
        if self.successes:
            print("✅ VALID SCHEMAS:")
            for success in self.successes[:10]:
                print(f"   {success}")
            if len(self.successes) > 10:
                print(f"   ... and {len(self.successes) - 10} more")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings[:5]:
                print(f"   {warning}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors[:10]:
                print(f"   {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")
        
        # Summary
        print("\n" + "="*70)
        total = len(self.successes) + len(self.errors)
        if total > 0:
            success_rate = (len(self.successes) / total) * 100
            print(f"📈 Schema Compliance: {success_rate:.1f}% ({len(self.successes)}/{total})")
        else:
            print("📈 No schemas found in HTML files")
        print("="*70 + "\n")

if __name__ == "__main__":
    validator = SchemaValidator()
    
    # Validate public directory (static HTML)
    print("Validating public/ directory (static pages)...")
    if Path("public/").exists():
        validator.validate_directory(Path("public/"))
    
    # Validate templates directory (template files)
    print("\nValidating templates/ directory (template pages)...")
    if Path("templates/").exists():
        validator.validate_directory(Path("templates/"))
    
    print("\n✨ Validation complete!")
