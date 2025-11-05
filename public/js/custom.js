/* ========================================
   🚀 API MERCADO LIVRE - JAVASCRIPT MODERNO
   ======================================== */

// 🌟 Inicialização Moderna
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 API Mercado Livre carregada com sucesso!');
    
    // Inicializar componentes modernos
    initModernComponents();
    initAnimations();
    initInteractions();
    initTooltips();
    initParallax();
});

// 🎨 Inicializar Componentes Modernos
function initModernComponents() {
    // Adicionar classes de animação aos elementos
    const animatedElements = document.querySelectorAll('.animate-fadeInUp, .animate-slideInLeft');
    animatedElements.forEach((element, index) => {
        element.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Adicionar efeitos de hover aos cards
    const cards = document.querySelectorAll('.card-modern');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// 🎯 Inicializar Animações
function initAnimations() {
    // Intersection Observer para animações on-scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeInUp');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    // Observar elementos para animação
    const elementsToAnimate = document.querySelectorAll('.card-modern, .alert-modern');
    elementsToAnimate.forEach(element => {
        observer.observe(element);
    });
}

// 🎮 Inicializar Interações
function initInteractions() {
    // Efeito de ripple nos botões
    const buttons = document.querySelectorAll('.btn-modern');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            createRippleEffect(e, this);
        });
    });
    
    // Efeito de typing nos títulos
    const titles = document.querySelectorAll('.hero-title');
    titles.forEach(title => {
        typeWriter(title, title.textContent, 100);
    });
}

// 🌊 Criar Efeito Ripple
function createRippleEffect(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple');
    
    element.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// ⌨️ Efeito TypeWriter
function typeWriter(element, text, speed = 100) {
    element.textContent = '';
    let i = 0;
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// 🎯 Inicializar Tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// 🌟 Inicializar Parallax
function initParallax() {
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.hero-header');
        
        parallaxElements.forEach(element => {
            const speed = 0.5;
            element.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
}

// 📋 Copiar Código com Feedback Moderno
function copyCode(element) {
    const code = element.textContent;
    navigator.clipboard.writeText(code).then(() => {
        // Feedback visual moderno
        const originalText = element.textContent;
        element.innerHTML = '<i class="bi bi-check-circle-fill"></i> Copiado!';
        element.style.background = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
        element.style.color = 'white';
        element.style.transform = 'scale(1.05)';
        
        setTimeout(() => {
            element.textContent = originalText;
            element.style.background = '';
            element.style.color = '';
            element.style.transform = '';
        }, 2000);
    });
}

// 🎨 Mostrar Notificação Moderna
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert-modern position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.style.animation = 'slideInRight 0.5s ease-out';
    
    const icon = getNotificationIcon(type);
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi ${icon} me-3"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remover automaticamente
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.5s ease-in';
            setTimeout(() => notification.remove(), 500);
        }
    }, duration);
}

// 🎯 Obter Ícone da Notificação
function getNotificationIcon(type) {
    const icons = {
        'success': 'bi-check-circle-fill bi-ml-green',
        'error': 'bi-x-circle-fill bi-danger',
        'warning': 'bi-exclamation-triangle-fill bi-warning',
        'info': 'bi-info-circle-fill bi-ml-blue'
    };
    return icons[type] || icons['info'];
}

// 🔄 Loading State Moderno
function showLoading(elementId, message = 'Carregando...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="text-muted">${message}</p>
            </div>
        `;
        element.classList.add('loading');
    }
}

// 🎯 Esconder Loading
function hideLoading(elementId, content) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
        element.classList.remove('loading');
    }
}

// 🌐 Requisições AJAX Modernas
async function makeRequest(url, options = {}) {
    try {
        showLoading('content', 'Processando requisição...');
        
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        hideLoading('content', data);
        return data;
        
    } catch (error) {
        console.error('Erro na requisição:', error);
        showNotification('Erro na requisição: ' + error.message, 'error');
        throw error;
    }
}

// 🎨 Adicionar CSS para Animações (verifica se já existe para evitar duplicação)
if (!document.getElementById('custom-animations-style')) {
    const style = document.createElement('style');
    style.id = 'custom-animations-style';
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
    document.head.appendChild(style);
}

// 🌟 Exportar API Global
window.MLAPI = {
    copyCode,
    showNotification,
    showLoading,
    hideLoading,
    makeRequest,
    createRippleEffect,
    typeWriter
};
