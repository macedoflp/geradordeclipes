import sys
import os
import uuid
import subprocess
import shutil
import numpy as np
from yt_dlp import YoutubeDL
import whisper
from pydub import AudioSegment
import tkinter as tk
from tkinter import ttk, messagebox


def resource_path(path: str):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.abspath(path)


def ffmpeg_path():
    if hasattr(sys, "_MEIPASS"):
        candidate = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(candidate):
            return candidate

    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    found = shutil.which(exe)
    if found:
        return found

    return exe


def ensure_file_exists(path):
    return path and os.path.exists(path)



PASTAS = {
    "baixados": "videos_baixados",
    "legendas": "legendas",
    "recortes": "videos_recortados",
    "finais": "videos_finais",
}

for p in PASTAS.values():
    os.makedirs(p, exist_ok=True)



def obter_cookies():
    cookies_path = resource_path("cookies.txt")
    return cookies_path if os.path.exists(cookies_path) else None



def detectar_melhor_momento(url, wanted_duration=25):
    try:
        ydl_opts = {"skip_download": True, "extract_flat": False}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        heatmap = info.get("heatmap", None)
        duration = info.get("duration", None)

        if not duration:
            return None, None

        if heatmap:
            melhor = max(heatmap, key=lambda h: h.get("heatMarkerIntensityScoreNormalized", 0))
            start = melhor.get("start", 0)
            end = melhor.get("end", start + wanted_duration)
            meio = (start + end) / 2
            inicio = max(0, int(meio - wanted_duration / 2))
            return inicio, wanted_duration

        return None, None
    except Exception as e:
        raise RuntimeError(f"Erro ao detectar melhor momento: {e}")


