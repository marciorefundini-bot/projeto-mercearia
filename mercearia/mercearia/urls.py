"""
Configuração de URLs raiz do projeto Mercearia da Neusa.

Estrutura de rotas:
  /admin/    → Painel de administração Django
  /login/    → Tela de login (LoginView padrão do Django com template customizado)
  /logout/   → Encerramento de sessão (redireciona para /login/)
  /          → App 'clientes' (dashboard, clientes, produtos, vendas)
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Painel admin nativo do Django (requer superusuário)
    path('admin/', admin.site.urls),

    # ── Autenticação ──────────────────────────────────────────────────────────
    # LoginView: renderiza o template clientes/login.html e autentica o usuário.
    # Após login bem-sucedido, redireciona para LOGIN_REDIRECT_URL (settings.py).
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='clientes/login.html'),
        name='login',
    ),
    # LogoutView: destrói a sessão e redireciona para a tela de login.
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout',
    ),

    # ── App principal ─────────────────────────────────────────────────────────
    # Todas as rotas do app 'clientes' ficam em clientes/urls.py
    path('', include('clientes.urls')),
]
