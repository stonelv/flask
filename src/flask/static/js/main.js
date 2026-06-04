// 主JavaScript文件
// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化表单验证
    initFormValidation();
    
    // 初始化主题切换
    initThemeToggle();
    
    // 初始化文章卡片动画
    initArticleCardAnimations();
    
    // 初始化分页功能
    initPagination();
});

// 表单验证初始化
function initFormValidation() {
    // 获取所有表单
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // 为表单添加提交事件监听器
        form.addEventListener('submit', function(e) {
            // 清除之前的错误信息
            clearFormErrors(form);
            
            // 验证表单字段
            const isValid = validateFormFields(form);
            
            // 如果验证失败，阻止表单提交
            if (!isValid) {
                e.preventDefault();
            }
        });
        
        // 为表单字段添加输入事件监听器，实时验证
        const inputs = form.querySelectorAll('input[type="text"], input[type="password"], textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                validateField(this);
            });
        });
    });
}

// 清除表单错误信息
function clearFormErrors(form) {
    // 清除所有错误消息
    const errorMessages = form.querySelectorAll('.error-message');
    errorMessages.forEach(message => message.remove());
    
    // 清除所有字段的错误状态
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.classList.remove('error');
    });
}

// 验证表单字段
function validateFormFields(form) {
    let isValid = true;
    
    // 获取所有必填字段
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
        }
    });
    
    return isValid;
}

// 验证单个字段
function validateField(field) {
    let isValid = true;
    let errorMessage = '';
    
    // 清除之前的错误状态
    field.classList.remove('error');
    const existingError = field.parentNode.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // 必填验证
    if (field.hasAttribute('required') && !field.value.trim()) {
        isValid = false;
        errorMessage = '此字段为必填项';
    }
    
    // 长度验证
    if (field.hasAttribute('maxlength')) {
        const maxLength = parseInt(field.getAttribute('maxlength'));
        if (field.value.length > maxLength) {
            isValid = false;
            errorMessage = `长度不能超过${maxLength}个字符`;
        }
    }
    
    // 如果验证失败，显示错误信息
    if (!isValid) {
        field.classList.add('error');
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = errorMessage;
        errorElement.style.color = 'var(--accent-danger)';
        errorElement.style.fontSize = '0.875rem';
        errorElement.style.marginTop = '0.25rem';
        
        field.parentNode.appendChild(errorElement);
    }
    
    return isValid;
}

// 主题切换初始化
function initThemeToggle() {
    // 获取主题切换按钮
    const themeToggleButtons = document.querySelectorAll('form[action="/admin/theme/toggle"] button');
    
    themeToggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // 添加平滑过渡效果
            document.documentElement.style.transition = 'background-color 0.3s ease, color 0.3s ease';
            
            // 延迟移除过渡效果，以便下次切换时仍然有过渡
            setTimeout(() => {
                document.documentElement.style.transition = '';
            }, 300);
        });
    });
}

// 文章卡片动画初始化
function initArticleCardAnimations() {
    // 获取所有文章卡片
    const articleCards = document.querySelectorAll('.article-card');
    
    // 为文章卡片添加鼠标悬停效果
    articleCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.01)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// 分页功能初始化
function initPagination() {
    // 获取所有分页链接
    const paginationLinks = document.querySelectorAll('.pagination a');
    
    paginationLinks.forEach(link => {
        // 如果是禁用状态，阻止点击
        if (link.parentNode.classList.contains('disabled')) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
            });
        }
    });
}

// 平滑滚动到页面顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 显示加载指示器
function showLoadingIndicator() {
    // 创建加载指示器元素
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator';
    loadingIndicator.innerHTML = `
        <div class="spinner"></div>
        <p>加载中...</p>
    `;
    
    // 添加样式
    loadingIndicator.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        color: white;
    `;
    
    // 添加到页面
    document.body.appendChild(loadingIndicator);
}

// 隐藏加载指示器
function hideLoadingIndicator() {
    const loadingIndicator = document.querySelector('.loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}
