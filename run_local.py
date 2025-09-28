#!/usr/bin/env python3
"""
Script para rodar a API localmente (sem ngrok)
"""
import uvicorn
from app.config.settings import settings

def main():
    print("🚀 Iniciando API Mercado Livre localmente...")
    print("="*50)
    print("📡 URLs Locais:")
    print(f"   • API: http://localhost:{settings.api_port}")
    print(f"   • Documentação: http://localhost:{settings.api_port}/docs")
    print(f"   • ReDoc: http://localhost:{settings.api_port}/redoc")
    print()
    print("⚠️  IMPORTANTE:")
    print("   • Para usar com Mercado Livre, você precisa do ngrok")
    print("   • Use: python start.py (com ngrok)")
    print("   • Ou configure um servidor público")
    print("="*50)
    print()
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )

if __name__ == "__main__":
    main()
