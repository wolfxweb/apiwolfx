#!/usr/bin/env python3
"""
Script para criar o agente "Analise cadastro produto"
Execute este script para criar o agente "Analise cadastro produto"
"""
import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import SessionLocal
from app.models.saas_models import OpenAIAssistant, InteractionMode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(db):
    """Cria o agente 'Analise cadastro produto' se não existir"""
    try:
        # Verificar se já existe
        existing = db.query(OpenAIAssistant).filter(
            OpenAIAssistant.name == "Analise cadastro produto"
        ).first()
        
        if existing:
            logger.info("ℹ️ Agente 'Analise cadastro produto' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Instruções do agente
        instructions = """Você é um especialista em otimização de cadastros de produtos no Mercado Livre.

[SUA FUNÇÃO]
Analisar o cadastro completo de um produto e fornecer recomendações específicas para otimização, considerando:
- Título do anúncio (SEO, palavras-chave, limite de 60 caracteres)
- Descrição (completa, informativa, SEO)
- Preço e estratégia de precificação
- Categoria e atributos específicos da categoria
- Características do produto (atributos dinâmicos)
- Variações (se aplicável)
- Imagens e mídia
- Informações de envio e garantia
- Códigos (GTIN, SKU, MPN)

[ANÁLISE ESPECÍFICA POR CATEGORIA]
- Os campos e atributos variam conforme a categoria do produto
- Analise os atributos específicos da categoria recebida
- Identifique atributos obrigatórios que podem estar faltando
- Sugira valores apropriados para atributos baseado nas melhores práticas do ML
- Considere as características específicas da categoria (ex: eletrônicos têm atributos diferentes de roupas)

[FORMATO DE RESPOSTA]
Forneça uma análise estruturada com:
1. **Resumo Executivo**: Pontos principais a otimizar
2. **Título**: Sugestões de melhoria (se necessário)
3. **Descrição**: Recomendações de conteúdo e SEO
4. **Atributos**: 
   - Atributos faltantes que são importantes
   - Valores sugeridos para atributos existentes
   - Atributos que podem melhorar a visibilidade
5. **Precificação**: Análise do preço e sugestões
6. **Variações**: Se aplicável, otimizações nas variações
7. **Outros**: Envio, garantia, códigos, etc.

[REGRAS IMPORTANTES]
- Seja específico e acionável nas recomendações
- Considere as regras do Mercado Livre para cada categoria
- Mantenha o limite de 60 caracteres no título
- Priorize atributos obrigatórios e importantes para SEO
- Sugira melhorias práticas e implementáveis"""

        initial_prompt = """Analise o cadastro de produto do Mercado Livre abaixo e forneça recomendações específicas de otimização.

Considere:
- Título do anúncio (SEO, palavras-chave, limite de 60 caracteres)
- Descrição (completa, informativa, SEO)
- Preço e estratégia de precificação
- Categoria e atributos específicos da categoria
- Características do produto (atributos dinâmicos que variam por categoria)
- Variações (se aplicável)
- Informações de envio e garantia
- Códigos (GTIN, SKU, MPN)

Os dados completos do produto serão fornecidos abaixo."""

        welcome_message = "Olá! Vou analisar o cadastro do seu produto e fornecer recomendações específicas para otimização. Os dados do cadastro serão fornecidos abaixo."
        
        # Criar agente
        agent = OpenAIAssistant(
            name="Analise cadastro produto",
            description="Agente especializado em análise e otimização de cadastros de produtos do Mercado Livre",
            assistant_id=f"local_analise_cadastro_{uuid.uuid4().hex[:16]}",
            model="gpt-5-nano",
            instructions=instructions,
            temperature=None,
            max_tokens=16000,
            tools_config={"reasoning_effort": "low", "verbosity": "medium", "tools": []},
            interaction_mode=InteractionMode.CHAT,
            use_case="Análise de cadastro de produto",
            memory_enabled=True,
            initial_prompt=initial_prompt,
            welcome_enabled=True,
            welcome_use_model=False,
            welcome_message=welcome_message,
            provider="openai",
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"✅ Agente 'Analise cadastro produto' criado com sucesso (ID: {agent.id})")
        return {"success": True, "agent_id": agent.id}
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar agente: {e}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = run(db)
        if result.get("success"):
            print("✅ Agente criado com sucesso!")
            sys.exit(0)
        else:
            print(f"❌ Erro: {result.get('error')}")
            sys.exit(1)
    finally:
        db.close()

