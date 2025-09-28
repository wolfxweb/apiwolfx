# 📁 Pasta Public - API Mercado Livre

Esta pasta contém todos os arquivos estáticos da aplicação, incluindo CSS, JavaScript, imagens e fontes.

## 🎨 Design Bootstrap

O design foi atualizado para usar a **paleta de cores padrão do Bootstrap**, proporcionando um visual mais limpo e profissional.

### 🎯 Paleta de Cores Bootstrap
- **Primary**: `#0d6efd` (Azul)
- **Secondary**: `#6c757d` (Cinza)
- **Success**: `#198754` (Verde)
- **Danger**: `#dc3545` (Vermelho)
- **Warning**: `#ffc107` (Amarelo)
- **Info**: `#0dcaf0` (Ciano)

### 🎨 Componentes Atualizados
- **Cards**: Usando classes Bootstrap padrão
- **Botões**: Cores e estilos Bootstrap
- **Alertas**: Paleta de cores Bootstrap
- **Ícones**: Cores consistentes com Bootstrap
- **Grid**: Sistema de grid Bootstrap

### 📱 Demonstração
- **Design Bootstrap**: `/static/DESIGN_BOOTSTRAP.html`
- **Ícones**: `/static/ICONES_EXEMPLOS.html`

## 📂 Estrutura de Pastas

```
public/
├── css/                    # Arquivos CSS
│   ├── bootstrap.min.css   # Bootstrap 5 (minificado)
│   ├── bootstrap.css       # Bootstrap 5 (desenvolvimento)
│   ├── bootstrap-icons.css # CSS para ícones Bootstrap
│   └── custom.css         # CSS personalizado
├── js/                     # Arquivos JavaScript
│   ├── bootstrap.bundle.min.js  # Bootstrap 5 JS (minificado)
│   ├── bootstrap.bundle.js       # Bootstrap 5 JS (desenvolvimento)
│   └── custom.js          # JavaScript personalizado
├── images/                 # Imagens
│   └── (imagens da aplicação)
├── fonts/                  # Fontes
│   └── (fontes personalizadas)
├── *.svg                   # Ícones Bootstrap (1800+ ícones)
└── ICONES_EXEMPLOS.html    # Página de exemplos dos ícones
```

## 🎨 Bootstrap 5

### CSS
- **bootstrap.min.css**: Versão minificada para produção
- **bootstrap.css**: Versão completa para desenvolvimento
- **bootstrap-grid.css**: Apenas sistema de grid
- **bootstrap-utilities.css**: Apenas utilitários

### JavaScript
- **bootstrap.bundle.min.js**: Versão minificada com Popper.js
- **bootstrap.bundle.js**: Versão completa com Popper.js
- **bootstrap.min.js**: Apenas Bootstrap (sem Popper.js)

## 🎯 Bootstrap Icons

### Ícones Disponíveis
- **1800+ ícones SVG**: Todos os ícones do Bootstrap Icons
- **bootstrap-icons.css**: CSS personalizado para ícones
- **Cores personalizadas**: Cores do Mercado Livre
- **Tamanhos**: xs, sm, lg, xl, 2x, 3x, 4x, 5x
- **Animações**: spin, pulse, hover effects

### Como Usar
```html
<!-- Ícone básico -->
<i class="bi bi-heart"></i>

<!-- Ícone com tamanho -->
<i class="bi bi-star-fill bi-lg"></i>

<!-- Ícone com cor personalizada -->
<i class="bi bi-shield-lock-fill bi-ml-green"></i>

<!-- Ícone com animação -->
<i class="bi bi-arrow-clockwise bi-spin"></i>
```

## 🔧 Como Usar

### 1. CSS Personalizado
```html
<link href="/static/css/custom.css" rel="stylesheet">
```

### 2. JavaScript Personalizado
```html
<script src="/static/js/custom.js"></script>
```

### 3. Imagens
```html
<img src="/static/images/logo.png" alt="Logo">
```

## 🎯 Funcionalidades Personalizadas

### CSS (custom.css)
- Cores do Mercado Livre
- Botões personalizados
- Cards com estilo ML
- Responsividade

### JavaScript (custom.js)
- Animações de cards
- Validação de formulários
- Requisições AJAX
- Notificações
- Funções utilitárias

## 📱 Responsividade

Todos os arquivos são otimizados para:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (< 768px)

## 🚀 Performance

- Arquivos minificados para produção
- CSS e JS carregados de forma otimizada
- Imagens otimizadas
- Cache configurado

## 🔗 URLs de Acesso

- CSS: `/static/css/arquivo.css`
- JS: `/static/js/arquivo.js`
- Imagens: `/static/images/arquivo.png`
- Fontes: `/static/fonts/arquivo.woff2`

## 📝 Exemplos de Uso

### Botão Bootstrap
```html
<button class="btn btn-primary">
    <i class="bi bi-shield-lock-fill"></i> Botão Primary
</button>
```

### Card Bootstrap
```html
<div class="card shadow-sm hover-lift">
    <div class="card-body text-center">
        <div class="icon-modern">
            <i class="bi bi-star-fill text-primary"></i>
        </div>
        <h5 class="card-title text-primary">Título</h5>
        <p class="card-text">Descrição</p>
    </div>
</div>
```

### Alerta Bootstrap
```html
<div class="alert alert-info">
    <i class="bi bi-info-circle-fill"></i> Informação importante
</div>
```

### JavaScript personalizado
```javascript
// Mostrar notificação
MLAPI.showNotification('Sucesso!', 'success');

// Validar formulário
if (MLAPI.validateForm('meuForm')) {
    // Formulário válido
}
```
