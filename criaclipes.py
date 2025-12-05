import os
import uuid
import subprocess
import numpy as np
from yt_dlp import YoutubeDL
import whisper
from pydub import AudioSegment
import tkinter as tk
from tkinter import ttk, messagebox


PASTAS = {
    "baixados": "videos_baixados",
    "legendas": "legendas",
    "recortes": "videos_recortados",
    "finais": "videos_finais",
}

for p in PASTAS.values():
    os.makedirs(p, exist_ok=True)




def obter_cookies():
    """Retorna o arquivo de cookies, se existir."""
    cookies_path = "cookies.txt"
    return cookies_path if os.path.exists(cookies_path) else None


def detectar_melhor_momento(url, wanted_duration=25):
    ydl_opts = {"skip_download": True, "extract_flat": False}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    heatmap = info.get("heatmap", None)
    duration = info.get("duration", None)

    if not duration:
        return None, None

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
    energies = [np.mean(samples[i:i + chunk] ** 2) for i in range(0, len(samples), chunk)]
    best_second = int(np.argmax(energies))
    start = max(0, best_second - wanted_duration // 2)

    return start, wanted_duration


def baixar_video(url, cookies):
    output_name = os.path.join(PASTAS["baixados"], f"video_{uuid.uuid4()}.mp4")
    ydl_opts = {
        "outtmpl": output_name,
        "format": "mp4",
    }

    if isinstance(cookies, str):
        ydl_opts["cookiefile"] = cookies

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_name


def cortar_video(input_file, start, duration):
    output_file = os.path.join(PASTAS["recortes"], f"recorte_{uuid.uuid4()}.mp4")

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

    srt_path = os.path.join(PASTAS["legendas"], f"subs_{uuid.uuid4()}.srt")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], start=1):
            texto = seg["text"].strip().replace("\n", " ")
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")
            f.write(texto + "\n\n")

    return srt_path


def gerar_video_final(video, srt):
    output = os.path.join(PASTAS["finais"], f"final_{uuid.uuid4()}.mp4")

    force_style = (
        "FontName=Anton,"
        "FontSize=20,"
        "PrimaryColour=&HFFFFFF,"
        "OutlineColour=&H000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "WrapStyle=0"
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




def processar():
    url = entrada_url.get().strip()
    inicio = entrada_inicio.get().strip()
    duracao = entrada_duracao.get().strip()

    if not url:
        messagebox.showerror("Erro", "Informe a URL do vídeo.")
        return

    inicio = int(inicio) if inicio else None
    duracao = int(duracao) if duracao else 25

    try:
        progresso["value"] = 5
        root.update_idletasks()

        cookies = obter_cookies()

        progresso["value"] = 10
        root.update_idletasks()

        if inicio is None:
            s, d = detectar_melhor_momento(url, duracao)
        else:
            s, d = inicio, duracao

        progresso["value"] = 25
        root.update_idletasks()

        temp_video = baixar_video(url, cookies)

        if inicio is None and s is None:
            s, d = detectar_pico_audio(temp_video, duracao)

        progresso["value"] = 40
        root.update_idletasks()

        recorte = cortar_video(temp_video, s, d)

        progresso["value"] = 60
        root.update_idletasks()

        srt = gerar_srt(recorte)

        progresso["value"] = 80
        root.update_idletasks()

        final_video = gerar_video_final(recorte, srt)

        progresso["value"] = 100
        root.update_idletasks()

        messagebox.showinfo("Sucesso", f"Vídeo final gerado em:\n{final_video}")

    except Exception as e:
        messagebox.showerror("Erro", str(e))



root = tk.Tk()
root.title("Gerador de Clipes YouTube")
root.geometry("450x300")

tk.Label(root, text="URL do vídeo:").pack(anchor="w", padx=10)
entrada_url = tk.Entry(root, width=60)
entrada_url.pack(padx=10)

tk.Label(root, text="Início (segundos, opcional):").pack(anchor="w", padx=10)
entrada_inicio = tk.Entry(root, width=10)
entrada_inicio.pack(padx=10)

tk.Label(root, text="Duração (segundos):").pack(anchor="w", padx=10)
entrada_duracao = tk.Entry(root, width=10)
entrada_duracao.insert(0, "25")
entrada_duracao.pack(padx=10)

ttk.Button(root, text="Processar Vídeo", command=processar).pack(pady=15)

progresso = ttk.Progressbar(root, orient="horizontal", length=350, mode="determinate")
progresso.pack(pady=10)

root.mainloop()
