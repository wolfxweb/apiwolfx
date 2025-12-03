"""
Serviço para gerenciar Briefings de Marketing
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.content_models import ContentBriefing
from app.services.agent_executor_service import AgentExecutorService
from app.models.saas_models import OpenAIAssistant

logger = logging.getLogger(__name__)


class BriefingService:
    """Serviço para gerenciar Briefings de Marketing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.executor = AgentExecutorService(db)
    
    def create_briefing(self, company_id: Optional[int], user_id: int, briefing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo briefing (company_id pode ser None para superadmin)"""
        try:
            briefing = ContentBriefing(
                company_id=company_id,  # Pode ser None para superadmin
                user_id=user_id,
                nome_empresa_produto=briefing_data.get("nome_empresa_produto"),
                publico_alvo=briefing_data.get("publico_alvo"),
                objetivo_conteudo=briefing_data.get("objetivo_conteudo"),
                estagio_funil=briefing_data.get("estagio_funil"),
                linha_editorial=briefing_data.get("linha_editorial"),
                redes_sociais=briefing_data.get("redes_sociais"),
                blog_config=briefing_data.get("blog_config"),
                material_complementar=briefing_data.get("material_complementar"),
                status="draft"
            )
            
            self.db.add(briefing)
            self.db.commit()
            self.db.refresh(briefing)
            
            return {
                "success": True,
                "data": briefing.to_dict()
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar briefing: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_briefing(self, briefing_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém um briefing específico (company_id pode ser None para superadmin)"""
        try:
            query = self.db.query(ContentBriefing).filter(ContentBriefing.id == briefing_id)
            if company_id is not None:
                query = query.filter(ContentBriefing.company_id == company_id)
            briefing = query.first()
            
            if not briefing:
                return {"success": False, "error": "Briefing não encontrado"}
            
            return {
                "success": True,
                "data": briefing.to_dict()
            }
        except Exception as e:
            logger.error(f"Erro ao obter briefing: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_briefings(self, company_id: Optional[int] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Lista briefings (company_id pode ser None para superadmin listar todos)"""
        try:
            query = self.db.query(ContentBriefing)
            if company_id is not None:
                query = query.filter(ContentBriefing.company_id == company_id)
            
            if status:
                query = query.filter(ContentBriefing.status == status)
            
            briefings = query.order_by(desc(ContentBriefing.created_at)).all()
            
            return {
                "success": True,
                "data": [briefing.to_dict() for briefing in briefings]
            }
        except Exception as e:
            logger.error(f"Erro ao listar briefings: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def execute_research(self, briefing_id: int, company_id: int, user: dict) -> Dict[str, Any]:
        """Executa pesquisa Perplexity para o briefing"""
        try:
            briefing = self.db.query(ContentBriefing).filter(
                ContentBriefing.id == briefing_id,
                ContentBriefing.company_id == company_id
            ).first()
            
            if not briefing:
                return {"success": False, "error": "Briefing não encontrado"}
            
            # Atualizar status
            briefing.status = "researching"
            self.db.commit()
            
            # Buscar agente Perplexity de pesquisa
            research_agent = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.name == "Pesquisa de Conteúdo",
                OpenAIAssistant.is_active == True
            ).first()
            
            if not research_agent:
                briefing.status = "error"
                self.db.commit()
                return {"success": False, "error": "Agente de pesquisa não encontrado"}
            
            # Construir prompt de pesquisa
            prompt = self._build_research_prompt(briefing)
            
            # Executar pesquisa
            result = self.executor.execute(
                agent_id=research_agent.id,
                user=user,
                message=prompt,
                context_data={
                    "briefing": briefing.to_dict()
                }
            )
            
            if result.get("success"):
                briefing.pesquisa_resultado = result.get("content", "")
                briefing.status = "draft"  # Voltar para draft após pesquisa
                self.db.commit()
                
                return {
                    "success": True,
                    "data": {
                        "briefing_id": briefing_id,
                        "pesquisa_resultado": briefing.pesquisa_resultado
                    }
                }
            else:
                briefing.status = "error"
                self.db.commit()
                return {
                    "success": False,
                    "error": result.get("error", "Erro ao executar pesquisa")
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao executar pesquisa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def identify_agents(self, briefing_id: int, company_id: Optional[int], user: dict) -> Dict[str, Any]:
        """Usa agente orquestrador para identificar agentes necessários (company_id pode ser None para superadmin)"""
        try:
            query = self.db.query(ContentBriefing).filter(ContentBriefing.id == briefing_id)
            if company_id is not None:
                query = query.filter(ContentBriefing.company_id == company_id)
            briefing = query.first()
            
            if not briefing:
                return {"success": False, "error": "Briefing não encontrado"}
            
            # Buscar agente orquestrador
            orchestrator = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.name == "Orquestrador de Briefing",
                OpenAIAssistant.is_active == True
            ).first()
            
            if not orchestrator:
                return {"success": False, "error": "Agente orquestrador não encontrado"}
            
            # Construir prompt para orquestrador
            prompt = self._build_orchestrator_prompt(briefing)
            
            # Executar orquestrador
            result = self.executor.execute(
                agent_id=orchestrator.id,
                user=user,
                message=prompt,
                context_data={
                    "briefing": briefing.to_dict(),
                    "pesquisa": briefing.pesquisa_resultado
                }
            )
            
            if result.get("success"):
                # Parsear resposta do orquestrador para extrair lista de agentes
                agents_list = self._parse_agents_list(result.get("content", ""))
                
                briefing.agentes_identificados = agents_list
                self.db.commit()
                
                return {
                    "success": True,
                    "data": {
                        "briefing_id": briefing_id,
                        "agentes_identificados": agents_list
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Erro ao identificar agentes")
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao identificar agentes: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def execute_agents_chain(self, briefing_id: int, company_id: Optional[int], user: dict) -> Dict[str, Any]:
        """Executa agentes encadeadamente (company_id pode ser None para superadmin)"""
        try:
            query = self.db.query(ContentBriefing).filter(ContentBriefing.id == briefing_id)
            if company_id is not None:
                query = query.filter(ContentBriefing.company_id == company_id)
            briefing = query.first()
            
            if not briefing:
                return {"success": False, "error": "Briefing não encontrado"}
            
            if not briefing.agentes_identificados:
                return {"success": False, "error": "Nenhum agente identificado. Execute a identificação primeiro."}
            
            # Atualizar status
            briefing.status = "generating"
            self.db.commit()
            
            # Lista de agentes a executar
            agents_list = briefing.agentes_identificados if isinstance(briefing.agentes_identificados, list) else []
            
            # Resultados acumulados
            generated_content = {}
            previous_results = {}
            
            # Mapeamento de nomes de agentes (para compatibilidade)
            agent_name_mapping = {
                "Geração de Texto": "Criação de Texto",
                "Geração de Imagens": "Geração de Imagem"
            }
            
            # Executar cada agente na ordem
            for agent_name in agents_list:
                try:
                    # Aplicar mapeamento se necessário
                    search_name = agent_name_mapping.get(agent_name, agent_name)
                    
                    # Buscar agente pelo nome
                    agent = self.db.query(OpenAIAssistant).filter(
                        OpenAIAssistant.name == search_name,
                        OpenAIAssistant.is_active == True
                    ).first()
                    
                    if not agent:
                        logger.warning(f"Agente '{agent_name}' (procurado como '{search_name}') não encontrado, pulando...")
                        continue
                    
                    # Construir prompt com contexto
                    prompt = self._build_agent_prompt(briefing, agent_name, previous_results)
                    
                    # Executar agente
                    result = self.executor.execute(
                        agent_id=agent.id,
                        user=user,
                        message=prompt,
                        context_data={
                            "briefing": briefing.to_dict(),
                            "pesquisa": briefing.pesquisa_resultado,
                            "previous_results": previous_results
                        }
                    )
                    
                    if result.get("success"):
                        # Salvar resultado
                        content_key = self._get_content_key_for_agent(agent_name)
                        generated_content[content_key] = result.get("content", "")
                        previous_results[agent_name] = result.get("content", "")
                    else:
                        logger.error(f"Erro ao executar agente {agent_name}: {result.get('error')}")
                        generated_content[content_key] = f"Erro: {result.get('error')}"
                        
                except Exception as e:
                    logger.error(f"Erro ao executar agente {agent_name}: {e}", exc_info=True)
                    continue
            
            # Salvar conteúdo gerado
            briefing.conteudo_gerado = generated_content
            briefing.status = "completed"
            self.db.commit()
            
            return {
                "success": True,
                "data": {
                    "briefing_id": briefing_id,
                    "conteudo_gerado": generated_content
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao executar cadeia de agentes: {e}", exc_info=True)
            briefing.status = "error"
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def _build_research_prompt(self, briefing: ContentBriefing) -> str:
        """Constrói prompt para pesquisa Perplexity"""
        prompt_parts = []
        
        if briefing.nome_empresa_produto:
            prompt_parts.append(f"Empresa/Produto: {briefing.nome_empresa_produto}")
        
        if briefing.publico_alvo:
            prompt_parts.append(f"Público-alvo: {briefing.publico_alvo}")
        
        if briefing.objetivo_conteudo:
            objetivos = briefing.objetivo_conteudo if isinstance(briefing.objetivo_conteudo, list) else []
            if objetivos:
                prompt_parts.append(f"Objetivos: {', '.join(objetivos)}")
        
        if briefing.estagio_funil:
            prompt_parts.append(f"Estágio do funil: {briefing.estagio_funil}")
        
        if briefing.linha_editorial:
            prompt_parts.append(f"Linha editorial: {briefing.linha_editorial}")
        
        base_prompt = "Pesquise informações atualizadas sobre: " + " | ".join(prompt_parts)
        base_prompt += "\n\nForneça insights sobre tendências, melhores práticas, dados relevantes e oportunidades de conteúdo para este briefing de marketing."
        
        return base_prompt
    
    def _build_orchestrator_prompt(self, briefing: ContentBriefing) -> str:
        """Constrói prompt para agente orquestrador"""
        prompt = f"""
Analise o seguinte briefing de marketing e identifique quais agentes especializados devem ser executados para gerar o conteúdo completo.

BRIEFING:
- Empresa/Produto: {briefing.nome_empresa_produto or 'Não informado'}
- Público-alvo: {briefing.publico_alvo or 'Não informado'}
- Objetivos: {briefing.objetivo_conteudo or 'Não informado'}
- Estágio do funil: {briefing.estagio_funil or 'Não informado'}
- Linha editorial: {briefing.linha_editorial or 'Não informado'}
- Redes sociais: {briefing.redes_sociais or 'Não informado'}
- Blog config: {briefing.blog_config or 'Não informado'}
- Material complementar: {briefing.material_complementar or 'Não informado'}

PESQUISA REALIZADA:
{briefing.pesquisa_resultado or 'Nenhuma pesquisa realizada ainda'}

AGENTES DISPONÍVEIS:
- Pesquisa de Conteúdo (já executado)
- Geração de Texto
- Otimização SEO
- Copy para Redes Sociais
- Geração de Imagens
- Scripts de Vídeo
- Email Marketing
- Copy para Anúncios

Retorne APENAS uma lista JSON com os nomes dos agentes que devem ser executados, na ordem correta.
Exemplo: ["Geração de Texto", "Otimização SEO", "Copy para Redes Sociais"]
"""
        return prompt
    
    def _build_agent_prompt(self, briefing: ContentBriefing, agent_name: str, previous_results: Dict[str, str]) -> str:
        """Constrói prompt específico para cada agente"""
        prompt_parts = [f"BRIEFING DE MARKETING - Agente: {agent_name}"]
        prompt_parts.append(f"\nEmpresa/Produto: {briefing.nome_empresa_produto or 'Não informado'}")
        prompt_parts.append(f"Público-alvo: {briefing.publico_alvo or 'Não informado'}")
        
        if briefing.pesquisa_resultado:
            prompt_parts.append(f"\nPESQUISA REALIZADA:\n{briefing.pesquisa_resultado}")
        
        if previous_results:
            prompt_parts.append(f"\nRESULTADOS ANTERIORES:")
            for agent, result in previous_results.items():
                prompt_parts.append(f"\n{agent}:\n{result[:500]}...")  # Limitar tamanho
        
        # Adicionar instruções específicas por tipo de agente
        if "SEO" in agent_name:
            if briefing.blog_config:
                blog_config = briefing.blog_config if isinstance(briefing.blog_config, dict) else {}
                prompt_parts.append(f"\nCONFIGURAÇÃO DE SEO:")
                prompt_parts.append(f"Palavra-chave principal: {blog_config.get('palavra_chave_principal', 'Não informado')}")
                prompt_parts.append(f"Palavras secundárias: {blog_config.get('palavras_secundarias', 'Não informado')}")
        
        if "Redes Sociais" in agent_name:
            if briefing.redes_sociais:
                redes = briefing.redes_sociais if isinstance(briefing.redes_sociais, dict) else {}
                prompt_parts.append(f"\nCONFIGURAÇÃO DE REDES SOCIAIS:")
                prompt_parts.append(f"Plataformas: {redes.get('plataformas', [])}")
                prompt_parts.append(f"Formatos: {redes.get('formatos', [])}")
        
        return "\n".join(prompt_parts)
    
    def generate_briefing_from_name(self, company_id: Optional[int], user_id: int, nome_empresa_produto: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Gera um briefing completo a partir apenas do nome da empresa/produto (company_id pode ser None para superadmin)"""
        try:
            # Buscar o agente gerador de briefing
            agent = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.name == "Gerador de Briefing"
            ).first()
            
            if not agent:
                return {
                    "success": False,
                    "error": "Agente 'Gerador de Briefing' não encontrado. Execute o script de criação do agente."
                }
            
            # Executar o agente
            prompt = f"Gere um briefing completo de marketing para: {nome_empresa_produto}"
            
            result = self.executor.execute(
                agent_id=agent.id,
                user=user,
                message=prompt,
                context_data={
                    "nome_empresa_produto": nome_empresa_produto
                }
            )
            
            if not result.get("success"):
                return result
            
            # Parsear a resposta JSON do agente
            response_content = result.get("response", "")
            
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                briefing_data = json.loads(json_match.group())
            else:
                # Se não encontrar JSON, tentar parsear diretamente
                try:
                    briefing_data = json.loads(response_content)
                except:
                    return {
                        "success": False,
                        "error": "Não foi possível parsear a resposta do agente como JSON"
                    }
            
            # Criar o briefing com os dados gerados
            briefing = ContentBriefing(
                company_id=company_id,
                user_id=user_id,
                nome_empresa_produto=briefing_data.get("nome_empresa_produto", nome_empresa_produto),
                publico_alvo=briefing_data.get("publico_alvo"),
                objetivo_conteudo=briefing_data.get("objetivo_conteudo", []),
                estagio_funil=briefing_data.get("estagio_funil"),
                linha_editorial=briefing_data.get("linha_editorial"),
                redes_sociais=briefing_data.get("redes_sociais", {}),
                blog_config=briefing_data.get("blog_config", {}),
                material_complementar=briefing_data.get("material_complementar", []),
                status="draft"
            )
            
            self.db.add(briefing)
            self.db.commit()
            self.db.refresh(briefing)
            
            return {
                "success": True,
                "data": briefing.to_dict(),
                "raw_response": response_content
            }
            
        except json.JSONDecodeError as e:
            self.db.rollback()
            logger.error(f"Erro ao parsear JSON do agente: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao parsear resposta do agente: {str(e)}",
                "raw_response": result.get("response", "") if 'result' in locals() else ""
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao gerar briefing: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _parse_agents_list(self, content: str) -> List[str]:
        """Parseia resposta do orquestrador para extrair lista de agentes"""
        try:
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                agents_json = json_match.group(0)
                agents = json.loads(agents_json)
                if isinstance(agents, list):
                    return agents
        except:
            pass
        
        # Fallback: tentar identificar agentes por nome
        available_agents = [
            "Geração de Texto",
            "Criação de Texto",
            "Otimização SEO",
            "Copy para Redes Sociais",
            "Geração de Imagens",
            "Geração de Imagem",
            "Scripts de Vídeo",
            "Email Marketing",
            "Copy para Anúncios"
        ]
        
        found_agents = []
        for agent in available_agents:
            if agent.lower() in content.lower():
                found_agents.append(agent)
        
        return found_agents if found_agents else ["Criação de Texto"]  # Default
    
    def _get_content_key_for_agent(self, agent_name: str) -> str:
        """Retorna chave para salvar conteúdo gerado por agente"""
        mapping = {
            "Geração de Texto": "texto_completo",
            "Criação de Texto": "texto_completo",
            "Otimização SEO": "seo",
            "Copy para Redes Sociais": "redes_sociais_copy",
            "Geração de Imagens": "imagens",
            "Geração de Imagem": "imagens",
            "Scripts de Vídeo": "video_script",
            "Email Marketing": "email_marketing",
            "Copy para Anúncios": "ad_copy"
        }
        return mapping.get(agent_name, agent_name.lower().replace(" ", "_"))

