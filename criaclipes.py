import os
import uuid
import subprocess
import argparse
import tempfile
import browser_cookie3
import numpy as np

from yt_dlp import YoutubeDL
import whisper
from pydub import AudioSegment

# ==========================================
# 1️⃣ CARREGAR COOKIES
# ==========================================

def obter_cookies():
    cookies_path = "cookies.txt"
    
    if os.path.exists(cookies_path):
        print("🍪 Carregando cookies do arquivo...")
        print(f"✅ Cookies carregados: {cookies_path}")
        return cookies_path
    else:
        print("⚠️ cookies.txt não encontrado. Tentando cookies do navegador...")
        try:
            print("🍪 Carregando cookies do Chrome...")
            cj = browser_cookie3.chrome(domain_name=".youtube.com")
            return cj
        except:
            try:
                print("🍪 Chrome não encontrado. Tentando Firefox...")
                cj = browser_cookie3.firefox(domain_name=".youtube.com")
                return cj
            except:
                print("⚠️ Nenhum cookie carregado. YouTube pode bloquear o download.")
                return None


# ==========================================
# 2️⃣ PEGAR MELHOR MOMENTO (HEATMAP)
# ==========================================

def detectar_melhor_momento(url, wanted_duration=25):
    print("🔎 Analisando vídeo para detectar melhor momento...")

    ydl_opts = {
        "skip_download": True,
        "extract_flat": False
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    heatmap = info.get("heatmap", None)
    duration = info.get("duration", None)

    if not duration:
        print("⚠️ Não consegui pegar a duração do vídeo.")
        return None, None

    # ------------------------
    # 1) Se tiver heatmap → usar trecho mais assistido
    # ------------------------
    if heatmap:
        print("🔥 Heatmap encontrado! Selecionando trecho mais assistido...")

        melhor = max(heatmap, key=lambda h: h["heatMarkerIntensityScoreNormalized"])
        start = melhor["start"]
        end = melhor["end"]

        # ajusta para 25s centralizados
        meio = (start + end) / 2
        inicio = max(0, int(meio - wanted_duration / 2))

        print(f"🎯 Melhor momento detectado pelo YouTube: {inicio}s")
        return inicio, wanted_duration

    print("⚠️ Heatmap não encontrado. Usando fallback de áudio...")

    return None, None


# ==========================================
# 3️⃣ FALLBACK: ANALISAR ÁUDIO (Picos)
# ==========================================

def detectar_pico_audio(video_path, wanted_duration=25):
    print("🎧 Analisando áudio para detectar trecho mais interessante...")

    audio = AudioSegment.from_file(video_path)
    samples = np.array(audio.get_array_of_samples())
    
    # janela de 1 segundo
    sample_rate = audio.frame_rate
    chunk = sample_rate * 1

    energies = []
    for i in range(0, len(samples), chunk):
        energies.append(np.mean(samples[i:i+chunk]**2))

    energies = np.array(energies)

    best_second = int(np.argmax(energies))
    start = max(0, best_second - wanted_duration // 2)

    print(f"🎯 Melhor momento por áudio detectado: {start}s")
    return start, wanted_duration


# ==========================================
# 4️⃣ BAIXAR VÍDEO DO YOUTUBE
# ==========================================

def baixar_video(url, cookies):
    output_name = f"video_{uuid.uuid4()}.mp4"

    ydl_opts = {
        "outtmpl": output_name,
        "format": "mp4",
    }

    if isinstance(cookies, str):
        ydl_opts["cookiefile"] = cookies
    elif cookies is not None:
        ydl_opts["cookiesfrombrowser"] = ("chrome",)

    print("📥 Baixando vídeo...")

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print(f"✅ Vídeo salvo como: {output_name}")
    return output_name


# ==========================================
# 5️⃣ CORTAR TRECHO
# ==========================================

def cortar_video(input_file, start, duration):
    output_file = f"recorte_{uuid.uuid4()}.mp4"

    print(f"✂️ Cortando trecho {start}s → {start+duration}s...")

    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", input_file,
        "-t", str(duration),
        "-c", "copy",
        output_file,
        "-y",
    ]

    subprocess.run(cmd, check=True)
    return output_file


# ==========================================
# 6️⃣ TRANSCRIÇÃO (WHISPER)
# ==========================================

def gerar_srt(video, modelo="small"):
    print("📝 Transcrevendo...")

    model = whisper.load_model(modelo)
    result = model.transcribe(video)

    srt_path = f"subs_{uuid.uuid4()}.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        write_srt(result["segments"], file=f)

    print(f"💬 Legendas geradas: {srt_path}")
    return srt_path


def write_srt(segments, file):
    for i, segment in enumerate(segments, start=1):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()

        file.write(f"{i}\n")
        file.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
        file.write(text + "\n\n")


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")


# ==========================================
# 7️⃣ GERAR VÍDEO FINAL
# ==========================================

def gerar_video_final(video, srt):
    output = f"final_{uuid.uuid4()}.mp4"

    print("🎬 Gerando vídeo final...")

    force_style = (
        "FontName=Anton,"
        "FontSize=20,"
        "PrimaryColour=&HFFFFFF,"      # Cor branca
        "OutlineColour=&H000000,"      # Contorno preto
        "BorderStyle=1,"
        "Outline=2,"                   # Largura do contorno
        "Shadow=1"                     # Sombra leve
    )

    cmd = [
        "ffmpeg",
        "-i", video,
        "-vf", f"subtitles={srt}:force_style='{force_style}'",
        "-c:a", "copy",
        output,
        "-y"
    ]

    subprocess.run(cmd, check=True)

    print(f"✨ Vídeo final criado: {output}")
    return output


# ==========================================
# 8️⃣ MAIN
# ==========================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL do vídeo do YouTube")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--duration", type=int, default=25)
    parser.add_argument("--model", type=str, default="small")
    args = parser.parse_args()

    cookies = obter_cookies()

    # se usuário não passou start → usamos autodetecção
    if args.start is None:
        start, dur = detectar_melhor_momento(args.url, args.duration)

        if start is None:
            print("🔄 Usando fallback de áudio...")
            temp_video = baixar_video(args.url, cookies)
            start, dur = detectar_pico_audio(temp_video, args.duration)
        else:
            temp_video = baixar_video(args.url, cookies)

    else:
        temp_video = baixar_video(args.url, cookies)
        start, dur = args.start, args.duration

    recorte = cortar_video(temp_video, start, dur)
    srt = gerar_srt(recorte, args.model)
    gerar_video_final(recorte, srt)


if __name__ == "__main__":
    main()
