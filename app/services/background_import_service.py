"""
Serviço para importação de pedidos em background
"""
import threading
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.services.ml_orders_service import MLOrdersService
from app.models.saas_models import MLAccount, MLAccountStatus
import time

logger = logging.getLogger(__name__)

# Armazenar status dos jobs em memória (simplificado)
# Em produção, deveria usar Redis ou banco de dados
active_jobs = {}

class BackgroundImportService:
    """Serviço para importar pedidos em background"""
    
    def __init__(self):
        self.jobs = active_jobs
    
    def start_import_job(self, company_id: int, ml_account_id: int, 
                        total_orders: int, db_url: str) -> str:
        """Inicia um job de importação em background"""
        try:
            # Gerar ID único para o job
            job_id = f"import_{company_id}_{int(datetime.now().timestamp())}"
            
            # Criar registro do job
            self.jobs[job_id] = {
                "id": job_id,
                "company_id": company_id,
                "ml_account_id": ml_account_id,
                "status": "running",
                "total_orders": total_orders,
                "processed": 0,
                "imported": 0,
                "updated": 0,
                "errors": 0,
                "current_batch": 0,
                "total_batches": (total_orders + 49) // 50,  # Arredondar para cima
                "started_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "error_message": None
            }
            
            # Iniciar thread de importação
            thread = threading.Thread(
                target=self._import_worker,
                args=(job_id, company_id, ml_account_id, db_url),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Job de importação iniciado: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Erro ao iniciar job de importação: {e}")
            raise e
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Retorna status de um job"""
        return self.jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancela um job em execução"""
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "cancelled"
            return True
        return False
    
    def _import_worker(self, job_id: str, company_id: int, ml_account_id: int, db_url: str):
        """Worker que executa a importação em background"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        try:
            # Criar nova sessão de banco (thread-safe)
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            # Criar serviço de orders
            orders_service = MLOrdersService(db)
            
            # Buscar conta ML
            account = db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["error_message"] = "Conta ML não encontrada"
                db.close()
                return
            
            # Obter token
            access_token = orders_service._get_active_token(ml_account_id)
            if not access_token:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["error_message"] = "Token não encontrado"
                db.close()
                return
            
            # Importar em lotes
            offset = 0
            batch_size = 50
            total_to_import = self.jobs[job_id]["total_orders"]
            current_batch = 1
            
            while offset < total_to_import and self.jobs[job_id]["status"] == "running":
                try:
                    logger.info(f"Job {job_id}: Processando lote {current_batch}")
                    
                    # Atualizar status
                    self.jobs[job_id]["current_batch"] = current_batch
                    self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
                    
                    # Buscar pedidos da API
                    import requests
                    headers = {"Authorization": f"Bearer {access_token}"}
                    url = "https://api.mercadolibre.com/orders/search"
                    params = {
                        "seller": account.ml_user_id,
                        "limit": batch_size,
                        "offset": offset,
                        "sort": "date_desc"
                    }
                    
                    response = requests.get(url, headers=headers, params=params, timeout=60)
                    
                    if response.status_code != 200:
                        logger.error(f"Erro ao buscar pedidos: {response.status_code}")
                        self.jobs[job_id]["errors"] += 1
                        offset += batch_size
                        current_batch += 1
                        continue
                    
                    data = response.json()
                    orders_data = data.get("results", [])
                    
                    # Processar cada pedido do lote
                    for idx, order_data in enumerate(orders_data):
                        if self.jobs[job_id]["status"] != "running":
                            break
                        
                        try:
                            # Pausa de 5 segundos entre pedidos (exceto o primeiro)
                            if idx > 0:
                                time.sleep(5)
                            
                            # Buscar dados completos
                            complete_data = orders_service._fetch_complete_order_data(order_data, access_token)
                            
                            # Salvar no banco
                            result = orders_service._save_order_to_database(complete_data, ml_account_id, company_id)
                            
                            if result["action"] == "created":
                                self.jobs[job_id]["imported"] += 1
                            elif result["action"] == "updated":
                                self.jobs[job_id]["updated"] += 1
                            
                            self.jobs[job_id]["processed"] += 1
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar pedido {order_data.get('id')}: {e}")
                            self.jobs[job_id]["errors"] += 1
                            continue
                    
                    # Commit do lote
                    db.commit()
                    
                    # Avançar offset
                    offset += batch_size
                    current_batch += 1
                    
                    # Pausa de 10 segundos entre lotes
                    if offset < total_to_import and self.jobs[job_id]["status"] == "running":
                        logger.info(f"Job {job_id}: Aguardando 10 segundos...")
                        time.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Erro no lote {current_batch}: {e}")
                    self.jobs[job_id]["errors"] += 1
                    offset += batch_size
                    current_batch += 1
                    continue
            
            # Finalizar job
            if self.jobs[job_id]["status"] == "running":
                self.jobs[job_id]["status"] = "completed"
                self.jobs[job_id]["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"Job {job_id} finalizado: {self.jobs[job_id]['imported']} importados, {self.jobs[job_id]['updated']} atualizados")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Erro fatal no worker do job {job_id}: {e}")
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["error_message"] = str(e)
                self.jobs[job_id]["updated_at"] = datetime.now().isoformat()

# Instância global do serviço
background_import_service = BackgroundImportService()

