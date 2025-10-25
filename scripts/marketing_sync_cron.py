#!/usr/bin/env python3
"""
Script de cron para sincronização automática de custos de marketing.

Este script pode ser executado via cron para sincronização automática:
- Diária: 0 2 * * * (todos os dias às 2h)
- Semanal: 0 3 * * 0 (domingos às 3h)
- Mensal: 0 4 1 * * (dia 1 de cada mês às 4h)

Uso:
    python scripts/marketing_sync_cron.py daily
    python scripts/marketing_sync_cron.py weekly
    python scripts/marketing_sync_cron.py monthly
"""
import sys
import os
import logging
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.marketing_sync_job import (
    cron_daily_sync,
    cron_weekly_sync,
    cron_monthly_sync
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/marketing_sync_cron.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_daily_sync():
    """Executa sincronização diária"""
    logger.info("🚀 Iniciando sincronização diária de custos de marketing")
    try:
        result = cron_daily_sync()
        if result["success"]:
            logger.info(f"✅ Sincronização diária concluída: {result.get('message', 'Sucesso')}")
        else:
            logger.error(f"❌ Erro na sincronização diária: {result.get('error', 'Erro desconhecido')}")
        return result
    except Exception as e:
        logger.error(f"❌ Erro crítico na sincronização diária: {e}")
        return {"success": False, "error": str(e)}

def run_weekly_sync():
    """Executa sincronização semanal"""
    logger.info("🚀 Iniciando sincronização semanal de custos de marketing")
    try:
        result = cron_weekly_sync()
        if result["success"]:
            logger.info(f"✅ Sincronização semanal concluída: {result.get('message', 'Sucesso')}")
        else:
            logger.error(f"❌ Erro na sincronização semanal: {result.get('error', 'Erro desconhecido')}")
        return result
    except Exception as e:
        logger.error(f"❌ Erro crítico na sincronização semanal: {e}")
        return {"success": False, "error": str(e)}

def run_monthly_sync():
    """Executa sincronização mensal"""
    logger.info("🚀 Iniciando sincronização mensal de custos de marketing")
    try:
        result = cron_monthly_sync()
        if result["success"]:
            logger.info(f"✅ Sincronização mensal concluída: {result.get('message', 'Sucesso')}")
        else:
            logger.error(f"❌ Erro na sincronização mensal: {result.get('error', 'Erro desconhecido')}")
        return result
    except Exception as e:
        logger.error(f"❌ Erro crítico na sincronização mensal: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python scripts/marketing_sync_cron.py [daily|weekly|monthly]")
        sys.exit(1)
    
    sync_type = sys.argv[1].lower()
    
    logger.info(f"🤖 Iniciando sincronização {sync_type} em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if sync_type == "daily":
            result = run_daily_sync()
        elif sync_type == "weekly":
            result = run_weekly_sync()
        elif sync_type == "monthly":
            result = run_monthly_sync()
        else:
            logger.error(f"❌ Tipo de sincronização inválido: {sync_type}")
            print(f"Tipo de sincronização inválido: {sync_type}")
            print("Use: daily, weekly ou monthly")
            sys.exit(1)
        
        if result["success"]:
            logger.info("✅ Sincronização concluída com sucesso")
            print("✅ Sincronização concluída com sucesso")
            sys.exit(0)
        else:
            logger.error(f"❌ Sincronização falhou: {result.get('error', 'Erro desconhecido')}")
            print(f"❌ Sincronização falhou: {result.get('error', 'Erro desconhecido')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
