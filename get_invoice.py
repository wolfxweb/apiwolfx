#!/usr/bin/env python3
"""
Script para buscar nota fiscal do pedido específico
"""
import os
import requests
from sqlalchemy import create_engine, text

# Configuração do banco
DATABASE_URL = "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"

def main():
    print("🔍 Buscando nota fiscal do pedido 2000013387431232...")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # 1. Buscar dados do pedido
        print("1. Buscando dados do pedido no banco...")
        order_result = conn.execute(text('''
            SELECT ml_order_id, pack_id, invoice_emitted, invoice_number, invoice_series, invoice_key
            FROM ml_orders 
            WHERE ml_order_id = '2000013387431232' AND company_id = 15
        ''')).fetchone()
        
        if not order_result:
            print("❌ Pedido não encontrado no banco")
            return
        
        ml_order_id, pack_id, invoice_emitted, invoice_number, invoice_series, invoice_key = order_result
        print(f"✅ Pedido encontrado:")
        print(f"   ML Order ID: {ml_order_id}")
        print(f"   Pack ID: {pack_id}")
        print(f"   Invoice Emitted (DB): {invoice_emitted}")
        print(f"   Invoice Number (DB): {invoice_number}")
        print(f"   Invoice Series (DB): {invoice_series}")
        print(f"   Invoice Key (DB): {invoice_key}")
        
        # 2. Buscar token
        print("\n2. Buscando token de acesso...")
        token_result = conn.execute(text('''
            SELECT t.access_token
            FROM tokens t
            JOIN users u ON u.id = t.user_id
            WHERE u.company_id = 15
            AND u.is_active = true
            AND t.is_active = true
            AND t.expires_at > NOW()
            ORDER BY t.expires_at DESC
            LIMIT 1
        ''')).fetchone()
        
        if not token_result:
            print("❌ Token não encontrado")
            return
        
        access_token = token_result[0]
        print(f"✅ Token encontrado: {access_token[:20]}...")
        
        # 3. Buscar pack
        print(f"\n3. Buscando pack {pack_id}...")
        url = f"https://api.mercadolibre.com/packs/{pack_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            pack_data = response.json()
            print(f"   Pack ID: {pack_data.get('id')}")
            
            # 4. Buscar shipment
            shipment = pack_data.get('shipment', {})
            shipment_id = shipment.get('id')
            print(f"   Shipment ID: {shipment_id}")
            
            if shipment_id:
                # 5. Buscar nota fiscal usando endpoint correto da documentação
                print(f"\n4. Buscando nota fiscal no shipment {shipment_id}...")
                # Endpoint correto conforme documentação: /users/{user_id}/invoices/shipments/{shipment_id}
                invoice_url = f"https://api.mercadolibre.com/users/1979794691/invoices/shipments/{shipment_id}"
                invoice_response = requests.get(invoice_url, headers=headers, timeout=30)
                print(f"   Status: {invoice_response.status_code}")
                
                if invoice_response.status_code == 200:
                    invoice_data = invoice_response.json()
                    print(f"✅ Nota fiscal encontrada!")
                    print(f"   ID: {invoice_data.get('id')}")
                    print(f"   Status: {invoice_data.get('status')}")
                    print(f"   Número: {invoice_data.get('invoice_number')}")
                    print(f"   Série: {invoice_data.get('invoice_series')}")
                    print(f"   Chave: {invoice_data.get('attributes', {}).get('invoice_key')}")
                    print(f"   Data: {invoice_data.get('issued_date')}")
                    
                    # 6. Atualizar banco se necessário
                    if not invoice_emitted:
                        print(f"\n5. Atualizando banco de dados...")
                        update_query = text('''
                            UPDATE ml_orders SET
                                invoice_emitted = true,
                                invoice_emitted_at = NOW(),
                                invoice_number = :invoice_number,
                                invoice_series = :invoice_series,
                                invoice_key = :invoice_key,
                                updated_at = NOW()
                            WHERE ml_order_id = '2000013387431232' AND company_id = 15
                        ''')
                        
                        conn.execute(update_query, {
                            "invoice_number": invoice_data.get('invoice_number'),
                            "invoice_series": invoice_data.get('invoice_series'),
                            "invoice_key": invoice_data.get('attributes', {}).get('invoice_key')
                        })
                        conn.commit()
                        print(f"✅ Banco atualizado com sucesso!")
                    else:
                        print(f"\n5. Banco já está atualizado")
                else:
                    print(f"❌ Erro ao buscar nota fiscal: {invoice_response.text[:200]}")
            else:
                print(f"❌ Nenhum shipment encontrado")
        else:
            print(f"❌ Erro ao buscar pack: {response.text[:200]}")

if __name__ == "__main__":
    main()
