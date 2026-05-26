# Raw Smith Circle - Hugging Face Spaces (Docker SDK) image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=raw_smith_circle.settings

# Hugging Face Spaces run the container as UID 1000; create a matching user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

# Install Python dependencies first (better layer caching).
COPY --chown=user:user requirements.txt .
RUN pip install --user -r requirements.txt

# Copy the application (includes data/ CSVs and the trained circle/ml/*.joblib).
COPY --chown=user:user . .

# Production runtime settings. ALLOWED_HOSTS uses the wildcard so any
# *.hf.space subdomain is accepted. HF terminates TLS, so Django's own HTTPS
# redirect is disabled to avoid a redirect loop (the Space is still HTTPS-only).
ENV DEBUG=False \
    ALLOWED_HOSTS=.hf.space \
    SECURE_SSL_REDIRECT=False

# Bake the static manifest into the image (SECRET_KEY just needs to exist here).
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

EXPOSE 7860

CMD ["sh", "start.sh"]
