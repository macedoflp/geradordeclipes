# Imagem base leve
FROM python:3.10-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Atualizar e instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    unzip \
 && rm -rf /var/lib/apt/lists/*

# Criar pasta de trabalho
WORKDIR /app

# Instalar dependências Python (Torch CPU primeiro)
RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Dependências do seu projeto
RUN pip install --no-cache-dir \
    yt-dlp \
    openai-whisper \
    pydub \
    streamlit \
    numpy

# Copiar arquivos do projeto
COPY . .

# Criar pastas necessárias (evita erros no runtime)
RUN mkdir -p videos_baixados legendas videos_recortados videos_finais

# Expor porta do Streamlit
EXPOSE 8501

# Streamlit sem pedir browser
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true

# Comando para rodar seu app Streamlit automaticamente
CMD ["streamlit", "run", "criaclipes.py", "--server.address=0.0.0.0"]
