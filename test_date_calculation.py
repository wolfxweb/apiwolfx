#!/usr/bin/env python3
"""
Testar cálculo de datas no dashboard
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta

def test_date_calculation():
    """Testar cálculo de datas no dashboard"""
    print("🔍 Testando Cálculo de Datas no Dashboard")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Simular chamada para Outubro de 2025 (31 dias)
        october_days = 31
        
        print(f"📅 Dias solicitados: {october_days}")
        
        # Simular a lógica do get_sales_dashboard
        end_date = datetime.now()
        start_date = end_date - timedelta(days=october_days)
        
        print(f"📅 Datas calculadas:")
        print(f"   Início: {start_date.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"   Fim: {end_date.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Testar se as datas estão corretas para Outubro
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"\n📅 Datas esperadas para Outubro:")
        print(f"   Início: {october_start.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"   Fim: {october_end.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Verificar se as datas calculadas se sobrepõem com Outubro
        overlaps = (start_date <= october_end and end_date >= october_start)
        print(f"\n🔍 As datas calculadas se sobrepõem com Outubro: {'✅ SIM' if overlaps else '❌ NÃO'}")
        
        # Testar _get_billing_data com as datas calculadas
        billing_data = controller._get_billing_data(company_id, start_date, end_date)
        
        print(f"\n📊 Dados de billing com datas calculadas:")
        if billing_data:
            print(f"   🎯 Marketing: R$ {billing_data.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data.get('periods_count', 0)}")
        else:
            print(f"   ❌ Nenhum dado retornado")
        
        # Testar _get_billing_data com datas específicas de Outubro
        billing_data_october = controller._get_billing_data(company_id, october_start, october_end)
        
        print(f"\n📊 Dados de billing com datas específicas de Outubro:")
        if billing_data_october:
            print(f"   🎯 Marketing: R$ {billing_data_october.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data_october.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data_october.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data_october.get('periods_count', 0)}")
        else:
            print(f"   ❌ Nenhum dado retornado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Testando Cálculo de Datas no Dashboard")
    print("=" * 60)
    print()
    
    success = test_date_calculation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
