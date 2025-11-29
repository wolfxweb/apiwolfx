"""
Script para criar tabelas de Recursos Humanos (RH)
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.config.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_hr_tables():
    """Cria todas as tabelas de RH no banco de dados"""
    try:
        with engine.begin() as conn:  # begin() faz commit automático
            # Criar tabela employees
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    user_id INTEGER,
                    cpf VARCHAR(14) NOT NULL,
                    rg VARCHAR(20),
                    nome_completo VARCHAR(255) NOT NULL,
                    data_nascimento DATE,
                    telefone VARCHAR(20),
                    email VARCHAR(255),
                    endereco TEXT,
                    cidade VARCHAR(100),
                    estado VARCHAR(2),
                    cep VARCHAR(10),
                    cargo VARCHAR(100),
                    departamento VARCHAR(100),
                    data_admissao DATE NOT NULL,
                    data_demissao DATE,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    salario_base NUMERIC(10, 2) NOT NULL,
                    tipo_contrato VARCHAR(20) DEFAULT 'clt',
                    carga_horaria INTEGER DEFAULT 220,
                    financial_category_id INTEGER,
                    cost_center_id INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_employees_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    CONSTRAINT fk_employees_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT fk_employees_financial_category FOREIGN KEY (financial_category_id) REFERENCES financial_categories(id) ON DELETE SET NULL,
                    CONSTRAINT fk_employees_cost_center FOREIGN KEY (cost_center_id) REFERENCES cost_centers(id) ON DELETE SET NULL
                );
            """))
            
            # Criar índices para employees
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_employees_company_cpf 
                ON employees(company_id, cpf);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_company_status 
                ON employees(company_id, status);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_cpf ON employees(cpf);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_email ON employees(email);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_data_admissao ON employees(data_admissao);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_financial_category ON employees(financial_category_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employees_cost_center ON employees(cost_center_id);
            """))
            
            # Criar tabela payroll
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payroll (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    company_id INTEGER NOT NULL,
                    mes_referencia INTEGER NOT NULL,
                    ano_referencia INTEGER NOT NULL,
                    salario_bruto NUMERIC(10, 2) NOT NULL,
                    descontos NUMERIC(10, 2) DEFAULT 0,
                    adicionais NUMERIC(10, 2) DEFAULT 0,
                    inss NUMERIC(10, 2) DEFAULT 0,
                    irrf NUMERIC(10, 2) DEFAULT 0,
                    fgts NUMERIC(10, 2) DEFAULT 0,
                    salario_liquido NUMERIC(10, 2) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    observacoes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP WITH TIME ZONE,
                    paid_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT fk_payroll_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    CONSTRAINT fk_payroll_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                );
            """))
            
            # Criar índices para payroll
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_payroll_employee_period 
                ON payroll(employee_id, mes_referencia, ano_referencia);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_payroll_company_period 
                ON payroll(company_id, mes_referencia, ano_referencia);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_payroll_ano_referencia ON payroll(ano_referencia);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_payroll_status ON payroll(status);
            """))
            
            # Criar tabela payroll_items
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payroll_items (
                    id SERIAL PRIMARY KEY,
                    payroll_id INTEGER NOT NULL,
                    tipo VARCHAR(20) NOT NULL,
                    descricao VARCHAR(255) NOT NULL,
                    valor NUMERIC(10, 2) NOT NULL,
                    codigo_referencia VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_payroll_items_payroll FOREIGN KEY (payroll_id) REFERENCES payroll(id) ON DELETE CASCADE
                );
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_payroll_items_payroll ON payroll_items(payroll_id);
            """))
            
            # Criar tabela employee_vacations
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employee_vacations (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    periodo_aquisitivo_inicio DATE NOT NULL,
                    periodo_aquisitivo_fim DATE NOT NULL,
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    dias INTEGER NOT NULL DEFAULT 30,
                    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                    observacoes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_employee_vacations_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_vacations_employee ON employee_vacations(employee_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_vacations_status ON employee_vacations(status);
            """))
            
            # Criar tabela employee_benefits
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employee_benefits (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    tipo_beneficio VARCHAR(50) NOT NULL,
                    descricao VARCHAR(255) NOT NULL,
                    valor NUMERIC(10, 2) NOT NULL,
                    data_inicio DATE NOT NULL,
                    data_fim DATE,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_employee_benefits_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
                );
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_benefits_employee ON employee_benefits(employee_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_benefits_status ON employee_benefits(status);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_benefits_tipo ON employee_benefits(tipo_beneficio);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_benefits_data_inicio ON employee_benefits(data_inicio);
            """))
            
            # Criar tabela employee_permissions
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employee_permissions (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    company_id INTEGER NOT NULL,
                    menu_name VARCHAR(50) NOT NULL,
                    submenu_name VARCHAR(50),
                    has_access BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_employee_permissions_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    CONSTRAINT fk_employee_permissions_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                );
            """))
            
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_employee_permissions_employee_menu 
                ON employee_permissions(employee_id, menu_name, submenu_name);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_permissions_company ON employee_permissions(company_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_permissions_menu_name ON employee_permissions(menu_name);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_employee_permissions_submenu_name ON employee_permissions(submenu_name);
            """))
            
            logger.info("✅ Tabelas de RH verificadas/criadas com sucesso!")
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas de RH: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    create_hr_tables()

