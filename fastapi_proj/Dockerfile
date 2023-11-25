FROM python:3.11.6-slim-bookworm

# Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ARG USERNAME=wargoth
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update -y \
  && apt-get install -y postgresql gcc --no-install-recommends \
  && groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && passwd -l root \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /var/cache/apt/*

# Poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

RUN python -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry

ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /home/$USERNAME/app

# Copy project files
COPY pyproject.toml poetry.lock ./

# Install packages
# [OPTIONAL] Validate the project is properly configured
RUN poetry install --no-interaction \
                    --no-cache \
                    --no-root

# Copy project files
COPY . .

# Permissions
RUN chown -R $USER_UID:$USER_GID /home/$USERNAME \
  && chmod 777 /home/$USERNAME 

# Init user
USER $USERNAME

# WORKDIR /home/$USERNAME/app
