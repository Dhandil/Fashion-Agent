FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    HF_HOME=/home/fashion_agent/.cache/huggingface

WORKDIR /app

# RAG 当前固定使用 CPU。该层不依赖项目文件，配置或业务代码变化不会重复下载。
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN python -m pip install "torch>=2.2,<3.0" --index-url "${PYTORCH_CPU_INDEX_URL}"

# 使用当前 pip 解析现代包索引；缓存挂载只存在于 BuildKit，不进入最终镜像。
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 python -m pip install "pip>=26.1,<27.0"

# 依赖层只由项目声明决定；普通业务代码变化不会重新安装第三方包。
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 python -c "import subprocess, tomllib; dependencies = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call(['python', '-m', 'pip', 'install', *dependencies])"

# 最后复制应用并以无依赖模式安装本地包，最大化前面依赖层的缓存复用。
COPY app ./app
RUN python -m pip install . --no-deps

# Alembic 迁移和内存商品样例是运行时需要的非包资源。
COPY alembic.ini ./
COPY migrations ./migrations
COPY data/samples ./data/samples

# 运行进程不使用 root；挂载目录提前创建并交给应用用户。
RUN groupadd --system fashion_agent \
    && useradd --system --gid fashion_agent --create-home fashion_agent \
    && mkdir -p /app/data/chroma /app/data/raw /home/fashion_agent/.cache/huggingface \
    && chown -R fashion_agent:fashion_agent /app /home/fashion_agent

USER fashion_agent

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
