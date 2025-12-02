## 🚀 Guia de Instalação e Execução

Este `README.md` fornece as instruções necessárias para configurar o ambiente e executar o script principal da aplicação.

---

### Simplifique usando docker

```bash
docker compose up --build
```

### 📋 Pré-requisitos

Antes de instalar as dependências, você deve garantir que possui o seguinte instalado no seu sistema:

1.  **Python 3.8+**: É a linguagem de programação principal.
2.  **`pip`**: O gerenciador de pacotes do Python.
3.  **FFmpeg**: Uma ferramenta essencial para manipulação de áudio e vídeo, usada pela biblioteca `pydub` e `ffmpeg-python`.

#### 🔧 Instalação do FFmpeg

**O FFmpeg deve ser instalado separadamente** e adicionado ao **PATH** do seu sistema operacional.

* **Windows**:
    * Baixe a versão mais recente em [ffmpeg.org](https://ffmpeg.org/download.html).
    * Extraia e adicione o caminho da pasta `bin` ao seu sistema PATH.
* **macOS (via Homebrew)**:
    ```bash
    brew install ffmpeg
    ```
* **Linux (Debian/Ubuntu)**:
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
* **Linux (Fedora)**:
    ```bash
    sudo dnf install ffmpeg
    ```

---

### 📦 Instalação das Dependências do Python

É altamente recomendado que você use um **ambiente virtual** (`venv`) para isolar as dependências do projeto.

#### 1. Criar e Ativar o Ambiente Virtual

```bash
# Cria o ambiente virtual chamado 'venv'
python -m venv venv

# Ativa o ambiente virtual (Windows)
.\venv\Scripts\activate
# Ativa o ambiente virtual (macOS/Linux)
source venv/bin/activate
```

#### 2. Instalar as Bibliotecas

```bash
pip install streamlit yt-dlp==2024.12.23 numpy pydub openai-whisper torch ffmpeg-python
```

### Execução da Aplicação

```bash
streamlit run criaclipes.py
```