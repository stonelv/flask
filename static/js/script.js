// 主题切换功能
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.classList.contains('dark-theme') ? 'dark' : 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    // 更新 HTML 类
    html.classList.toggle('dark-theme');

    // 保存到 sessionStorage
    sessionStorage.setItem('theme', newTheme);
}

// 页面加载时恢复主题
function initTheme() {
    const savedTheme = sessionStorage.getItem('theme');
    const html = document.documentElement;

    if (savedTheme === 'dark') {
        html.classList.add('dark-theme');
    } else {
        html.classList.remove('dark-theme');
    }
}

// 表单验证功能
function validateForm(form) {
    const title = form.querySelector('input[name="title"]');
    const content = form.querySelector('textarea[name="content"]');
    let isValid = true;

    // 清除之前的错误提示
    const errorMessages = form.querySelectorAll('.error-message');
    errorMessages.forEach(message => message.remove());

    // 验证标题
    if (!title.value.trim()) {
        showError(title, '标题不能为空');
        isValid = false;
    } else if (title.value.length > 120) {
        showError(title, '标题长度不能超过 120 个字符');
        isValid = false;
    }

    // 验证内容
    if (!content.value.trim()) {
        showError(content, '内容不能为空');
        isValid = false;
    }

    return isValid;
}

// 显示错误提示
function showError(input, message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.color = 'red';
    errorDiv.style.fontSize = '14px';
    errorDiv.style.marginTop = '5px';

    input.parentNode.appendChild(errorDiv);

    // 聚焦到错误输入框
    input.focus();
}

// 确认删除功能
function confirmDelete(button) {
    const articleTitle = button.getAttribute('data-title');
    return confirm(`确定要删除文章"${articleTitle}"吗？`);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化主题
    initTheme();

    // 为主题切换按钮添加事件监听器
    const themeToggleButton = document.querySelector('[href="/toggle_theme"]');
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', function(e) {
            // 阻止默认跳转，先切换主题
            e.preventDefault();
            toggleTheme();
            // 然后跳转
            window.location.href = this.href;
        });
    }

    // 为文章表单添加验证
    const articleForms = document.querySelectorAll('form[action*="/articles/"]');
    articleForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });

    // 为删除按钮添加确认功能
    const deleteButtons = document.querySelectorAll('button[formaction*="/delete"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const articleRow = this.closest('tr');
            const articleTitle = articleRow.querySelector('td:nth-child(2)').textContent;
            this.setAttribute('data-title', articleTitle);

            if (!confirmDelete(this)) {
                e.preventDefault();
            }
        });
    });

    // 为发布/取消发布按钮添加确认功能
    const publishButtons = document.querySelectorAll('button[formaction*="/toggle_publish"]');
    publishButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.textContent.trim();
            if (!confirm(`确定要${action}这篇文章吗？`)) {
                e.preventDefault();
            }
        });
    });
});

// 平滑滚动到顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 当页面滚动时显示/隐藏返回顶部按钮
window.addEventListener('scroll', function() {
    const scrollToTopButton = document.querySelector('#scrollToTop');
    if (scrollToTopButton) {
        if (window.pageYOffset > 300) {
            scrollToTopButton.style.display = 'block';
        } else {
            scrollToTopButton.style.display = 'none';
        }
    }
});