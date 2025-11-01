"""
Sistema de logging global para todo o sistema
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os

class GlobalLogger:
    """Logger global para todo o sistema"""
    
    def __init__(self, log_dir: str = "app/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger("global_system")
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            # Handler para arquivo geral
            general_handler = logging.FileHandler(
                self.log_dir / "system.log",
                encoding='utf-8'
            )
            general_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            general_handler.setFormatter(formatter)
            
            self.logger.addHandler(general_handler)
    
    def log_event(self, event_type: str, data: Dict[str, Any], company_id: Optional[int] = None, success: bool = True, error_message: Optional[str] = None):
        """Log genérico para qualquer evento do sistema"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "company_id": company_id,
                "success": success,
                "error_message": error_message,
                "data": data
            }
            
            # Log geral
            if success:
                self.logger.info(f"✅ {event_type}: {data.get('description', 'Evento processado')} - Company: {company_id}")
            else:
                self.logger.error(f"❌ {event_type}: {data.get('description', 'Erro no evento')} - Company: {company_id} - Erro: {error_message}")
            
            # Log específico por empresa se company_id fornecido
            if company_id:
                self._log_to_company_file(company_id, log_entry)
            
            # Log específico por tipo de evento
            self._log_to_event_file(event_type, log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar evento {event_type}: {e}")
    
    def log_api_call(self, endpoint: str, method: str, company_id: Optional[int] = None, user_id: Optional[int] = None, success: bool = True, response_time: Optional[float] = None, error_message: Optional[str] = None):
        """Log para chamadas de API"""
        data = {
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "response_time": response_time,
            "description": f"API {method} {endpoint}"
        }
        self.log_event("api_call", data, company_id, success, error_message)
    
    def log_database_operation(self, operation: str, table: str, record_id: Optional[str] = None, company_id: Optional[int] = None, success: bool = True, error_message: Optional[str] = None):
        """Log para operações de banco de dados"""
        data = {
            "operation": operation,
            "table": table,
            "record_id": record_id,
            "description": f"DB {operation} on {table}"
        }
        self.log_event("database_operation", data, company_id, success, error_message)
    
    def log_external_api_call(self, service: str, endpoint: str, company_id: Optional[int] = None, success: bool = True, response_code: Optional[int] = None, error_message: Optional[str] = None):
        """Log para chamadas a APIs externas"""
        data = {
            "service": service,
            "endpoint": endpoint,
            "response_code": response_code,
            "description": f"External API {service}: {endpoint}"
        }
        self.log_event("external_api_call", data, company_id, success, error_message)
    
    def log_notification_received(self, notification_data: Dict[str, Any], company_id: int):
        """Log quando uma notificação é recebida"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "notification_received",
                "company_id": company_id,
                "topic": notification_data.get("topic"),
                "resource": notification_data.get("resource"),
                "ml_user_id": notification_data.get("user_id"),
                "application_id": notification_data.get("application_id"),
                "attempts": notification_data.get("attempts"),
                "sent": notification_data.get("sent"),
                "received": notification_data.get("received")
            }
            
            # Log geral
            self.logger.info(f"📬 Notificação recebida: {notification_data.get('topic')} - Company: {company_id}")
            
            # Log específico por empresa
            self._log_to_company_file(company_id, log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar notificação recebida: {e}")
    
    def log_notification_processed(self, notification_data: Dict[str, Any], company_id: int, success: bool, error_message: Optional[str] = None):
        """Log quando uma notificação é processada"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "notification_processed",
                "company_id": company_id,
                "topic": notification_data.get("topic"),
                "resource": notification_data.get("resource"),
                "ml_user_id": notification_data.get("user_id"),
                "success": success,
                "error_message": error_message
            }
            
            if success:
                self.logger.info(f"✅ Notificação processada com sucesso: {notification_data.get('topic')} - Company: {company_id}")
            else:
                self.logger.error(f"❌ Erro ao processar notificação: {notification_data.get('topic')} - Company: {company_id} - Erro: {error_message}")
            
            # Log específico por empresa
            self._log_to_company_file(company_id, log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar processamento: {e}")
    
    def log_order_processed(self, order_id: str, company_id: int, success: bool, action: str, error_message: Optional[str] = None):
        """Log específico para processamento de pedidos"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "order_processed",
                "company_id": company_id,
                "order_id": order_id,
                "action": action,  # "created", "updated", "error"
                "success": success,
                "error_message": error_message
            }
            
            if success:
                self.logger.info(f"📦 Pedido {action}: {order_id} - Company: {company_id}")
            else:
                self.logger.error(f"❌ Erro ao {action} pedido {order_id} - Company: {company_id} - Erro: {error_message}")
            
            # Log específico por empresa
            self._log_to_company_file(company_id, log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar pedido: {e}")
    
    def log_product_processed(self, item_id: str, company_id: int, success: bool, action: str, error_message: Optional[str] = None):
        """Log específico para processamento de produtos"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "product_processed",
                "company_id": company_id,
                "item_id": item_id,
                "action": action,  # "created", "updated", "error"
                "success": success,
                "error_message": error_message
            }
            
            if success:
                self.logger.info(f"🏷️ Produto {action}: {item_id} - Company: {company_id}")
            else:
                self.logger.error(f"❌ Erro ao {action} produto {item_id} - Company: {company_id} - Erro: {error_message}")
            
            # Log específico por empresa
            self._log_to_company_file(company_id, log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar produto: {e}")
    
    def log_question_processed(self, question_id: int, company_id: int, ml_account_id: Optional[int] = None, success: bool = True, action: str = "created", error_message: Optional[str] = None, question_data: Optional[Dict[str, Any]] = None):
        """Log específico para processamento de perguntas"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "question_processed",
                "company_id": company_id,
                "question_id": question_id,
                "ml_account_id": ml_account_id,
                "action": action,  # "created", "updated", "error"
                "success": success,
                "error_message": error_message
            }
            
            # Adicionar dados da pergunta se disponível
            if question_data:
                log_entry["question_details"] = {
                    "item_id": question_data.get("item", {}).get("id") if isinstance(question_data.get("item"), dict) else None,
                    "item_title": question_data.get("item", {}).get("title") if isinstance(question_data.get("item"), dict) else None,
                    "status": question_data.get("status"),
                    "has_answer": bool(question_data.get("answer")),
                    "buyer_nickname": question_data.get("from", {}).get("nickname") if isinstance(question_data.get("from"), dict) else None,
                    "question_text_length": len(question_data.get("text", "")) if question_data.get("text") else 0
                }
            
            if success:
                self.logger.info(f"❓ Pergunta {action}: {question_id} - Company: {company_id} - ML Account: {ml_account_id}")
            else:
                self.logger.error(f"❌ Erro ao {action} pergunta {question_id} - Company: {company_id} - ML Account: {ml_account_id} - Erro: {error_message}")
            
            # Log específico por empresa
            self._log_to_company_file(company_id, log_entry)
            
            # Log específico para eventos de pergunta
            self._log_to_event_file("question_processed", log_entry)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao logar pergunta: {e}")
    
    def _log_to_company_file(self, company_id: int, log_entry: Dict[str, Any]):
        """Log específico para arquivo da empresa"""
        try:
            company_log_file = self.log_dir / f"company_{company_id}.log"
            
            with open(company_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao escrever log da empresa {company_id}: {e}")
    
    def _log_to_event_file(self, event_type: str, log_entry: Dict[str, Any]):
        """Log específico para arquivo do tipo de evento"""
        try:
            # Sanitizar nome do arquivo
            safe_event_type = event_type.replace("/", "_").replace("\\", "_").replace(":", "_")
            event_log_file = self.log_dir / f"{safe_event_type}.log"
            
            with open(event_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao escrever log do evento {event_type}: {e}")
    
    def get_company_logs(self, company_id: int, limit: int = 100) -> list:
        """Recupera logs de uma empresa específica"""
        try:
            company_log_file = self.log_dir / f"company_{company_id}_notifications.log"
            
            if not company_log_file.exists():
                return []
            
            logs = []
            with open(company_log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
                # Pegar as últimas N linhas
                for line in lines[-limit:]:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
            
            return logs
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar logs da empresa {company_id}: {e}")
            return []
    
    def get_notification_stats(self, company_id: int, days: int = 7) -> Dict[str, Any]:
        """Estatísticas de notificações para uma empresa"""
        try:
            logs = self.get_company_logs(company_id, limit=1000)
            
            if not logs:
                return {
                    "total_notifications": 0,
                    "successful": 0,
                    "errors": 0,
                    "by_topic": {},
                    "by_event": {}
                }
            
            # Filtrar logs dos últimos N dias
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            recent_logs = [
                log for log in logs 
                if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff_date
            ]
            
            stats = {
                "total_notifications": len(recent_logs),
                "successful": len([log for log in recent_logs if log.get("success", False)]),
                "errors": len([log for log in recent_logs if not log.get("success", True)]),
                "by_topic": {},
                "by_event": {}
            }
            
            # Contar por tópico
            for log in recent_logs:
                topic = log.get("topic", "unknown")
                stats["by_topic"][topic] = stats["by_topic"].get(topic, 0) + 1
                
                event = log.get("event", "unknown")
                stats["by_event"][event] = stats["by_event"].get(event, 0) + 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular estatísticas: {e}")
            return {"error": str(e)}

# Instância global do logger
global_logger = GlobalLogger()

# Aliases para compatibilidade
notification_logger = global_logger
