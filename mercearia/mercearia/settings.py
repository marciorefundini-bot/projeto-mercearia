"""
Configurações do projeto Django — Mercearia da Neusa.

Guia de deploy seguro:
  https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

Variáveis de ambiente obrigatórias em produção:
  DJANGO_SECRET_KEY  — chave criptográfica (nunca compartilhe)
  DJANGO_DEBUG       — 'False' em produção
  DJANGO_ALLOWED_HOSTS — hosts separados por vírgula
"""

import os
from pathlib import Path
from django.contrib.messages import constants as message_constants

# ── Caminho raiz do projeto ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ── Carrega variáveis do arquivo .env (apenas em desenvolvimento local) ────────
# Em produção, defina as variáveis diretamente no ambiente do servidor.
# Formato do .env:  CHAVE=valor  (uma por linha; '#' para comentários)
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    with open(_env_path, encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            # Ignora linhas em branco e comentários
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _val = _line.split('=', 1)
                # setdefault: não sobrescreve variáveis já definidas no sistema
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))


# ── Segurança ──────────────────────────────────────────────────────────────────

# SECRET_KEY: usada para assinar cookies de sessão, tokens CSRF e links de
# reset de senha. NUNCA deixe este valor hardcoded ou versionado no Git.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'insecure-dev-fallback-troque-antes-de-subir-para-producao',
)

# DEBUG: em produção DEVE ser False — evita expor stack traces e dados internos.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: lista os domínios que podem servir esta aplicação.
# Exemplo de produção: DJANGO_ALLOWED_HOSTS=meusite.com,www.meusite.com
_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _hosts_env.split(',') if h.strip()]

# Em desenvolvimento sem ALLOWED_HOSTS definido, permite localhost automaticamente.
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# ── Apps instalados ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # App principal da mercearia (clientes, produtos, vendas)
    'clientes',
]

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Protege todos os formulários POST contra CSRF (Cross-Site Request Forgery)
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Adiciona o header X-Frame-Options para bloquear clickjacking
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mercearia.urls'

# ── Templates ──────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        # APP_DIRS=True: Django busca templates em <app>/templates/ automaticamente
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mercearia.wsgi.application'


# ── Banco de dados ─────────────────────────────────────────────────────────────
# SQLite é adequado para desenvolvimento e uso local de um único operador.
# Para produção com múltiplos usuários simultâneos, migre para PostgreSQL:
#   ENGINE: 'django.db.backends.postgresql'
#   NAME/USER/PASSWORD/HOST/PORT via variáveis de ambiente
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ── Validação de senhas de usuários ───────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Autenticação — redirecionamentos ──────────────────────────────────────────
# LOGIN_URL: para onde o @login_required redireciona usuários não autenticados.
LOGIN_URL = '/login/'
# LOGIN_REDIRECT_URL: após login bem-sucedido, vai para o dashboard.
LOGIN_REDIRECT_URL = '/'
# LOGOUT_REDIRECT_URL: após logout, volta para a tela de login.
LOGOUT_REDIRECT_URL = '/login/'


# ── Internacionalização ────────────────────────────────────────────────────────
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True   # Ativa tradução de strings internas do Django
USE_TZ = True     # Armazena datas em UTC; converte para TIME_ZONE na exibição


# ── Arquivos estáticos (CSS, JavaScript, imagens) ─────────────────────────────
STATIC_URL = 'static/'

# STATIC_ROOT: diretório onde 'manage.py collectstatic' agrupa todos os
# arquivos estáticos para ser servido pelo Nginx/Apache em produção.
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ── Campo primário padrão ──────────────────────────────────────────────────────
# BigAutoField usa inteiros de 64 bits — mais seguro para tabelas grandes.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── Mapeamento de tags de mensagem para classes Bootstrap ─────────────────────
# O Django usa 'error'; o Bootstrap usa 'danger'. Este mapeamento faz
# com que {% if message.tags == 'danger' %} funcione nos templates.
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}


# ── Logging ────────────────────────────────────────────────────────────────────
# Em desenvolvimento mostra tudo no console.
# Em produção, considere enviar erros para um serviço (Sentry, Logtail, etc.).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # Formato: [NÍVEL] 2024-01-01 12:00:00 módulo: mensagem
            'format': '[{levelname}] {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        # DEBUG em desenvolvimento; WARNING em produção (menos ruído)
        'level': 'DEBUG' if DEBUG else 'WARNING',
    },
    'loggers': {
        # Registra queries SQL apenas em modo debug
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}
