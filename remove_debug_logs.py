#!/usr/bin/env python3
"""
Remover logs de debug do arquivo HTML
"""
import re

def remove_debug_logs():
    """Remover logs de debug"""
    html_file = "/Users/wolfx/Documents/wolfx/apiwolfx/app/views/templates/ads_analytics_dashboard.html"
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remover logs de console
    patterns_to_remove = [
        r'console\.log\([^)]*\);',
        r'console\.error\([^)]*\);',
        r'console\.warn\([^)]*\);',
        r'console\.info\([^)]*\);'
    ]
    
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # Remover linhas vazias extras
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Logs de debug removidos com sucesso!")

if __name__ == "__main__":
    remove_debug_logs()
