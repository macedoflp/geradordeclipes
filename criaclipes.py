import os
import uuid
import subprocess
import browser_cookie3
import numpy as np
from yt_dlp import YoutubeDL
import whisper
from pydub import AudioSegment
import streamlit as st
import time



def obter_cookies():
    cookies_path = "cookies.txt"
    if os.path.exists(cookies_path):
        return cookies_path
    else:
        try:
            return browser_cookie3.chrome(domain_name=".youtube.com")
        except:
            try:
                return browser_cookie3.firefox(domain_name=".youtube.com")
            except:
                return None

def detectar_melhor_momento(url, wanted_duration=25):
    ydl_opts = {"skip_download": True, "extract_flat": False}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    heatmap = info.get("heatmap", None)
    duration = info.get("duration", None)
    if not duration: return None, None
    if heatmap:
        melhor = max(heatmap, key=lambda h: h["heatMarkerIntensityScoreNormalized"])
        start = melhor["start"]
        end = melhor["end"]
        meio = (start + end) / 2
        inicio = max(0, int(meio - wanted_duration / 2))
        return inicio, wanted_duration
    return None, None

def detectar_pico_audio(video_path, wanted_duration=25):
    audio = AudioSegment.from_file(video_path)
    samples = np.array(audio.get_array_of_samples())
    sample_rate = audio.frame_rate
    chunk = sample_rate * 1
    energies = [np.mean(samples[i:i+chunk]**2) for i in range(0, len(samples), chunk)]
    best_second = int(np.argmax(energies))
    start = max(0, best_second - wanted_duration // 2)
    return start, wanted_duration

def baixar_video(url, cookies):
    output_name = f"video_{uuid.uuid4()}.mp4"
    ydl_opts = {"outtmpl": output_name, "format": "mp4"}
    if isinstance(cookies, str):
        ydl_opts["cookiefile"] = cookies
    elif cookies is not None:
        ydl_opts["cookiesfrombrowser"] = ("chrome",)
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_name


def cortar_video(input_file, start, duration):
    output_file = f"recorte_{uuid.uuid4()}.mp4"
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-ss", str(start),
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        output_file,
        "-y"
    ]
    subprocess.run(cmd, check=True)
    return output_file


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

def gerar_srt(video, modelo="small"):
    model = whisper.load_model(modelo)
    result = model.transcribe(video)
    srt_path = f"subs_{uuid.uuid4()}.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], start=1):
            texto = seg["text"].strip().replace("\n", " ")
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")
            f.write(texto + "\n\n")
    return srt_path



def gerar_video_final(video, srt):
    output = f"final_{uuid.uuid4()}.mp4"
    force_style = (
        "FontName=Anton,"
        "FontSize=20,"
        "PrimaryColour=&HFFFFFF,"
        "OutlineColour=&H000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "WrapStyle=0"  # <- força apenas uma linha
    )
    cmd = [
        "ffmpeg",
        "-i", video,
        "-vf", f"subtitles={srt}:force_style='{force_style}'",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        output,
        "-y"
    ]
    subprocess.run(cmd, check=True)
    return output

st.title("🎬 Gerador de Clipes YouTube")
url = st.text_input("URL do vídeo")
start_input = st.text_input("Início (s, opcional)")
duration_input = st.text_input("Duração (s, padrão 25)")

if st.button("Processar Vídeo"):
    if not url.strip():
        st.error("❌ Informe a URL do vídeo")
    else:
        start_val = int(start_input) if start_input.strip() else None
        duration_val = int(duration_input) if duration_input.strip() else 25

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            progress_bar.progress(5)
            status_text.text("🍪 Carregando cookies...")
            cookies = obter_cookies()
            time.sleep(1)

            progress_bar.progress(10)
            status_text.text("🔎 Detectando melhor momento...")
            if start_val is None:
                s, d = detectar_melhor_momento(url, duration_val)
            else:
                s, d = start_val, duration_val
            time.sleep(1)
            progress_bar.progress(20)

            status_text.text("📥 Baixando vídeo...")
            temp_video = baixar_video(url, cookies)
            progress_bar.progress(40)
            time.sleep(1)

            if start_val is None and s is None:
                status_text.text("🎧 Detectando pico de áudio...")
                s, d = detectar_pico_audio(temp_video, duration_val)
                progress_bar.progress(50)
                time.sleep(1)

            status_text.text("✂️ Cortando vídeo...")
            recorte = cortar_video(temp_video, s, d)
            progress_bar.progress(60)
            time.sleep(1)

            status_text.text("📝 Gerando legendas...")
            srt = gerar_srt(recorte)
            progress_bar.progress(80)
            time.sleep(1)

            status_text.text("🎬 Gerando vídeo final...")
            final_video = gerar_video_final(recorte, srt)
            progress_bar.progress(100)
            status_text.text("✅ Vídeo finalizado!")

            st.success("🎉 Vídeo processado com sucesso!")
            st.video(final_video)


            with open(final_video, "rb") as f:
                st.download_button(
                    label="📥 Baixar vídeo final",
                    data=f,
                    file_name="video_final.mp4",
                    mime="video/mp4"
                )

        except Exception as e:
            st.error(f"❌ Ocorreu um erro: {e}")
