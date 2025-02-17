ARG THORN_HOME_ARG=/usr/local/thorn
FROM python:3.9.21-slim-bullseye AS base

FROM base AS uv_builder
ARG THORN_HOME_ARG
ENV THORN_HOME=$THORN_HOME_ARG \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR $THORN_HOME
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libldap-dev python-dev libsasl2-dev && \
    pip install -U pip wheel uv

# Copy and install dependencies using a cache-mounted directory
COPY pyproject.toml $THORN_HOME/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv lock && \
    uv sync --frozen --no-install-project --no-dev

FROM base
ARG THORN_HOME_ARG
ENV THORN_HOME=$THORN_HOME_ARG
ENV THORN_CONFIG=$THORN_HOME/conf/thorn-config.yaml \
    PATH="$THORN_HOME/.venv/bin:$PATH" \
    FLASK_APP=thorn.app

# Install dumb-init for better signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init libldap-common libldap-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . $THORN_HOME/
COPY --from=uv_builder $THORN_HOME/.venv $THORN_HOME/.venv

WORKDIR $THORN_HOME
COPY bin/entrypoint /usr/local/bin/
RUN pybabel compile -d thorn/i18n/locales

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/entrypoint"]
CMD ["server"]
