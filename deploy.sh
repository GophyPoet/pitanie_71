#!/bin/bash
# ============================================
# Скрипт деплоя pitanie_71
# Школьное питание - учёт посещаемости
# ============================================
set -e

APP_DIR="/opt/pitanie_71"
REPO_URL="https://github.com/GophyPoet/pitanie_71.git"
BRANCH="claude/school-attendance-app-vYnqq"
SERVER_IP=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "  Деплой приложения Питание-71"
echo "  Сервер: $SERVER_IP"
echo "=========================================="

# --- 1. Обновление системы и установка зависимостей ---
echo ""
echo "[1/7] Установка системных пакетов..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nginx \
    git \
    curl \
    > /dev/null 2>&1

# Установка Node.js 20 (если не установлен)
if ! command -v node &> /dev/null || [[ $(node -v | cut -d'.' -f1 | tr -d 'v') -lt 18 ]]; then
    echo "  Установка Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1
    sudo apt-get install -y -qq nodejs > /dev/null 2>&1
fi
echo "  Python: $(python3 --version)"
echo "  Node.js: $(node --version)"
echo "  npm: $(npm --version)"

# --- 2. Клонирование репозитория ---
echo ""
echo "[2/7] Клонирование репозитория..."
if [ -d "$APP_DIR" ]; then
    echo "  Обновление существующего кода..."
    cd "$APP_DIR"
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    sudo git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
    sudo chown -R $USER:$USER "$APP_DIR"
fi
cd "$APP_DIR"
echo "  Код загружен."

# --- 3. Backend setup ---
echo ""
echo "[3/7] Настройка Backend (FastAPI)..."
cd "$APP_DIR/backend"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Создаём .env если нет
if [ ! -f .env ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > .env << ENVEOF
DATABASE_URL=sqlite:///./school_meals.db
SECRET_KEY=$SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=school71@example.com
ENVEOF
    echo "  .env создан с безопасным ключом"
fi

# Инициализация БД
python3 seed.py
echo "  База данных инициализирована."
deactivate

# --- 4. Frontend build ---
echo ""
echo "[4/7] Сборка Frontend (React)..."
cd "$APP_DIR/frontend"
npm install --silent 2>&1 | tail -1
npm run build 2>&1 | tail -3
echo "  Frontend собран."

# --- 5. Systemd сервис для backend ---
echo ""
echo "[5/7] Настройка systemd сервиса..."
sudo tee /etc/systemd/system/pitanie71.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Pitanie71 Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pitanie_71/backend
Environment=PATH=/opt/pitanie_71/backend/venv/bin:/usr/bin:/bin
ExecStart=/opt/pitanie_71/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable pitanie71
sudo systemctl restart pitanie71
echo "  Backend запущен как сервис."

# --- 6. Nginx конфигурация ---
echo ""
echo "[6/7] Настройка Nginx..."
sudo tee /etc/nginx/sites-available/pitanie71 > /dev/null << NGINXEOF
server {
    listen 80;
    server_name $SERVER_IP _;

    # Frontend (React build)
    root /opt/pitanie_71/frontend/dist;
    index index.html;

    # API proxy to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 50M;
    }

    # SPA fallback - все маршруты -> index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINXEOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/pitanie71 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
echo "  Nginx настроен."

# --- 7. Готово! ---
echo ""
echo "=========================================="
echo "  ДЕПЛОЙ ЗАВЕРШЁН УСПЕШНО!"
echo "=========================================="
echo ""
echo "  Приложение доступно по адресу:"
echo ""
echo "    http://$SERVER_IP"
echo ""
echo "  Логины для входа:"
echo "    Админ:    admin / admin123"
echo "    Учитель:  krasnova / teacher123"
echo ""
echo "  Управление:"
echo "    sudo systemctl status pitanie71"
echo "    sudo systemctl restart pitanie71"
echo "    sudo journalctl -u pitanie71 -f"
echo "=========================================="
