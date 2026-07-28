# Imagem do programa para rodar no Google Cloud Run (Linux).
# Localmente você continua usando `python app.py` — este arquivo é só p/ a nuvem.
FROM python:3.12-slim

# matplotlib precisa de uma pasta de config gravável; /tmp serve no container
ENV MPLCONFIGDIR=/tmp/mpl \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# dependências primeiro (aproveita o cache do build quando o código muda)
COPY requirements.txt .
RUN pip install -r requirements.txt

# o código e os assets (fontes, layout, cartões) — tudo somente-leitura no container
COPY . .

# os dados mutáveis (config editável, clientes/, token do Drive) ficam FORA da
# imagem, num bucket montado em /data (ver instruções de deploy)
ENV S2V_DATA_DIR=/data

# o Cloud Run injeta a porta em $PORT (8080). gunicorn serve o app Flask.
# 1 worker + threads: gera PDF sem estourar memória; timeout folgado p/ o PDF.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 4 \
    --timeout 120 app:app