def detectar_pico_audio(video_path, wanted_duration=25):
    if not ensure_file_exists(video_path):
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {video_path}")

    audio = AudioSegment.from_file(video_path)
    samples = np.array(audio.get_array_of_samples())
    sample_rate = audio.frame_rate

    if len(samples) == 0 or sample_rate == 0:
        raise RuntimeError("Áudio inválido para detecção de pico.")

    chunk = sample_rate * 1
    energies = [np.mean(samples[i:i + chunk] ** 2) for i in range(0, len(samples), chunk)]
    best_second = int(np.argmax(energies))
    start = max(0, best_second - wanted_duration // 2)

    return start, wanted_duration


def baixar_video(url, cookies):
    try:
        output_name = os.path.join(PASTAS["baixados"], f"video_{uuid.uuid4()}.mp4")

        ydl_opts = {
            "outtmpl": output_name,
            "format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }

        if isinstance(cookies, str):
            ydl_opts["cookiefile"] = cookies

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(output_name):
            raise FileNotFoundError("Download não gerou o arquivo esperado.")

        return output_name
    except Exception as e:
        raise RuntimeError(f"Erro ao baixar vídeo: {e}")


def cortar_video(input_file, start, duration):
    if not ensure_file_exists(input_file):
        raise FileNotFoundError(f"Arquivo de vídeo para corte não encontrado: {input_file}")

    output_file = os.path.join(PASTAS["recortes"], f"recorte_{uuid.uuid4()}.mp4")

    cmd = [
        ffmpeg_path(),
        "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", input_file,
        "-ss", str(start),
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        output_file,
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg falhou ao cortar o vídeo: {e}")

    if not os.path.exists(output_file):
        raise RuntimeError("Corte falhou: arquivo de saída não criado.")

    return output_file


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")


def gerar_srt(video, modelo="small"):
    if not ensure_file_exists(video):
        raise FileNotFoundError(f"Vídeo para gerar SRT não encontrado: {video}")

    try:
        model = whisper.load_model(modelo)
        result = model.transcribe(
            video,
            verbose=False,
            no_progress=True  # <---- AQUI ESTÁ A CORREÇÃO
        )
    except Exception as e:
        raise RuntimeError(f"Erro ao transcrever com Whisper: {e}")

    segments = result.get("segments") or []
    if not segments:
        raise RuntimeError("Transcrição não retornou segmentos (SRT vazio).")

    srt_path = os.path.join(PASTAS["legendas"], f"subs_{uuid.uuid4()}.srt")

    try:
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                texto = seg.get("text", "").strip().replace("\n", " ")
                start_ts = seg.get("start", 0.0)
                end_ts = seg.get("end", start_ts + 1.0)
                f.write(f"{i}\n")
                f.write(f"{format_timestamp(start_ts)} --> {format_timestamp(end_ts)}\n")
                f.write(texto + "\n\n")
    except Exception as e:
        raise RuntimeError(f"Falha ao escrever SRT: {e}")

    if not os.path.exists(srt_path):
        raise RuntimeError("Falha ao criar arquivo SRT.")

    return srt_path



def gerar_video_final(video, srt):
    if not ensure_file_exists(video):
        raise FileNotFoundError(f"Vídeo para finalização não encontrado: {video}")
    if not ensure_file_exists(srt):
        raise FileNotFoundError(f"Arquivo SRT não encontrado: {srt}")

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

    srt_abs = os.path.abspath(srt)

    cmd = [
        ffmpeg_path(),
        "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", video,
        "-vf", f"subtitles='{srt_abs}':force_style='{force_style}'",
        "-c:v", "libx264",
        "-c:a", "aac",
        output,
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg falhou ao gerar vídeo final: {e}")

    if not os.path.exists(output):
        raise RuntimeError("Falha ao gerar vídeo final.")

    return output



def processar():
    url = entrada_url.get().strip()
    inicio = entrada_inicio.get().strip()
    duracao = entrada_duracao.get().strip()

    if not url:
        messagebox.showerror("Erro", "Informe a URL do vídeo.")
        return

    try:
        inicio = int(inicio) if inicio else None
    except ValueError:
        messagebox.showerror("Erro", "Início deve ser um número inteiro.")
        return

    try:
        duracao = int(duracao) if duracao else 25
    except ValueError:
        messagebox.showerror("Erro", "Duração deve ser um número inteiro.")
        return


    ff = ffmpeg_path()
    if not shutil.which(os.path.basename(ff)) and not os.path.exists(ff):
        messagebox.showerror(
            "Erro",
            "ffmpeg não encontrado. Coloque ffmpeg.exe na mesma pasta do .exe ou instale o ffmpeg no PATH."
        )
        return

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
        progresso["value"] = 40
        root.update_idletasks()

        if inicio is None and (s is None):
            s, d = detectar_pico_audio(temp_video, duracao)

        progresso["value"] = 50
        root.update_idletasks()

        recorte = cortar_video(temp_video, s, d)
        progresso["value"] = 65
        root.update_idletasks()

        srt = gerar_srt(recorte)
        progresso["value"] = 85
        root.update_idletasks()

        final_video = gerar_video_final(recorte, srt)
        progresso["value"] = 100
        root.update_idletasks()

        messagebox.showinfo("Sucesso", f"Vídeo final gerado em:\n{final_video}")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        messagebox.showerror("Erro", f"{e}\n\nDetalhes:\n{tb}")



root = tk.Tk()
root.title("Gerador de Clipes YouTube")
root.geometry("540x360")

tk.Label(root, text="URL do vídeo:").pack(anchor="w", padx=10, pady=(8, 0))
entrada_url = tk.Entry(root, width=72)
entrada_url.pack(padx=10, pady=(0, 6))

tk.Label(root, text="Início (segundos, opcional):").pack(anchor="w", padx=10)
entrada_inicio = tk.Entry(root, width=12)
entrada_inicio.pack(padx=10, pady=(0, 6))

tk.Label(root, text="Duração (segundos):").pack(anchor="w", padx=10)
entrada_duracao = tk.Entry(root, width=12)
entrada_duracao.insert(0, "25")
entrada_duracao.pack(padx=10, pady=(0, 6))

ttk.Button(root, text="Processar Vídeo", command=processar).pack(pady=15)

progresso = ttk.Progressbar(root, orient="horizontal", length=450, mode="determinate")
progresso.pack(pady=10)

root.mainloop()
