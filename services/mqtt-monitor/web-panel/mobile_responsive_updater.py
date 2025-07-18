#!/usr/bin/env python3
"""
Mobile Responsive Template Updater
Automatically applies mobile responsiveness to all HTML templates in the Opera-GodEye web panel.
"""

import os
import re
from pathlib import Path

# Mobile responsive CSS to add to all templates
MOBILE_CSS = """
        /* Mobile-First Responsive Design */
        @media (max-width: 768px) {
            .container-xl {
                padding-left: 10px;
                padding-right: 10px;
            }
            
            .page-header {
                padding: 1rem 0;
            }
            
            .page-title {
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
            }
            
            .btn-list {
                flex-direction: column;
                gap: 0.5rem;
                width: 100%;
            }
            
            .btn-list .btn {
                width: 100%;
                margin-bottom: 0.25rem;
            }
            
            .btn-group {
                width: 100%;
            }
            
            .btn-group .btn {
                flex: 1;
                font-size: 0.8rem;
                padding: 0.5rem 0.25rem;
            }
            
            .stats-cards .col-sm-6 {
                margin-bottom: 1rem;
            }
            
            .stat-card {
                padding: 1.5rem 1rem;
            }
            
            .stat-number {
                font-size: 1.8rem;
            }
            
            .stat-label {
                font-size: 0.8rem;
            }
            
            .table-responsive {
                font-size: 0.8rem;
            }
            
            .table th,
            .table td {
                padding: 0.5rem 0.25rem;
                font-size: 0.75rem;
            }
            
            .navbar-brand {
                font-size: 1.2rem;
            }
            
            .navbar-nav .nav-link {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
            }
        }
        
        @media (max-width: 576px) {
            .page-header .col-auto {
                width: 100%;
                margin-top: 1rem;
            }
            
            .page-header .row {
                flex-direction: column;
            }
            
            .stat-number {
                font-size: 1.5rem;
            }
            
            .stat-label {
                font-size: 0.75rem;
            }
            
            .table th,
            .table td {
                padding: 0.4rem 0.2rem;
                font-size: 0.7rem;
            }
        }
        
        @media (max-width: 480px) {
            .container-xl {
                padding-left: 5px;
                padding-right: 5px;
            }
            
            .page-title {
                font-size: 1.3rem;
            }
            
            .stat-number {
                font-size: 1.3rem;
            }
            
            .stat-label {
                font-size: 0.7rem;
            }
        }
        
        /* Touch-friendly interactions for mobile */
        @media (hover: none) and (pointer: coarse) {
            .card:hover {
                transform: none;
            }
            
            .btn:active {
                transform: scale(0.95);
            }
        }
        
        /* Mobile table enhancements */
        @media (max-width: 768px) {
            .table-responsive {
                border: none;
            }
            
            .table th {
                white-space: nowrap;
                min-width: 80px;
            }
            
            .table td {
                vertical-align: middle;
            }
            
            .data-value {
                max-width: 120px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            .topic-badge {
                font-size: 0.65rem;
                padding: 0.15rem 0.3rem;
            }
            
            .status-badge {
                font-size: 0.7rem;
                padding: 0.2rem 0.4rem;
            }
            
            .btn-sm {
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
            }
        }
        
        @media (max-width: 576px) {
            .data-value {
                max-width: 80px;
                font-size: 0.7rem;
            }
            
            .topic-badge {
                font-size: 0.6rem;
                padding: 0.1rem 0.25rem;
            }
            
            .status-badge {
                font-size: 0.65rem;
                padding: 0.15rem 0.3rem;
            }
            
            .btn-sm {
                padding: 0.2rem 0.4rem;
                font-size: 0.7rem;
            }
        }
        
        /* Mobile modal enhancements */
        @media (max-width: 768px) {
            .modal-dialog {
                margin: 0.5rem;
            }
            
            .modal-body {
                padding: 1rem;
            }
            
            .modal-footer {
                padding: 0.75rem 1rem;
            }
            
            .modal-footer .btn {
                width: 100%;
                margin-bottom: 0.5rem;
            }
            
            .modal-footer .btn:last-child {
                margin-bottom: 0;
            }
        }
"""

def update_template_mobile_responsiveness(template_path):
    """Update a single template with mobile responsiveness."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if mobile CSS already exists
        if '/* Mobile-First Responsive Design */' in content:
            print(f"  ✓ {template_path.name} - Already has mobile responsiveness")
            return False
        
        # Find the end of existing CSS styles
        style_pattern = r'(\s*</style>)'
        match = re.search(style_pattern, content)
        
        if match:
            # Insert mobile CSS before closing style tag
            new_content = content[:match.start()] + MOBILE_CSS + match.group(1)
            
            # Update statistics cards to be mobile-friendly
            new_content = re.sub(
                r'<div class="col-sm-6 col-lg-3">',
                '<div class="col-6 col-sm-6 col-lg-3">',
                new_content
            )
            
            # Update stat labels to be responsive
            new_content = re.sub(
                r'<div class="stat-label">([^<]+)</div>',
                r'<div class="stat-label">\n                                    <span class="d-none d-sm-inline">\1</span>\n                                    <span class="d-inline d-sm-none">\1</span>\n                                </div>',
                new_content
            )
            
            # Update page header buttons
            new_content = re.sub(
                r'<button class="btn btn-primary"[^>]*>([^<]*<i[^>]*></i>)\s*([^<]+)</button>',
                r'<button class="btn btn-primary" \1>\n                                    <span class="d-none d-sm-inline">\2</span>\n                                </button>',
                new_content
            )
            
            # Update page titles
            new_content = re.sub(
                r'<h2 class="page-title">([^<]+)</h2>',
                r'<h2 class="page-title">\n                            <span class="d-none d-sm-inline">\1</span>\n                            <span class="d-inline d-sm-none">\1</span>\n                        </h2>',
                new_content
            )
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  ✓ {template_path.name} - Updated with mobile responsiveness")
            return True
            
        else:
            print(f"  ✗ {template_path.name} - No style tag found")
            return False
            
    except Exception as e:
        print(f"  ✗ {template_path.name} - Error: {e}")
        return False

def main():
    """Main function to update all templates."""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("Templates directory not found!")
        return
    
    html_files = list(templates_dir.glob("*.html"))
    
    if not html_files:
        print("No HTML templates found!")
        return
    
    print(f"Found {len(html_files)} HTML templates")
    print("Updating mobile responsiveness...")
    
    updated_count = 0
    
    for template_file in html_files:
        if update_template_mobile_responsiveness(template_file):
            updated_count += 1
    
    print(f"\n✅ Mobile responsiveness update complete!")
    print(f"Updated {updated_count} out of {len(html_files)} templates")

if __name__ == "__main__":
    main() 