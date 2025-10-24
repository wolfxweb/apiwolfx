"""
Exemplos de como usar o sistema global de logs
"""
from app.utils.notification_logger import global_logger

# Exemplo 1: Log de chamada de API
def exemplo_api_call():
    """Exemplo de log para chamada de API"""
    try:
        # Simular chamada de API
        global_logger.log_api_call(
            endpoint="/api/orders",
            method="GET",
            company_id=15,
            user_id=2,
            success=True,
            response_time=0.5
        )
    except Exception as e:
        global_logger.log_api_call(
            endpoint="/api/orders",
            method="GET",
            company_id=15,
            user_id=2,
            success=False,
            error_message=str(e)
        )

# Exemplo 2: Log de operação de banco de dados
def exemplo_database_operation():
    """Exemplo de log para operação de banco"""
    try:
        # Simular operação de banco
        global_logger.log_database_operation(
            operation="INSERT",
            table="ml_orders",
            record_id="12345",
            company_id=15,
            success=True
        )
    except Exception as e:
        global_logger.log_database_operation(
            operation="INSERT",
            table="ml_orders",
            record_id="12345",
            company_id=15,
            success=False,
            error_message=str(e)
        )

# Exemplo 3: Log de chamada a API externa
def exemplo_external_api():
    """Exemplo de log para API externa"""
    try:
        # Simular chamada ao Mercado Livre
        global_logger.log_external_api_call(
            service="MercadoLivre",
            endpoint="/orders/12345",
            company_id=15,
            success=True,
            response_code=200
        )
    except Exception as e:
        global_logger.log_external_api_call(
            service="MercadoLivre",
            endpoint="/orders/12345",
            company_id=15,
            success=False,
            error_message=str(e)
        )

# Exemplo 4: Log genérico
def exemplo_log_generico():
    """Exemplo de log genérico"""
    data = {
        "description": "Processamento de pedido",
        "order_id": "12345",
        "amount": 100.50
    }
    
    global_logger.log_event(
        event_type="order_processing",
        data=data,
        company_id=15,
        success=True
    )

# Exemplo 5: Log de erro
def exemplo_log_erro():
    """Exemplo de log de erro"""
    data = {
        "description": "Falha na sincronização",
        "sync_type": "orders",
        "last_sync": "2024-01-01T10:00:00Z"
    }
    
    global_logger.log_event(
        event_type="sync_error",
        data=data,
        company_id=15,
        success=False,
        error_message="Timeout na API do Mercado Livre"
    )
