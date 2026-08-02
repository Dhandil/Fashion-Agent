FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    HF_HOME=/home/fashion_agent/.cache/huggingface

WORKDIR /app

# 先复制依赖声明和应用包，使业务外文件变化不会破坏依赖安装缓存。
COPY pyproject.toml README.md ./
COPY app ./app

# RAG 当前固定使用 CPU；先安装 CPU 版 PyTorch，避免拉取体积巨大的 CUDA 运行库。
ARG PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN python -m pip install "torch>=2.2,<3.0" --index-url "${PYTORCH_CPU_INDEX_URL}" \
    && python -m pip install .

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
