# Use Python 3.11 slim image for better performance
FROM python:3.11-slim

# Argumentos de build
ARG BUILD_DATE=unknown
ARG FORCE_REBUILD=1

# Metadados
LABEL maintainer="Transcritor Automático"
LABEL version="2.0.0"
LABEL description="Aplicação de monitoramento automático de vídeos no Google Drive"
LABEL build-date=$BUILD_DATE

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_DATE=$BUILD_DATE

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro para cache
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/transcriptions /app/downloads /app/temp /app/tasks /app/static

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 