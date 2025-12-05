# Imagem base leve
FROM python:3.10-slim


ENV DEBIAN_FRONTEND=noninteractive


RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    unzip \
    build-essential \
    gcc \
    libgl1 \
    tk \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app


RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu


RUN pip install --no-cache-dir \
    yt-dlp \
    openai-whisper \
    pydub \
    numpy \
    pillow \
    browser_cookie3


RUN pip install --no-cache-dir pyinstaller


COPY . .


RUN mkdir -p videos_baixados legendas videos_recortados videos_finais


CMD ["bash"]
