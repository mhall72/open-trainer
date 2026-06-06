# =============================================================================
# Open-Trainer — Bot image (Hermes + Open-Trainer overlay)
#
# Built on the PINNED upstream Hermes image (see ../agent/hermes.commit). Build
# that base first with ../scripts/build_base.sh (or the cloudbuild step), then:
#
#   docker build -f docker/Dockerfile \
#     --build-arg HERMES_IMAGE=open-trainer/hermes-base:ef7e5168 \
#     -t open-trainer/bot:latest .
#
# We only OVERLAY our customizations onto the canonical Hermes build — we never
# fork its 4,700 files. Hermes discovers bundled skills under /opt/hermes/skills
# and reads cli-config.yaml + SOUL.md from its working dir.
# =============================================================================
ARG HERMES_IMAGE=open-trainer/hermes-base:latest
FROM ${HERMES_IMAGE}

# Hermes image conventions (from upstream Dockerfile):
#   WORKDIR=/opt/hermes  HERMES_HOME=/opt/data  venv=/opt/hermes/.venv
WORKDIR /opt/hermes

# 1) The personal-trainer skill (bundled-skill location → always discovered).
COPY agent/skills/personal-trainer /opt/hermes/skills/personal-trainer

# 2) Agent identity + model + personalities config.
COPY agent/config/SOUL.md            /opt/hermes/SOUL.md
COPY agent/config/cli-config.yaml    /opt/hermes/cli-config.yaml
COPY agent/config/personalities.json /opt/hermes/opentrainer-personalities.json

# 3) Skill runtime dependency (httpx for Supabase REST).
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir "httpx>=0.27,<1.0"

# Cloud Run sets $PORT; Hermes' gateway/dashboard bind there if needed.
ENV OPEN_TRAINER_SUBSCRIBE_URL="https://open-trainer.app"

# Keep upstream's /init (s6) ENTRYPOINT; just select the gateway service, which
# brings up the Telegram platform when TELEGRAM_BOT_TOKEN is set.
CMD ["gateway", "run"]
