#!/usr/bin/env python3
"""
Script para explicar a lógica de sincronização com o Mercado Livre
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Adicionar o diretório do projeto ao path
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import DATABASE_URL

def explain_sync_logic():
    """Explica como funciona a lógica de sincronização"""
    
    print("=== LÓGICA DE SINCRONIZAÇÃO COM MERCADO LIVRE ===\n")
    
    print("✅ **SEMPRE ADICIONAR OU ATUALIZAR - NUNCA DELETAR**\n")
    
    print("1. **VERIFICAÇÃO DE PEDIDO EXISTENTE:**")
    print("   - Sistema verifica se o pedido já existe pelo `ml_order_id`")
    print("   - Se existe: ATUALIZA os dados")
    print("   - Se não existe: CRIA novo pedido")
    print("   - NUNCA deleta pedidos existentes")
    
    print("\n2. **PROCESSO DE SINCRONIZAÇÃO:**")
    print("   - Busca pedidos da API do Mercado Livre")
    print("   - Para cada pedido encontrado:")
    print("     ├─ Verifica se já existe no banco")
    print("     ├─ Se existe: Atualiza dados (status, valores, etc.)")
    print("     └─ Se não existe: Cria novo registro")
    
    print("\n3. **CAMPOS PROTEGIDOS (nunca alterados):**")
    print("   - `id` (ID interno do banco)")
    print("   - `ml_order_id` (ID do Mercado Livre)")
    print("   - `created_at` (data de criação)")
    
    print("\n4. **CAMPOS ATUALIZADOS:**")
    print("   - Status do pedido")
    print("   - Valores monetários")
    print("   - Dados de publicidade")
    print("   - Informações de envio")
    print("   - `updated_at` (data da última atualização)")
    
    print("\n5. **VANTAGENS DESTA ABORDAGEM:**")
    print("   ✅ Preserva histórico completo")
    print("   ✅ Não perde dados importantes")
    print("   ✅ Atualiza informações desatualizadas")
    print("   ✅ Mantém integridade dos dados")
    print("   ✅ Permite análise histórica")
    
    print("\n6. **EXEMPLO PRÁTICO:**")
    print("   - Pedido #2000013288040988 existe no banco")
    print("   - Sincronização encontra o mesmo pedido na API")
    print("   - Sistema ATUALIZA os dados (não cria duplicata)")
    print("   - Se status mudou de 'paid' para 'delivered', atualiza")
    print("   - Se custo de publicidade mudou, atualiza")
    print("   - Mantém todos os dados históricos")
    
    print("\n7. **RESULTADO DA SINCRONIZAÇÃO:**")
    print("   - Novos pedidos: CRIADOS")
    print("   - Pedidos existentes: ATUALIZADOS")
    print("   - Pedidos antigos: MANTIDOS (nunca deletados)")
    print("   - Dados históricos: PRESERVADOS")
    
    print("\n=== CONCLUSÃO ===")
    print("✅ **A sincronização é SEGURA e não deleta dados**")
    print("✅ **Sempre adiciona novos ou atualiza existentes**")
    print("✅ **Preserva histórico completo de vendas**")
    print("✅ **Mantém integridade dos dados**")

if __name__ == "__main__":
    explain_sync_logic()
