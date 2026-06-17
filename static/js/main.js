function setMode(mode) {
    const actionInput = document.getElementById('form-action');
    const submitBtn = document.getElementById('submit-button');
    const subtitle = document.getElementById('subtitle-text');
    const btnLogin = document.getElementById('btn-login');
    const btnRegister = document.getElementById('btn-register');

    if (!actionInput || !submitBtn || !subtitle) return;

    if (mode === 'login') {
        actionInput.value = 'login';
        submitBtn.innerText = 'Sign In';
        subtitle.innerText = 'Sign in to access your account';
        if (btnLogin) btnLogin.classList.add('active');
        if (btnRegister) btnRegister.classList.remove('active');
    } else {
        actionInput.value = 'register';
        submitBtn.innerText = 'Create Account';
        subtitle.innerText = 'Create a new account profile';
        if (btnLogin) btnLogin.classList.remove('active');
        if (btnRegister) btnRegister.classList.add('active');
    }
}