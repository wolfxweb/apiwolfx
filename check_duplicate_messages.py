#!/usr/bin/env python3
"""
Script para verificar se há mensagens duplicadas no banco de dados
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistantMessage, OpenAIAssistantThread
from sqlalchemy import func, and_
from collections import defaultdict

def check_duplicate_messages():
    """Verifica se há mensagens duplicadas no banco de dados"""
    db = SessionLocal()
    
    try:
        print("🔍 Verificando mensagens duplicadas no banco de dados...\n")
        
        # Buscar todas as threads
        threads = db.query(OpenAIAssistantThread).filter(
            OpenAIAssistantThread.is_active == True
        ).all()
        
        print(f"📊 Total de threads ativas: {len(threads)}\n")
        
        total_duplicates = 0
        threads_with_duplicates = []
        
        for thread in threads:
            # Buscar todas as mensagens desta thread
            messages = db.query(OpenAIAssistantMessage).filter(
                OpenAIAssistantMessage.thread_id == thread.id
            ).order_by(OpenAIAssistantMessage.created_at.asc()).all()
            
            # Agrupar mensagens por role + content para encontrar duplicatas
            message_groups = defaultdict(list)
            for msg in messages:
                key = (msg.role, msg.content.strip())
                message_groups[key].append(msg)
            
            # Verificar se há duplicatas
            duplicates_in_thread = []
            for key, msg_list in message_groups.items():
                if len(msg_list) > 1:
                    duplicates_in_thread.append({
                        'role': key[0],
                        'content_preview': key[1][:100] + '...' if len(key[1]) > 100 else key[1],
                        'count': len(msg_list),
                        'ids': [msg.id for msg in msg_list],
                        'created_at': [msg.created_at.isoformat() if msg.created_at else None for msg in msg_list]
                    })
            
            if duplicates_in_thread:
                total_duplicates += sum(d['count'] - 1 for d in duplicates_in_thread)  # -1 porque uma é original
                threads_with_duplicates.append({
                    'thread_id': thread.thread_id,
                    'thread_db_id': thread.id,
                    'assistant_id': thread.assistant_id,
                    'duplicates': duplicates_in_thread
                })
        
        # Exibir resultados
        if threads_with_duplicates:
            print(f"❌ ENCONTRADAS DUPLICAÇÕES!\n")
            print(f"📊 Total de threads com duplicatas: {len(threads_with_duplicates)}")
            print(f"📊 Total de mensagens duplicadas: {total_duplicates}\n")
            
            for thread_info in threads_with_duplicates:
                print(f"🔴 Thread ID: {thread_info['thread_id']} (DB ID: {thread_info['thread_db_id']})")
                print(f"   Assistant ID: {thread_info['assistant_id']}")
                print(f"   Duplicatas encontradas: {len(thread_info['duplicates'])}")
                
                for dup in thread_info['duplicates']:
                    print(f"\n   📝 Mensagem duplicada:")
                    print(f"      Role: {dup['role']}")
                    print(f"      Conteúdo: {dup['content_preview']}")
                    print(f"      Quantidade: {dup['count']} cópias")
                    print(f"      IDs: {dup['ids']}")
                    print(f"      Datas: {dup['created_at']}")
                print()
        else:
            print("✅ Nenhuma duplicação encontrada no banco de dados!\n")
            print("💡 Se você está vendo duplicação na tela, o problema pode ser:")
            print("   1. Renderização duplicada no frontend")
            print("   2. Mensagens sendo adicionadas múltiplas vezes no DOM")
            print("   3. Problema na função loadConversation ou renderMessages")
        
        # Estatísticas gerais
        total_messages = db.query(OpenAIAssistantMessage).count()
        print(f"\n📊 Estatísticas gerais:")
        print(f"   Total de mensagens no banco: {total_messages}")
        print(f"   Total de threads: {len(threads)}")
        
        # Verificar mensagens por role
        messages_by_role = db.query(
            OpenAIAssistantMessage.role,
            func.count(OpenAIAssistantMessage.id).label('count')
        ).group_by(OpenAIAssistantMessage.role).all()
        
        print(f"\n📊 Mensagens por role:")
        for role, count in messages_by_role:
            print(f"   {role}: {count}")
        
    except Exception as e:
        print(f"❌ Erro ao verificar duplicatas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_duplicate_messages()

