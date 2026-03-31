ARG BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

ARG APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|https\\?://deb.debian.org/debian|${APT_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources && \
      sed -i "s|https\\?://security.debian.org/debian-security|${APT_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i "s|https\\?://deb.debian.org/debian|${APT_MIRROR}/debian|g" /etc/apt/sources.list && \
      sed -i "s|https\\?://security.debian.org/debian-security|${APT_MIRROR}/debian-security|g" /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/data /app/reports /app/logs

ENTRYPOINT ["python3", "main.py"]
CMD ["--help"]
