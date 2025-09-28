# 🚀 API Mercado Livre - FastAPI MVC

Uma API moderna para integração com o Mercado Livre usando FastAPI, arquitetura MVC e design Bootstrap puro.

## 📋 Características

- **FastAPI** - Framework web moderno e rápido
- **Arquitetura MVC** - Model-View-Controller organizado
- **Bootstrap 5** - Design responsivo e limpo
- **Bootstrap Icons** - Ícones modernos
- **ngrok** - Exposição segura para callbacks
- **OAuth2** - Autenticação segura com Mercado Livre

## 🏗️ Estrutura do Projeto

```
apiwolfx/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicação FastAPI principal
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Configurações da aplicação
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── auth_controller.py  # Controller de autenticação
│   ├── models/
│   │   ├── __init__.py
│   │   └── mercadolibre_models.py # Modelos Pydantic
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main_routes.py      # Rotas principais
│   │   ├── auth_routes.py      # Rotas de autenticação
│   │   ├── product_routes.py   # Rotas de produtos
│   │   ├── user_routes.py      # Rotas de usuário
│   │   └── category_routes.py  # Rotas de categorias
│   ├── services/
│   │   ├── __init__.py
│   │   └── mercadolibre_service.py # Serviço ML
│   └── views/
│       ├── __init__.py
│       ├── template_renderer.py # Renderizador de templates
│       └── templates/
│           ├── base.html       # Template base
│           ├── home.html       # Página inicial
│           ├── login_success.html
│           ├── user_info.html
│           └── error.html
├── public/
│   ├── css/
│   │   ├── bootstrap.min.css   # Bootstrap 5
│   │   ├── bootstrap-icons.css # Bootstrap Icons
│   │   └── custom.css          # CSS customizado
│   ├── js/
│   │   ├── bootstrap.bundle.min.js # Bootstrap JS
│   │   └── custom.js           # JavaScript customizado
│   ├── images/                 # Imagens
│   ├── fonts/                  # Fontes
│   └── *.svg                   # Ícones Bootstrap
├── requirements.txt              # Dependências Python
├── start.py                    # Script para iniciar com ngrok
├── run_local.py               # Script para rodar localmente
└── README.md                  # Este arquivo
```

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/apiwolfx.git
cd apiwolfx
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as credenciais
Edite o arquivo `app/config/settings.py`:
```python
self.ml_app_id = "SEU_APP_ID_AQUI"
self.ml_client_secret = "SEU_CLIENT_SECRET_AQUI"
self.ml_redirect_uri = "https://sua-url.ngrok.io/api/callback"
```

## 🎯 Como Usar

### Com ngrok (Recomendado)
```bash
python start.py
```

### Localmente
```bash
python run_local.py
```

## 📱 URLs da API

- **Home**: `/`
- **Login**: `/login`
- **Callback**: `/api/callback`
- **Documentação**: `/docs`
- **Status**: `/health`

## 🔧 Configuração no Mercado Livre

1. Acesse [Mercado Livre Developers](https://developers.mercadolibre.com/)
2. Crie uma nova aplicação
3. Configure a URL de redirecionamento: `https://sua-url.ngrok.io/api/callback`
4. Copie o App ID e Client Secret
5. Configure no arquivo `app/config/settings.py`

## 🎨 Design

- **Bootstrap 5** - Framework CSS responsivo
- **Bootstrap Icons** - Biblioteca de ícones
- **Design Limpo** - Interface moderna e profissional
- **Responsivo** - Funciona em todos os dispositivos

## 📚 Tecnologias

- **FastAPI** - Framework web
- **Pydantic** - Validação de dados
- **httpx** - Cliente HTTP assíncrono
- **Jinja2** - Templates HTML
- **Bootstrap 5** - CSS Framework
- **ngrok** - Túnel seguro

## 🔐 Autenticação

A API usa OAuth2 para autenticação com o Mercado Livre:

1. Usuário acessa `/login`
2. É redirecionado para o Mercado Livre
3. Autoriza a aplicação
4. Retorna para `/api/callback` com código
5. Código é trocado por token de acesso

## 📖 Documentação da API

Acesse `/docs` para ver a documentação interativa da API.

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

- **GitHub Issues**: [Reportar problemas](https://github.com/seu-usuario/apiwolfx/issues)
- **Email**: seu-email@exemplo.com

## 🙏 Agradecimentos

- [FastAPI](https://fastapi.tiangolo.com/)
- [Bootstrap](https://getbootstrap.com/)
- [Mercado Livre API](https://developers.mercadolibre.com/)
- [ngrok](https://ngrok.com/)

---

**Desenvolvido com ❤️ para integração com Mercado Livre**