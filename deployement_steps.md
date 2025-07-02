
# Ez-Task Production Deployment Guide

## ✅ Deployment Plan for Ez-Task (Production)

### 1. Choose a Hosting Platform
Examples:
- VPS (e.g. DigitalOcean, Linode, AWS EC2) — full control
- Platform-as-a-Service (e.g. Heroku, Render) — easier, less config

For full control and secure file handling, VPS is recommended.

### 2. Set Up the Production Server

#### Install necessary packages:
```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx mysql-server
```

#### Clone your project:
```bash
git clone <your-repo-url> ez-task
cd ez-task
```

#### Set up a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:
```
DEBUG=False
SECRET_KEY=<your-secret>
DB_NAME=ez
DB_USER=<prod_user>
DB_PASSWORD=<prod_password>
DB_HOST=localhost
DB_PORT=3306
EMAIL_HOST=...
FERNET_KEY=...
```

Important: NEVER commit this file to version control.

### 4. Setup Database

- Create a MySQL production database
- Run migrations:
```bash
python manage.py migrate
```

### 5. Collect Static Files
```bash
python manage.py collectstatic
```

### 6. Use Gunicorn as WSGI Server

Install Gunicorn:
```bash
pip install gunicorn
```

Run it (example):
```bash
gunicorn ez_task.wsgi:application --bind 0.0.0.0:8000
```

### 7. Configure Nginx as Reverse Proxy

Edit `/etc/nginx/sites-available/ez_task`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/ez-task/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }
}
```

Then enable the config:
```bash
sudo ln -s /etc/nginx/sites-available/ez_task /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Secure with SSL (Optional but Recommended)

Use Certbot for free HTTPS:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 9. Set Up a Process Manager (e.g., Supervisor or systemd)

Use systemd to keep Gunicorn running:

```bash
sudo nano /etc/systemd/system/ez_task.service
```

```ini
[Unit]
Description=Ez-Task Gunicorn
After=network.target

[Service]
User=youruser
Group=www-data
WorkingDirectory=/path/to/ez-task
ExecStart=/path/to/venv/bin/gunicorn ez_task.wsgi:application --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl start ez_task
sudo systemctl enable ez_task
```

## Final Notes

- Ensure DEBUG=False
- Set proper ALLOWED_HOSTS
- Configure logging & monitoring (e.g. Sentry)
- Regularly back up your .env and database
