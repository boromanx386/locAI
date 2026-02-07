#!/usr/bin/env python3
"""
Vrati transformers na prethodnu verziju
"""

import subprocess
import sys
import os

def restore_version():
    """Vrati verziju iz backup fajla"""
    backup_file = 'transformers_version_backup.txt'
    
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup fajl ne postoji: {backup_file}")
        print("[INFO] Možes ručno da vratis verziju:")
        print("   pip install transformers==4.53.3")
        return False
    
    # Pročitaj verziju iz backup fajla
    version = None
    with open(backup_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('transformers=='):
                version = line.split('==')[1].strip()
                break
    
    if not version:
        print(f"[ERROR] Nije moguce pronaci verziju u {backup_file}")
        return False
    
    print(f"[INFO] Vracanje transformers na verziju: {version}")
    print()
    
    # Instaliraj verziju
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', f'transformers=={version}'],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"[OK] Transformers uspesno vracen na verziju {version}")
            return True
        else:
            print(f"[ERROR] Greska pri vracanju verzije!")
            return False
            
    except Exception as e:
        print(f"[ERROR] Greska: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("VRACANJE TRANSFORMERS VERZIJE")
    print("=" * 50)
    print()
    restore_version()
