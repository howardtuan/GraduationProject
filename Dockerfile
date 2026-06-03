FROM python:3.10-slim

# Keep Python logs visible in Docker and avoid writing bytecode into the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DJANGO_DEBUG=False \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0 \
    DJANGO_SECURE_SSL_REDIRECT=False \
    DJANGO_SESSION_COOKIE_SECURE=False \
    DJANGO_CSRF_COOKIE_SECURE=False \
    DJANGO_SECURE_HSTS_SECONDS=0 \
    DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False \
    DJANGO_SECURE_HSTS_PRELOAD=False \
    SQLITE_DATABASE_PATH=/app/data/db.sqlite3

WORKDIR /app

# Install Python dependencies first so Docker can cache this layer.
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Copy the Django project after dependencies to keep rebuilds fast.
COPY . /app

# Static files are collected at build time and served by Whitenoise in the app.
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && chmod +x /app/docker/entrypoint.sh \
    && python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "talk2draw_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
