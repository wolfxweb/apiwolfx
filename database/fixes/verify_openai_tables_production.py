"""
Script Python para verificar se todas as tabelas e colunas OpenAI foram criadas em produção
Execute este script para verificar o estado atual do banco de dados
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import get_db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_tables():
    """Verifica se todas as tabelas e colunas OpenAI foram criadas"""
    
    db = next(get_db())
    
    try:
        results = {
            "tabelas_principais": [],
            "tabelas_ferramentas": [],
            "colunas_assistants": [],
            "colunas_threads": [],
            "indices": [],
            "ferramentas": [],
            "agentes": []
        }
        
        # 1. Verificar tabelas principais
        logger.info("📋 Verificando tabelas principais...")
        tables_main = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('openai_assistants', 'openai_assistant_threads', 'openai_assistant_messages', 'openai_assistant_usage')
            ORDER BY table_name
        """)).fetchall()
        
        expected_main = ['openai_assistants', 'openai_assistant_threads', 'openai_assistant_messages', 'openai_assistant_usage']
        for table in expected_main:
            exists = any(t[0] == table for t in tables_main)
            results["tabelas_principais"].append({
                "nome": table,
                "existe": exists,
                "status": "✅" if exists else "❌"
            })
        
        # 2. Verificar tabelas de ferramentas
        logger.info("📋 Verificando tabelas de ferramentas...")
        tables_tools = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('openai_tools', 'openai_tool_handlers', 'openai_agent_tools')
            ORDER BY table_name
        """)).fetchall()
        
        expected_tools = ['openai_tools', 'openai_tool_handlers', 'openai_agent_tools']
        for table in expected_tools:
            exists = any(t[0] == table for t in tables_tools)
            results["tabelas_ferramentas"].append({
                "nome": table,
                "existe": exists,
                "status": "✅" if exists else "❌"
            })
        
        # 3. Verificar colunas importantes de openai_assistants
        logger.info("📋 Verificando colunas de openai_assistants...")
        columns_assistants = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'openai_assistants'
            AND column_name IN (
                'memory_enabled', 'memory_data', 'initial_prompt',
                'welcome_message', 'welcome_enabled', 'welcome_use_model'
            )
            ORDER BY column_name
        """)).fetchall()
        
        expected_cols = ['memory_enabled', 'memory_data', 'initial_prompt', 'welcome_message', 'welcome_enabled', 'welcome_use_model']
        for col in expected_cols:
            exists = any(c[0] == col for c in columns_assistants)
            results["colunas_assistants"].append({
                "nome": col,
                "existe": exists,
                "status": "✅" if exists else "❌"
            })
        
        # 4. Verificar índices importantes
        logger.info("📋 Verificando índices...")
        try:
            indices = db.execute(text("""
                SELECT indexname, tablename
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND (
                    indexname LIKE '%openai_assistant_threads%company_id%' OR
                    indexname LIKE '%openai_assistant_threads%user_id%' OR
                    indexname LIKE '%openai_assistant_messages%thread_id%'
                )
                ORDER BY tablename, indexname
            """)).fetchall()
            
            for idx in indices:
                results["indices"].append({
                    "nome": idx[0],
                    "tabela": idx[1],
                    "status": "✅"
                })
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar índices: {e}")
        
        # 5. Verificar ferramentas criadas
        logger.info("📋 Verificando ferramentas...")
        try:
            tools = db.execute(text("""
                SELECT name, description, is_active
                FROM openai_tools
                WHERE name IN ('get_orders', 'get_product_sales')
                ORDER BY name
            """)).fetchall()
            
            expected_tools_names = ['get_orders', 'get_product_sales']
            for tool_name in expected_tools_names:
                tool_data = next((t for t in tools if t[0] == tool_name), None)
                results["ferramentas"].append({
                    "nome": tool_name,
                    "existe": tool_data is not None,
                    "ativo": tool_data[2] if tool_data else False,
                    "status": "✅" if tool_data else "❌"
                })
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar ferramentas (tabela pode não existir): {e}")
        
        # 6. Verificar agente "Analise produto"
        logger.info("📋 Verificando agente 'Analise produto'...")
        try:
            agent = db.execute(text("""
                SELECT id, name, model, is_active
                FROM openai_assistants
                WHERE LOWER(name) LIKE '%analise%produto%'
                ORDER BY id
                LIMIT 1
            """)).fetchone()
            
            results["agentes"].append({
                "nome": "Analise produto",
                "existe": agent is not None,
                "id": agent[0] if agent else None,
                "modelo": agent[2] if agent else None,
                "ativo": agent[3] if agent else False,
                "status": "✅" if agent else "❌"
            })
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar agente (tabela pode não existir): {e}")
        
        # Imprimir resultados
        print("\n" + "="*80)
        print("📊 VERIFICAÇÃO DE TABELAS E COLUNAS OPENAI")
        print("="*80)
        
        print("\n📋 TABELAS PRINCIPAIS:")
        for item in results["tabelas_principais"]:
            print(f"  {item['status']} {item['nome']}")
        
        print("\n🔧 TABELAS DE FERRAMENTAS:")
        for item in results["tabelas_ferramentas"]:
            print(f"  {item['status']} {item['nome']}")
        
        print("\n📝 COLUNAS EXTRAS (openai_assistants):")
        for item in results["colunas_assistants"]:
            print(f"  {item['status']} {item['nome']}")
        
        print("\n🔍 ÍNDICES:")
        if results["indices"]:
            for item in results["indices"]:
                print(f"  {item['status']} {item['nome']} ({item['tabela']})")
        else:
            print("  ⚠️ Nenhum índice encontrado")
        
        print("\n🛠️ FERRAMENTAS:")
        for item in results["ferramentas"]:
            if item['existe']:
                print(f"  {item['status']} {item['nome']} (Ativo: {item['ativo']})")
            else:
                print(f"  {item['status']} {item['nome']} (NÃO EXISTE)")
        
        print("\n🤖 AGENTES:")
        for item in results["agentes"]:
            if item['existe']:
                print(f"  {item['status']} {item['nome']} (ID: {item['id']}, Modelo: {item['modelo']}, Ativo: {item['ativo']})")
            else:
                print(f"  {item['status']} {item['nome']} (NÃO EXISTE)")
        
        print("\n" + "="*80)
        
        # Resumo
        total_ok = sum([
            sum(1 for t in results["tabelas_principais"] if t['existe']),
            sum(1 for t in results["tabelas_ferramentas"] if t['existe']),
            sum(1 for c in results["colunas_assistants"] if c['existe']),
            sum(1 for f in results["ferramentas"] if f['existe']),
            sum(1 for a in results["agentes"] if a['existe'])
        ])
        
        total_expected = (
            len(results["tabelas_principais"]) +
            len(results["tabelas_ferramentas"]) +
            len(results["colunas_assistants"]) +
            len(results["ferramentas"]) +
            len(results["agentes"])
        )
        
        print(f"\n📊 RESUMO: {total_ok}/{total_expected} itens verificados com sucesso")
        
        if total_ok == total_expected:
            print("✅ Todas as tabelas, colunas e dados estão criados corretamente!")
        else:
            print("⚠️ Alguns itens estão faltando. Verifique os logs acima.")
        
        print("="*80 + "\n")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}", exc_info=True)
        return None
    finally:
        db.close()

if __name__ == "__main__":
    verify_tables()

