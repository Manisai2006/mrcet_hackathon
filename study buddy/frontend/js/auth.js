// Authentication & User Session Page Handlers
document.addEventListener('DOMContentLoaded', () => {
    // Check session on protected pages
    const path = window.location.pathname;
    const isPublicPage = path.includes('login.html') || path.includes('register.html') || path.endsWith('index.html') || path === '/';

    const token = API.getToken();

    if (!token && !isPublicPage) {
        window.location.href = 'login.html';
        return;
    }

    if (token && (path.includes('login.html') || path.includes('register.html'))) {
        window.location.href = 'dashboard.html';
        return;
    }

    // Handle Login Form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const submitBtn = loginForm.querySelector('button[type="submit"]');

            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Logging in...';
                
                await API.login(email, password);
                showToast('Welcome back! Redirecting to dashboard...', 'success');
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 800);
            } catch (err) {
                showToast(err.message || 'Login failed. Please check your credentials.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Login <i class="fa-solid fa-arrow-right ms-2"></i>';
            }
        });
    }

    // Handle Registration Form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const student_class = document.getElementById('student_class').value;
            const preferred_language = document.getElementById('preferred_language').value;
            const submitBtn = registerForm.querySelector('button[type="submit"]');

            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Creating Account...';

                await API.register({
                    name,
                    email,
                    password,
                    student_class,
                    preferred_language
                });

                showToast('Registration successful! Logging you in...', 'success');
                // Automatically log in newly created user
                await API.login(email, password);
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1000);
            } catch (err) {
                showToast(err.message || 'Registration failed. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Create Account <i class="fa-solid fa-user-plus ms-2"></i>';
            }
        });
    }

    // Populate and Handle Profile Settings Form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        loadProfileData();

        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value.trim();
            const student_class = document.getElementById('student_class').value;
            const preferred_language = document.getElementById('preferred_language').value;
            const preferred_subjects = document.getElementById('preferred_subjects').value.trim();
            const learning_level = document.getElementById('learning_level').value;
            const submitBtn = profileForm.querySelector('button[type="submit"]');

            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Saving Changes...';

                await API.updateProfile({
                    name,
                    student_class,
                    preferred_language,
                    preferred_subjects,
                    learning_level
                });

                showToast('Profile updated successfully!', 'success');
            } catch (err) {
                showToast(err.message || 'Failed to update profile.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Save Profile Settings';
            }
        });
    }
});

async function loadProfileData() {
    try {
        const user = await API.getMe();
        if (user && user.profile) {
            document.getElementById('email').value = user.email || '';
            document.getElementById('name').value = user.profile.name || '';
            document.getElementById('student_class').value = user.profile.student_class || '10th';
            document.getElementById('preferred_language').value = user.profile.preferred_language || 'English';
            if (document.getElementById('preferred_subjects')) {
                document.getElementById('preferred_subjects').value = user.profile.preferred_subjects || '';
            }
            if (document.getElementById('learning_level')) {
                document.getElementById('learning_level').value = user.profile.learning_level || 'Intermediate';
            }
        }
    } catch (err) {
        showToast('Failed to load student profile data.', 'error');
    }
}
