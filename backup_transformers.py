#!/usr/bin/env python3
"""
Backup trenutne verzije transformers pre ažuriranja
"""

import subprocess
import sys
from datetime import datetime

def backup_current_version():
    """Snimi trenutnu verziju transformers u fajl"""
    try:
        # Pročitaj trenutnu verziju
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', 'transformers'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print("[ERROR] Greska pri citanju transformers verzije!")
            return False
        
        # Parsiraj verziju
        version = None
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
                break
        
        if not version:
            print("[ERROR] Nije moguce pronaci verziju!")
            return False
        
        # Snimi u fajl
        backup_file = 'transformers_version_backup.txt'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f"# Transformers Version Backup\n")
            f.write(f"# Created: {timestamp}\n")
            f.write(f"# Version: {version}\n")
            f.write(f"\n")
            f.write(f"# Da vratiš ovu verziju, pokreni:\n")
            f.write(f"# pip install transformers=={version}\n")
            f.write(f"\n")
            f.write(f"transformers=={version}\n")
        
        print(f"[OK] Backup kreiran: {backup_file}")
        print(f"   Trenutna verzija: {version}")
        print(f"   Timestamp: {timestamp}")
        print()
        print("[INFO] Da vratis verziju nazad, pokreni:")
        print(f"   pip install transformers=={version}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Greska: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("BACKUP TRANSFORMERS VERZIJE")
    print("=" * 50)
    print()
    backup_current_version()
