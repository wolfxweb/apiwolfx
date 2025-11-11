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
function showNotification(message, type = 'info', duration = 8000) {
    const palette = {
        success: { title: 'Sucesso', icon: 'bi-check-circle-fill', headerBg: 'bg-success', headerText: 'text-white' },
        error: { title: 'Erro', icon: 'bi-x-circle-fill', headerBg: 'bg-danger', headerText: 'text-white' },
        warning: { title: 'Atenção', icon: 'bi-exclamation-triangle-fill', headerBg: 'bg-warning', headerText: 'text-dark' },
        info: { title: 'Informação', icon: 'bi-info-circle-fill', headerBg: 'bg-primary', headerText: 'text-white' },
    };
    const scheme = palette[type] || palette.info;

    let container = document.getElementById('global-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'global-toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const toastTemplate = container.querySelector('.toast[data-template="true"]');
    let toastElement;

    if (toastTemplate) {
        toastElement = toastTemplate.cloneNode(true);
        toastElement.dataset.template = 'false';
        toastElement.classList.remove('d-none');
    } else {
        toastElement = document.createElement('div');
        toastElement.className = 'toast border-0 shadow-lg';
        toastElement.setAttribute('role', 'alert');
        toastElement.setAttribute('aria-live', 'assertive');
        toastElement.setAttribute('aria-atomic', 'true');
        toastElement.dataset.template = 'true';
        toastElement.innerHTML = `
            <div class="toast-header">
                <span class="toast-icon me-2"></span>
                <strong class="me-auto toast-title"></strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Fechar"></button>
            </div>
            <div class="toast-body"></div>
        `;
        container.appendChild(toastElement);
        toastElement = toastElement.cloneNode(true);
        toastElement.dataset.template = 'false';
        toastElement.classList.remove('d-none');
    }

    const header = toastElement.querySelector('.toast-header');
    const iconEl = toastElement.querySelector('.toast-icon');
    const titleEl = toastElement.querySelector('.toast-title');
    const bodyEl = toastElement.querySelector('.toast-body');
    const closeBtn = toastElement.querySelector('.btn-close');

    header.className = `toast-header ${scheme.headerBg} ${scheme.headerText}`;
    iconEl.className = `toast-icon bi ${scheme.icon}`;
    titleEl.textContent = scheme.title;
    bodyEl.textContent = '';
    if (typeof message === 'string') {
        bodyEl.innerHTML = message;
    } else if (message instanceof HTMLElement) {
        bodyEl.appendChild(message);
    }
    if (scheme.headerText === 'text-white') {
        closeBtn.classList.add('btn-close-white');
    } else {
        closeBtn.classList.remove('btn-close-white');
    }

    toastElement.classList.remove('show');
    toastElement.style.setProperty('--bs-toast-bg', '#ffffff');
    toastElement.style.backgroundColor = '#ffffff';
    toastElement.querySelector('.toast-body').style.backgroundColor = '#ffffff';

    container.appendChild(toastElement);

    const bsToast = new bootstrap.Toast(toastElement, { delay: duration });
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
    bsToast.show();
}

// 🎯 Obter Ícone da Notificação
function getNotificationIcon(type) {
    const icons = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-x-circle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'info': 'bi-info-circle-fill'
    };
    return icons[type] || icons['info'];
}

function getNotificationTitle(type) {
    const titles = {
        'success': 'Sucesso',
        'error': 'Erro',
        'warning': 'Atenção',
        'info': 'Informação'
    };
    return titles[type] || titles['info'];
}

function getNotificationAccent(type) {
    const accents = {
        'success': '#22c55e',
        'error': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6'
    };
    return accents[type] || accents['info'];
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
function makeRequest(url, options = {}) {
    showLoading('content', 'Processando requisição...');
    
    return fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.headers || {})
        },
        ...options
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading('content', data);
        return data;
    })
    .catch(error => {
        console.error('Erro na requisição:', error);
        showNotification('Erro na requisição: ' + error.message, 'error');
        throw error;
    });
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
