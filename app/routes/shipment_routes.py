"""
Rotas para expedição e notas fiscais
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
import logging
import httpx
import zipfile
import requests
from io import BytesIO

from app.config.database import get_db
from app.controllers.shipment_controller import ShipmentController
from app.controllers.auth_controller import AuthController
from app.services.token_manager import TokenManager
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

# Tentar importar bibliotecas para conversão ZPL
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from PIL import Image
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("ReportLab não instalado. Conversão ZPL para PDF pode não funcionar corretamente.")

# Tentar importar Zebrafy para conversão ZPL local
try:
    from zebrafy import ZebrafyZPL
    HAS_ZEBRAFY = True
except ImportError:
    HAS_ZEBRAFY = False
    logger.info("Zebrafy não instalado. Usando API Labelary como alternativa.")

router = APIRouter(prefix="/shipments", tags=["Expedição"])

def _create_pdf_from_image(img: Image.Image, order_id: str) -> Optional[bytes]:
    """
    Converte uma imagem PIL para PDF no tamanho 10x15cm
    """
    try:
        if not HAS_REPORTLAB:
            return None
        
        # Tamanho da etiqueta: 10cm x 15cm
        TARGET_WIDTH_CM = 10
        TARGET_HEIGHT_CM = 15
        CM_TO_POINTS = 28.3465
        
        pdf_width = TARGET_WIDTH_CM * CM_TO_POINTS   # ~283.465 pontos (10cm)
        pdf_height = TARGET_HEIGHT_CM * CM_TO_POINTS  # ~425.197 pontos (15cm)
        
        logger.info(f"📏 Criando PDF de etiqueta: {TARGET_WIDTH_CM}cm x {TARGET_HEIGHT_CM}cm ({pdf_width:.2f} x {pdf_height:.2f} pontos)")
        
        # Criar PDF com tamanho exato da etiqueta
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))
        
        # Calcular escala para preencher toda a área mantendo proporção
        img_width, img_height = img.size
        scale_x = pdf_width / img_width
        scale_y = pdf_height / img_height
        scale = max(scale_x, scale_y)  # Usar maior escala para preencher
        
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        # Centralizar imagem
        x_offset = (pdf_width - scaled_width) / 2
        y_offset = (pdf_height - scaled_height) / 2
        
        logger.info(f"📐 Imagem: {img_width}x{img_height}px, Escala: {scale:.4f}, Tamanho final: {scaled_width:.2f}x{scaled_height:.2f} pontos")
        
        # Converter imagem PIL para arquivo temporário (ReportLab precisa de arquivo ou path)
        # Se a imagem não estiver em RGB, converter
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        import tempfile
        import os
        
        # Criar arquivo temporário para o ReportLab
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        tmp_path = tmp_file.name
        tmp_file.close()
        
        try:
            # Salvar imagem no arquivo temporário
            img.save(tmp_path, format='PNG')
            
            # Adicionar imagem ao PDF usando o caminho do arquivo
            c.drawImage(
                tmp_path,
                x_offset, 
                y_offset, 
                width=scaled_width, 
                height=scaled_height,
                preserveAspectRatio=True
            )
        finally:
            # Remover arquivo temporário
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass  # Ignorar erro ao remover arquivo temporário
        
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"❌ Erro ao criar PDF da imagem: {e}", exc_info=True)
        return None

async def convert_zpl_to_pdf(zpl_content: str, order_id: str) -> Optional[bytes]:
    """
    Converte conteúdo ZPL para PDF usando conversão local (Zebrafy) ou API Labelary
    """
    try:
        if not HAS_REPORTLAB:
            logger.error("ReportLab não está disponível. Instale com: pip install reportlab")
            return create_pdf_from_zpl_text(zpl_content, order_id)
        
        # Limpar e validar ZPL antes de processar
        zpl_clean = zpl_content.strip()
        
        # Verificar se ZPL está completo
        if not zpl_clean.startswith('^XA'):
            logger.warning("⚠️ ZPL não começa com ^XA, adicionando...")
            zpl_clean = '^XA\n' + zpl_clean
        
        if not zpl_clean.rstrip().endswith('^XZ'):
            logger.warning("⚠️ ZPL não termina com ^XZ, adicionando...")
            zpl_clean = zpl_clean.rstrip() + '\n^XZ'
        
        logger.info(f"🔄 Convertendo ZPL para PDF - Tamanho: {len(zpl_clean)} chars")
        
        # PRIORIDADE 1: Tentar conversão local com Zebrafy (sem API externa)
        if HAS_ZEBRAFY:
            try:
                logger.info("📦 Tentando conversão local com Zebrafy...")
                zpl_converter = ZebrafyZPL(zpl_clean)
                images = zpl_converter.to_images()
                
                if images and len(images) > 0:
                    img = images[0]
                    logger.info(f"✅ Zebrafy gerou imagem: {img.size[0]}x{img.size[1]}px, Modo: {img.mode}")
                    
                    # Converter imagem para PDF 10x15cm
                    return _create_pdf_from_image(img, order_id)
                else:
                    logger.warning("⚠️ Zebrafy não gerou imagens, tentando API Labelary...")
            except Exception as e:
                logger.warning(f"⚠️ Erro na conversão Zebrafy: {e}. Tentando API Labelary...")
        
        # PRIORIDADE 2: Usar API Labelary com requests (síncrono, mais estável que httpx)
        conversion_url = "http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/"
        logger.info("🌐 Tentando conversão via API Labelary...")
        
        # Usar requests (síncrono) que é mais estável para essa API
        response = requests.post(
            conversion_url,
            data=zpl_clean,  # Sem Content-Type - funciona melhor assim
            timeout=30
        )
        
        logger.info(f"📥 Labelary - Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}, Tamanho: {len(response.content)} bytes")
        
        if response.status_code == 200:
            # Verificar se é realmente uma imagem PNG
            if not response.content.startswith(b'\x89PNG'):
                logger.error(f"❌ Resposta Labelary não é PNG (primeiros bytes: {response.content[:10].hex()})")
                logger.error(f"❌ Resposta texto: {response.text[:500] if hasattr(response, 'text') else 'N/A'}")
                return create_pdf_from_zpl_text(zpl_content, order_id)
            
            # Carregar PNG
            try:
                img = Image.open(BytesIO(response.content))
                logger.info(f"✅ Imagem PNG carregada: {img.size[0]}x{img.size[1]}px, Modo: {img.mode}")
                return _create_pdf_from_image(img, order_id)
            except Exception as e:
                logger.error(f"❌ Erro ao abrir imagem PNG: {e}")
                return create_pdf_from_zpl_text(zpl_content, order_id)
        else:
            error_preview = response.text[:500] if response.text else response.content[:200]
            logger.error(f"❌ Erro na API Labelary (Status {response.status_code}): {error_preview}")
            return create_pdf_from_zpl_text(zpl_content, order_id)
    
    except Exception as e:
        logger.error(f"Erro ao converter ZPL para PDF: {e}", exc_info=True)
        # Fallback: criar PDF com o texto ZPL
        return create_pdf_from_zpl_text(zpl_content, order_id)

def create_pdf_from_zpl_text(zpl_content: str, order_id: str) -> Optional[bytes]:
    """
    Cria PDF básico com o conteúdo ZPL como texto (fallback)
    """
    try:
        if not HAS_REPORTLAB:
            logger.error("ReportLab não está disponível. Não é possível criar PDF.")
            return None
        
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Adicionar título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, 10*inch, f"Etiqueta de Envio - Pedido {order_id}")
        
        # Adicionar conteúdo ZPL
        c.setFont("Courier", 8)
        y_position = 9.5*inch
        
        # Quebrar ZPL em linhas e adicionar ao PDF
        lines = zpl_content.split('\n')
        for i, line in enumerate(lines[:80]):  # Limitar a 80 linhas
            if y_position < 0.5*inch:
                break
            c.drawString(0.5*inch, y_position, line[:100])  # Limitar largura da linha
            y_position -= 0.15*inch
        
        # Nota no rodapé
        c.setFont("Helvetica", 8)
        c.drawString(0.5*inch, 0.3*inch, "Nota: Este PDF contém o código ZPL original. Use o formato ZPL2 para impressora térmica.")
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Erro ao criar PDF do texto ZPL: {e}")
        return None

@router.get("/", response_class=HTMLResponse)
async def shipments_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de expedição de produtos"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    return render_template("shipments.html", user=user_data)

@router.get("/pending")
async def list_pending_shipments(
    request: Request,
    search: Optional[str] = Query(""),
    invoice_status: Optional[str] = Query(""),
    status: Optional[str] = Query(""),
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(100, ge=1, le=5000),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Lista pedidos para expedição com filtros e paginação"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.list_pending_shipments(
            company_id, 
            search=search, 
            invoice_status=invoice_status,
            status=status,
            page=page,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-invoices")
async def sync_invoice_status(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza status das notas fiscais com o Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_invoices(company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-single-invoice/{order_id}")
async def sync_single_order_invoice(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza nota fiscal de um pedido específico"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_single_order_invoice(order_id, company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/bulk-update")
async def bulk_update_orders(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza múltiplos pedidos em lote"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 [BULK UPDATE] Recebida requisição de atualização em lote")
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Obter dados da requisição
        body = await request.json()
        order_ids = body.get("order_ids", [])
        
        logger.info(f"📋 [BULK UPDATE] Recebidos {len(order_ids)} pedidos para atualizar: {order_ids}")
        
        if not order_ids:
            return JSONResponse(content={"error": "Nenhum pedido selecionado"}, status_code=400)
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        
        # Processar cada pedido
        results = []
        for order_id in order_ids:
            try:
                result = controller.sync_single_order_invoice(order_id, company_id, access_token)
                results.append(result)
                logger.info(f"✅ Result for order {order_id}: success={result.get('success')}, error={result.get('error')}, message={result.get('message')}")
            except Exception as e:
                logger.error(f"❌ Error processing order {order_id}: {e}")
                results.append({"success": False, "error": str(e)})
        
        # Contar sucessos e falhas
        success_count = sum(1 for r in results if r.get("success"))
        failure_count = len(results) - success_count
        
        logger.info(f"📊 Total: {len(results)}, Success: {success_count}, Failure: {failure_count}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Atualizados {success_count} pedidos com sucesso, {failure_count} falharam",
            "total": len(order_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        })
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-single-order/{order_id}")
async def sync_single_order(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza todos os dados de um pedido específico do Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        user_id = user_data["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user_id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_single_order_invoice(order_id, company_id, access_token)
        
        if result.get("success"):
            return JSONResponse(content={
                "success": True,
                "message": result.get("message", "Pedido atualizado com sucesso"),
                "data": result
            })
        else:
            return JSONResponse(content={
                "success": False,
                "error": result.get("error", "Erro ao atualizar pedido")
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Erro ao atualizar pedido {order_id}: {e}", exc_info=True)
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/download-invoice/{order_id}")
async def download_invoice(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Download da nota fiscal do pedido"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar pedido no banco
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            MLOrder.ml_order_id == order_id,
            MLOrder.company_id == company_id
        ).first()
        
        if not order:
            return JSONResponse(content={"error": "Pedido não encontrado"}, status_code=404)
        
        if not order.invoice_pdf_url:
            return JSONResponse(content={"error": "Nota fiscal não disponível"}, status_code=404)
        
        # Buscar token de acesso
        token_manager = TokenManager(db)
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Usuário não encontrado"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        if not access_token:
            return JSONResponse(content={"error": "Token inválido"}, status_code=401)
        
        # Baixar PDF da API do Mercado Livre
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(order.invoice_pdf_url, headers=headers, timeout=30.0)
            
            if response.status_code != 200:
                logger.error(f"Erro ao baixar PDF: {response.status_code}")
                return JSONResponse(content={"error": "Erro ao baixar nota fiscal"}, status_code=500)
            
            # Preparar nome do arquivo
            invoice_filename = f"NF-{order_id}"
            if order.invoice_number:
                invoice_filename = f"NF-{order.invoice_number}"
                if order.invoice_series:
                    invoice_filename = f"NF-{order.invoice_number}-{order.invoice_series}"
            
            invoice_filename += ".pdf"
            
            # Retornar arquivo como download
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{invoice_filename}"'
                }
            )
    
    except Exception as e:
        logger.error(f"Erro ao baixar nota fiscal: {e}")
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/download-label/{order_id}")
async def download_shipping_label(
        order_id: str,
        format: str = Query("pdf", description="Formato da etiqueta: 'pdf' ou 'zpl2'"),
        session_token: Optional[str] = Cookie(None),
        db: Session = Depends(get_db)
    ):
    """Download da etiqueta de envio do pedido (para ponto de coleta)"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar pedido no banco
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            MLOrder.ml_order_id == order_id,
            MLOrder.company_id == company_id
        ).first()
        
        if not order:
            return JSONResponse(content={"error": "Pedido não encontrado"}, status_code=404)
        
        if not order.shipping_id:
            return JSONResponse(content={"error": "Etiqueta de envio não disponível (sem shipping_id)"}, status_code=404)
        
        # Verificar detalhes do envio
        import json
        shipping_details = None
        if order.shipping_details:
            if isinstance(order.shipping_details, str):
                try:
                    shipping_details = json.loads(order.shipping_details)
                except:
                    shipping_details = {}
            else:
                shipping_details = order.shipping_details
        
        logistic_type = shipping_details.get('logistic_type') if shipping_details else order.shipping_type
        
        # Tipos de logística que suportam etiquetas (segundo documentação ML)
        supported_logistic_types = ['drop_off', 'xd_drop_off', 'cross_docking', 'self_service']
        is_supported = (
            logistic_type in supported_logistic_types or
            order.shipping_type in supported_logistic_types
        )
        
        # Não bloquear tentativa, mas logar aviso se não for tipo suportado
        if not is_supported:
            logger.warning(f"⚠️ Tipo de logística '{logistic_type}' pode não suportar etiquetas, mas tentando mesmo assim...")
        
        # Buscar token de acesso
        token_manager = TokenManager(db)
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Usuário não encontrado"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        if not access_token:
            return JSONResponse(content={"error": "Token inválido"}, status_code=401)
        
        # Buscar etiqueta na API do Mercado Livre
        # Endpoint correto: GET /shipment_labels?shipment_ids={shipping_id}&response_type=pdf
        shipping_id = str(order.shipping_id)
        
        # Verificar status do envio antes de tentar baixar
        # A etiqueta só está disponível se status = "ready_to_ship" e substatus = "ready_to_print"
        shipment_status = shipping_details.get('status') if shipping_details else None
        shipment_substatus = shipping_details.get('substatus') if shipping_details else None
        
        logger.info(f"📦 Verificando etiqueta para shipping_id {shipping_id}: status={shipment_status}, substatus={shipment_substatus}")
        
        # Validar formato solicitado
        format_lower = format.lower()
        if format_lower not in ['pdf', 'zpl2', 'zpl2pdf']:
            return JSONResponse(content={
                "error": "Formato inválido. Use 'pdf', 'zpl2' ou 'zpl2pdf'"
            }, status_code=400)
        
        # Tentar baixar a etiqueta usando o endpoint correto
        label_url = f"https://api.mercadolibre.com/shipment_labels"
        
        # Se for zpl2pdf, primeiro baixar ZPL e depois converter
        if format_lower == 'zpl2pdf':
            # Baixar ZPL primeiro
            params_zpl = {
                "shipment_ids": shipping_id,
                "response_type": "zpl2"
            }
            headers_zpl = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "*/*"  # Aceitar qualquer formato da API
            }
            
            async with httpx.AsyncClient() as zpl_client:
                zpl_response = await zpl_client.get(label_url, headers=headers_zpl, params=params_zpl, timeout=30.0)
                
                if zpl_response.status_code == 200:
                    # Garantir encoding correto do ZPL - manter como bytes primeiro
                    raw_content = zpl_response.content
                    
                    if not raw_content or len(raw_content) == 0:
                        logger.error("Conteúdo vazio recebido para conversão!")
                        return JSONResponse(content={"error": "Conteúdo vazio recebido da API"}, status_code=500)
                    
                    # Verificar se é um arquivo ZIP (começa com PK)
                    zpl_content_bytes = None
                    if raw_content.startswith(b'PK'):
                        logger.info("📦 Conteúdo para conversão é um arquivo ZIP - extraindo ZPL...")
                        try:
                            with zipfile.ZipFile(io.BytesIO(raw_content), 'r') as zip_file:
                                # Listar arquivos no ZIP
                                file_list = zip_file.namelist()
                                logger.info(f"📦 Arquivos no ZIP: {file_list}")
                                
                                # Procurar arquivo ZPL (geralmente .txt ou .zpl)
                                zpl_file = None
                                for filename in file_list:
                                    if filename.lower().endswith(('.txt', '.zpl')) or 'etiqueta' in filename.lower():
                                        zpl_file = filename
                                        break
                                
                                if zpl_file:
                                    logger.info(f"📄 Extraindo arquivo ZPL: {zpl_file}")
                                    zpl_content_bytes = zip_file.read(zpl_file)
                                else:
                                    # Se não encontrar por extensão, pegar o primeiro arquivo de texto
                                    for filename in file_list:
                                        if not filename.lower().endswith('.pdf'):
                                            zpl_file = filename
                                            zpl_content_bytes = zip_file.read(zpl_file)
                                            logger.info(f"📄 Usando arquivo: {zpl_file}")
                                            break
                                
                                if not zpl_content_bytes:
                                    logger.error("Não foi possível encontrar arquivo ZPL no ZIP para conversão")
                                    return JSONResponse(content={"error": "Arquivo ZPL não encontrado no ZIP recebido"}, status_code=500)
                        except zipfile.BadZipFile:
                            logger.warning("Conteúdo não é um ZIP válido, tratando como ZPL direto")
                            zpl_content_bytes = raw_content
                        except Exception as e:
                            logger.error(f"Erro ao extrair ZIP para conversão: {e}", exc_info=True)
                            return JSONResponse(content={"error": f"Erro ao extrair arquivo ZIP: {str(e)}"}, status_code=500)
                    else:
                        # Não é ZIP, tratar como ZPL direto
                        zpl_content_bytes = raw_content
                        logger.info("📄 Conteúdo para conversão é ZPL direto")
                    
                    # Remover BOM se existir
                    if zpl_content_bytes.startswith(b'\xef\xbb\xbf'):
                        zpl_content_bytes = zpl_content_bytes[3:]
                    
                    # Decodificar para string (para a função de conversão)
                    # Tentar UTF-8 primeiro, depois latin-1 (mais comum em ZPL)
                    try:
                        zpl_content = zpl_content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            zpl_content = zpl_content_bytes.decode('latin-1')
                            logger.info("ZPL decodificado como latin-1")
                        except:
                            # Último recurso: usar errors='replace' para substituir caracteres inválidos
                            zpl_content = zpl_content_bytes.decode('latin-1', errors='replace')
                            logger.warning("ZPL decodificado com substituição de caracteres inválidos")
                    
                    # Validar que o ZPL está completo (deve começar com ^XA e terminar com ^XZ)
                    zpl_preview = zpl_content[:500] if len(zpl_content) > 500 else zpl_content
                    zpl_ends = zpl_content[-100:] if len(zpl_content) > 100 else zpl_content
                    
                    if not zpl_content.strip().startswith('^XA'):
                        logger.warning(f"⚠️ ZPL pode estar incompleto - não começa com ^XA. Preview: {zpl_preview[:200]}")
                    if not zpl_content.strip().endswith('^XZ'):
                        logger.warning(f"⚠️ ZPL pode estar incompleto - não termina com ^XZ. Final: {zpl_ends[-100:]}")
                    
                    logger.info(f"📄 ZPL para conversão - Tamanho: {len(zpl_content_bytes)} bytes, String: {len(zpl_content)} chars")
                    logger.info(f"📄 ZPL começa com: {zpl_content[:50]}")
                    logger.info(f"📄 ZPL termina com: {zpl_content[-50:]}")
                    
                    # Converter ZPL para PDF
                    pdf_bytes = await convert_zpl_to_pdf(zpl_content, order_id)
                    
                    if not pdf_bytes:
                        logger.error("❌ Falha na conversão ZPL→PDF - retornando None")
                    
                    if pdf_bytes:
                        label_filename = f"Etiqueta-{order_id}.pdf"
                        return StreamingResponse(
                            io.BytesIO(pdf_bytes),
                            media_type="application/pdf",
                            headers={
                                "Content-Disposition": f'attachment; filename="{label_filename}"'
                            }
                        )
                    else:
                        return JSONResponse(content={
                            "error": "Erro ao converter ZPL para PDF"
                        }, status_code=500)
                else:
                    error_msg = "Erro ao baixar ZPL"
                    try:
                        error_data = zpl_response.json()
                        error_msg = error_data.get("message", error_data.get("error", error_msg))
                    except:
                        error_msg = zpl_response.text[:200] if zpl_response.text else error_msg
                    
                    return JSONResponse(content={
                        "error": error_msg,
                        "status_code": zpl_response.status_code
                    }, status_code=zpl_response.status_code)
        
        # Para PDF e ZPL2 direto
        params = {
            "shipment_ids": shipping_id,
            "response_type": format_lower if format_lower != 'zpl2pdf' else 'zpl2'
        }
        
        # Ajustar headers conforme formato
        if format_lower == 'pdf':
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/pdf"
            }
            media_type = "application/pdf"
            file_extension = "pdf"
        else:  # zpl2
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "*/*"  # Aceitar qualquer formato da API
            }
            media_type = "application/zpl"
            file_extension = "zpl"
        
        # Se não tiver status no banco, tentar buscar da API antes de baixar etiqueta
        if not shipment_status:
            try:
                shipment_url = f"https://api.mercadolibre.com/shipments/{shipping_id}"
                headers_api = {"Authorization": f"Bearer {access_token}"}
                async with httpx.AsyncClient() as check_client:
                    shipment_response = await check_client.get(shipment_url, headers=headers_api, timeout=10.0)
                    if shipment_response.status_code == 200:
                        shipment_data = shipment_response.json()
                        shipment_status = shipment_data.get('status')
                        shipment_substatus = shipment_data.get('substatus')
                        logger.info(f"📦 Status obtido da API: status={shipment_status}, substatus={shipment_substatus}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível verificar status do shipment na API: {e}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                label_url, 
                headers=headers, 
                params=params, 
                timeout=30.0,
                follow_redirects=True
            )
            
            # Para debug: logar resposta
            logger.info(f"📦 Resposta da API ML - Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}, Tamanho: {len(response.content)} bytes")

            # Fallback: shipments/{id}/documents/labels para status drop_off/dropped_off
            if response.status_code == 400:
                fallback_error = response.text
                try:
                    fallback_json = response.json()
                    fallback_error = fallback_json.get('message') or fallback_json.get('error') or fallback_error
                except Exception:
                    pass

                status_combined = (shipment_status or '') + ' ' + (fallback_error or '')
                if 'dropped_off' in status_combined.lower():
                    logger.info("🔄 Tentando fallback em /shipments/{id}/documents/labels para status dropped_off")
                    documents_url = f"https://api.mercadolibre.com/shipments/{shipping_id}/documents/labels"
                    documents_headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/pdf" if format_lower != 'zpl2' else "*/*"
                    }
                    documents_params = {}

                    response = await client.get(
                        documents_url,
                        headers=documents_headers,
                        params=documents_params,
                        timeout=30.0,
                        follow_redirects=True
                    )
                    logger.info(f"📦 Fallback documents/labels - Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}, Tamanho: {len(response.content)} bytes")

                    if response.status_code != 200:
                        logger.error("❌ Fallback documents/labels também falhou")
                        error_msg = fallback_error or "Etiqueta indisponível para status dropped_off"
                        return JSONResponse(content={
                            "error": error_msg,
                            "status_code": response.status_code
                        }, status_code=response.status_code)

                    # Caso resposta seja um ZIP, extrair PDF
                    content_type = response.headers.get("content-type", "")
                    if response.content.startswith(b'PK'):
                        try:
                            with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_file:
                                pdf_bytes = None
                                for name in zip_file.namelist():
                                    if name.lower().endswith('.pdf'):
                                        pdf_bytes = zip_file.read(name)
                                        break
                                if not pdf_bytes:
                                    logger.error("❌ ZIP de documentos não contém PDF")
                                    return JSONResponse(content={
                                        "error": "Documento PDF não encontrado no ZIP retornado"
                                    }, status_code=500)

                                if format_lower == 'zpl2':
                                    return JSONResponse(content={
                                        "error": "Formato ZPL não disponível para este status"
                                    }, status_code=400)

                                label_filename = f"Etiqueta-{order_id}.pdf"
                                return StreamingResponse(
                                    io.BytesIO(pdf_bytes),
                                    media_type="application/pdf",
                                    headers={
                                        "Content-Disposition": f'attachment; filename="{label_filename}"'
                                    }
                                )
                        except zipfile.BadZipFile:
                            logger.warning("Conteúdo de fallback não é ZIP, tratando como PDF")

                    if format_lower == 'zpl2':
                        return JSONResponse(content={
                            "error": "Formato ZPL não disponível para este status"
                        }, status_code=400)

                    label_filename = f"Etiqueta-{order_id}.pdf"
                    return StreamingResponse(
                        io.BytesIO(response.content),
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": f'attachment; filename="{label_filename}"'
                        }
                    )

            if response.status_code == 200:
                # Verificar tipo de conteúdo baseado no formato
                content_type = response.headers.get("content-type", "")
                is_valid_response = False
                
                if format_lower == 'pdf':
                    is_valid_response = "application/pdf" in content_type or "pdf" in content_type.lower()
                else:  # zpl2
                    is_valid_response = "text/plain" in content_type or "zpl" in content_type.lower() or len(response.content) > 0
                
                if is_valid_response:
                    # Preparar nome do arquivo
                    label_filename = f"Etiqueta-{order_id}.{file_extension}"
                    
                    # Para ZPL, garantir encoding correto
                    if format_lower == 'zpl2':
                        # Obter conteúdo como bytes (httpx já retorna como bytes em response.content)
                        raw_content = response.content
                        
                        # Verificar se está vazio
                        if not raw_content or len(raw_content) == 0:
                            logger.error("Conteúdo recebido está vazio!")
                            return JSONResponse(content={"error": "Conteúdo vazio recebido da API"}, status_code=500)
                        
                        # Verificar se é um arquivo ZIP (começa com PK)
                        zpl_content = None
                        if raw_content.startswith(b'PK'):
                            logger.info("📦 Conteúdo recebido é um arquivo ZIP - extraindo ZPL...")
                            try:
                                with zipfile.ZipFile(io.BytesIO(raw_content), 'r') as zip_file:
                                    # Listar arquivos no ZIP
                                    file_list = zip_file.namelist()
                                    logger.info(f"📦 Arquivos no ZIP: {file_list}")
                                    
                                    # Procurar arquivo ZPL (geralmente .txt ou .zpl)
                                    zpl_file = None
                                    for filename in file_list:
                                        if filename.lower().endswith(('.txt', '.zpl')) or 'etiqueta' in filename.lower():
                                            zpl_file = filename
                                            break
                                    
                                    if zpl_file:
                                        logger.info(f"📄 Extraindo arquivo ZPL: {zpl_file}")
                                        zpl_content = zip_file.read(zpl_file)
                                    else:
                                        # Se não encontrar por extensão, pegar o primeiro arquivo de texto
                                        for filename in file_list:
                                            if not filename.lower().endswith('.pdf'):
                                                zpl_file = filename
                                                zpl_content = zip_file.read(zpl_file)
                                                logger.info(f"📄 Usando arquivo: {zpl_file}")
                                                break
                                    
                                    if not zpl_content:
                                        logger.error("Não foi possível encontrar arquivo ZPL no ZIP")
                                        return JSONResponse(content={"error": "Arquivo ZPL não encontrado no ZIP recebido"}, status_code=500)
                            except zipfile.BadZipFile:
                                logger.warning("Conteúdo não é um ZIP válido, tratando como ZPL direto")
                                zpl_content = raw_content
                            except Exception as e:
                                logger.error(f"Erro ao extrair ZIP: {e}", exc_info=True)
                                return JSONResponse(content={"error": f"Erro ao extrair arquivo ZIP: {str(e)}"}, status_code=500)
                        else:
                            # Não é ZIP, tratar como ZPL direto
                            zpl_content = raw_content
                            logger.info("📄 Conteúdo recebido é ZPL direto")
                        
                        # Verificar se há BOM (Byte Order Mark) UTF-8 e remover se existir
                        if zpl_content.startswith(b'\xef\xbb\xbf'):
                            zpl_content = zpl_content[3:]
                            logger.info("Removido BOM UTF-8 do ZPL")
                        
                        # Log para debug (primeiros 100 bytes em hex e texto)
                        try:
                            preview = zpl_content[:200].decode('latin-1', errors='replace')
                            logger.info(f"📄 ZPL final - Tamanho: {len(zpl_content)} bytes")
                            logger.info(f"📄 Preview (primeiros 200 chars): {preview[:200]}")
                        except Exception as e:
                            logger.warning(f"Erro ao fazer preview do ZPL: {e}")
                        
                        # Retornar arquivo como download - conteúdo exato do ZPL
                        return StreamingResponse(
                            io.BytesIO(zpl_content),
                            media_type="application/zpl",
                            headers={
                                "Content-Disposition": f'attachment; filename="{label_filename}"',
                                "Content-Type": "application/zpl",
                                "Content-Length": str(len(zpl_content))
                            }
                        )
                    else:
                        # Para PDF, retornar normalmente
                        return StreamingResponse(
                            io.BytesIO(response.content),
                            media_type=media_type,
                            headers={
                                "Content-Disposition": f'attachment; filename="{label_filename}"'
                            }
                        )
                else:
                    # Resposta pode ser JSON com erro
                    try:
                        error_data = response.json()
                        logger.error(f"Erro na API: {error_data}")
                        error_msg = error_data.get("message", "Etiqueta não disponível")
                        return JSONResponse(content={"error": error_msg}, status_code=404)
                    except:
                        # Se não for JSON, pode ser que seja o conteúdo esperado mesmo sem content-type correto
                        # Tentar retornar como está
                        label_filename = f"Etiqueta-{order_id}.{file_extension}"
                        return StreamingResponse(
                            io.BytesIO(response.content),
                            media_type=media_type,
                            headers={
                                "Content-Disposition": f'attachment; filename="{label_filename}"'
                            }
                        )
            elif response.status_code == 404:
                logger.warning(f"Etiqueta não encontrada para shipping_id {shipping_id}")
                return JSONResponse(content={"error": "Etiqueta de envio não disponível no Mercado Livre"}, status_code=404)
            else:
                # Tentar obter mensagem de erro da resposta
                error_msg = "Erro ao baixar etiqueta"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", error_msg))
                    logger.error(f"Erro ao baixar etiqueta: {response.status_code} - {error_msg}")
                except:
                    logger.error(f"Erro ao baixar etiqueta: {response.status_code} - {response.text[:200]}")
                
                return JSONResponse(content={
                    "error": error_msg,
                    "status_code": response.status_code,
                    "hint": "Verifique se o envio está com status 'ready_to_ship' e substatus 'ready_to_print'"
                }, status_code=response.status_code)
    
    except Exception as e:
        logger.error(f"Erro ao baixar etiqueta de envio: {e}", exc_info=True)
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/stats")
async def get_stats(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas dos pedidos"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.get_stats(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/tab-counts")
async def get_tab_counts(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna contadores de pedidos por status para as abas"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.get_tab_counts(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-recent")
async def sync_recent_orders(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza pedidos dos últimos 2 dias com o Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        user_id = user_data["id"]  # ID do usuário logado
        
        logger.info(f"🔄 ========== SYNC-RECENT: SINCRONIZAR PEDIDOS ==========")
        logger.info(f"🔄 Usuário logado: {user_data.get('name', 'N/A')} (ID: {user_id})")
        logger.info(f"🔄 Company ID: {company_id}")
        logger.info(f"🔄 Company Name: {user_data['company'].get('name', 'N/A')}")
        logger.info(f"🔄 Vai sincronizar TODAS as contas ML do company_id {company_id}")
        
        # Usar MLOrdersController como as outras rotas (/sync-invoices, /sync-single-invoice)
        from app.controllers.ml_orders_controller import MLOrdersController
        
        controller = MLOrdersController(db)
        result = controller.sync_orders(
            company_id=company_id,
            ml_account_id=None,  # Sincronizar todas as contas da empresa
            is_full_import=False,
            days_back=2,  # Últimos 2 dias
            user_id=user_id  # Passar user_id para usar TokenManager
        )
        
        # Sincronizar status de envio e notas fiscais para os pedidos sincronizados
        from app.services.shipment_service import ShipmentService
        shipment_service = ShipmentService(db)
        shipment_result = shipment_service.sync_shipment_status_and_invoices(company_id, user_id=user_id)
        logger.info(f"🔄 Resultado sincronização de envios/NF: {shipment_result}")
        
        if shipment_result.get("invoice_updated"):
            result["invoice_updated"] = shipment_result["invoice_updated"]
        
        logger.info(f"🔄 Resultado da sincronização: {result.get('success', False)}")
        if result.get('success'):
            logger.info(f"✅ {result.get('total_saved', 0)} novos, {result.get('total_updated', 0)} atualizados")
        else:
            logger.error(f"❌ Erro: {result.get('error', 'Desconhecido')}")
        
        # Se houver erro relacionado a token, retornar 401 (igual às outras rotas)
        if not result.get("success"):
            error_msg = result.get("error", "").lower()
            if "token" in error_msg or "não encontrado" in error_msg or "expirado" in error_msg:
                return JSONResponse(content={
                    "error": "Token de acesso do Mercado Livre inválido ou expirado. Por favor, reconecte sua conta ML em 'Contas ML'."
                }, status_code=401)
        
        return JSONResponse(content={
            **result,
            "shipment_sync": shipment_result
        })
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar pedidos recentes: {e}", exc_info=True)
        db.rollback()
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

