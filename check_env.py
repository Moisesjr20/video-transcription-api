#!/usr/bin/env python3
"""
Script para verificar variáveis de ambiente
"""

import os
import sys

def check_environment_variables():
    """Verifica se todas as variáveis necessárias estão configuradas"""
    
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", 
        "GOOGLE_REDIRECT_URI",
        "GOOGLE_DRIVE_FOLDER_ID",
        "DESTINATION_EMAIL"
    ]
    
    print("🔍 Verificando variáveis de ambiente...")
    print("=" * 50)
    
    all_configured = True
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * 10}...{value[-10:] if len(value) > 10 else value}")
        else:
            print(f"❌ {var}: NÃO CONFIGURADO")
            all_configured = False
    
    print("=" * 50)
    
    if all_configured:
        print("🎉 Todas as variáveis estão configuradas!")
        return True
    else:
        print("⚠️  Algumas variáveis não estão configuradas.")
        print("\n📋 Configure estas variáveis no Easypanel:")
        print("GOOGLE_CLIENT_ID=1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com")
        print("GOOGLE_CLIENT_SECRET=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")
        print("GOOGLE_REDIRECT_URI=https://transcritor-transcritor.whhc5g.easypanel.host/auth/callback")
        print("GOOGLE_DRIVE_FOLDER_ID=14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG")
        print("DESTINATION_EMAIL=seu-email@gmail.com")
        return False

if __name__ == "__main__":
    success = check_environment_variables()
    sys.exit(0 if success else 1) 