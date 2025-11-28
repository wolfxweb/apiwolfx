#!/usr/bin/env python3
"""
Script para limpar mensagens duplicadas no banco de dados
Mantém apenas a primeira ocorrência de cada mensagem única
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistantMessage, OpenAIAssistantThread
from collections import defaultdict

def clean_duplicate_messages(dry_run=True):
    """
    Remove mensagens duplicadas, mantendo apenas a primeira ocorrência
    
    Args:
        dry_run: Se True, apenas mostra o que seria removido sem deletar
    """
    db = SessionLocal()
    
    try:
        print("🔍 Procurando mensagens duplicadas...\n")
        
        # Buscar todas as threads
        threads = db.query(OpenAIAssistantThread).filter(
            OpenAIAssistantThread.is_active == True
        ).all()
        
        total_deleted = 0
        threads_cleaned = []
        
        for thread in threads:
            # Buscar todas as mensagens desta thread ordenadas por data
            messages = db.query(OpenAIAssistantMessage).filter(
                OpenAIAssistantMessage.thread_id == thread.id
            ).order_by(OpenAIAssistantMessage.created_at.asc(), OpenAIAssistantMessage.id.asc()).all()
            
            # Agrupar mensagens por role + content para encontrar duplicatas
            message_groups = defaultdict(list)
            for msg in messages:
                key = (msg.role, msg.content.strip())
                message_groups[key].append(msg)
            
            # Identificar duplicatas (manter a primeira, remover as outras)
            duplicates_to_remove = []
            for key, msg_list in message_groups.items():
                if len(msg_list) > 1:
                    # Manter a primeira (mais antiga), remover as outras
                    first_msg = msg_list[0]
                    duplicates = msg_list[1:]
                    
                    for dup in duplicates:
                        duplicates_to_remove.append({
                            'id': dup.id,
                            'role': dup.role,
                            'content_preview': dup.content[:100] + '...' if len(dup.content) > 100 else dup.content,
                            'created_at': dup.created_at.isoformat() if dup.created_at else None,
                            'first_msg_id': first_msg.id
                        })
            
            if duplicates_to_remove:
                threads_cleaned.append({
                    'thread_id': thread.thread_id,
                    'thread_db_id': thread.id,
                    'duplicates': duplicates_to_remove
                })
        
        # Exibir o que será removido
        if threads_cleaned:
            print(f"📊 Threads com duplicatas: {len(threads_cleaned)}\n")
            
            for thread_info in threads_cleaned:
                print(f"🔴 Thread ID: {thread_info['thread_id']} (DB ID: {thread_info['thread_db_id']})")
                print(f"   Duplicatas a remover: {len(thread_info['duplicates'])}\n")
                
                for dup in thread_info['duplicates']:
                    print(f"   ❌ ID {dup['id']} - {dup['role']}: {dup['content_preview']}")
                    print(f"      Criada em: {dup['created_at']}")
                    print(f"      Mantendo ID: {dup['first_msg_id']}\n")
                
                total_deleted += len(thread_info['duplicates'])
            
            print(f"\n📊 Total de mensagens duplicadas a remover: {total_deleted}")
            
            if dry_run:
                print("\n⚠️  MODO DRY-RUN: Nenhuma mensagem foi removida.")
                print("   Execute com dry_run=False para remover as duplicatas.")
            else:
                # Remover duplicatas
                print("\n🗑️  Removendo duplicatas...")
                for thread_info in threads_cleaned:
                    for dup in thread_info['duplicates']:
                        msg_to_delete = db.query(OpenAIAssistantMessage).filter(
                            OpenAIAssistantMessage.id == dup['id']
                        ).first()
                        if msg_to_delete:
                            db.delete(msg_to_delete)
                            print(f"   ✅ Removida mensagem ID {dup['id']}")
                
                db.commit()
                print(f"\n✅ {total_deleted} mensagens duplicadas foram removidas!")
        else:
            print("✅ Nenhuma duplicação encontrada no banco de dados!")
        
    except Exception as e:
        print(f"❌ Erro ao limpar duplicatas: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Limpar mensagens duplicadas do banco de dados')
    parser.add_argument('--execute', action='store_true', help='Executar a remoção (sem isso, apenas mostra o que seria removido)')
    args = parser.parse_args()
    
    clean_duplicate_messages(dry_run=not args.execute)

