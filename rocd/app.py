"""Início do programa: main() e trava de uma instância só."""

import ctypes
import sys
import tkinter as tk
import traceback
from ctypes import wintypes
from tkinter import messagebox

from .config import FALTANDO, NOME_APP, PASTA, VERSAO, registrar
from .janelas import dpi_aware
from .painel import Painel


def ja_aberto():
    """Evita abrir dois overlays ao mesmo tempo (duplo clique repetido)."""
    try:
        k32 = ctypes.windll.kernel32
        k32.CreateMutexW.restype = wintypes.HANDLE
        ja_aberto._mutex = k32.CreateMutexW(None, False, "RO_Cooldown_Overlay_instancia")
        return k32.GetLastError() == 183          # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def main():
    for nome, erro in FALTANDO.items():
        registrar(f"Biblioteca {nome} não carregou ({erro}): buffs, AP e busca de ícones "
                  "podem não funcionar.")
    if "--verificar-chave" in sys.argv:  # usado ao gerar o .exe: a chave padrão entrou?
        from .chave import chave_padrao
        sys.exit(0 if chave_padrao() else 1)
    if "--verificar" in sys.argv:       # usado ao gerar o .exe: falha se faltar biblioteca
        from .sites import icone_embutido   # ...ou os ícones embutidos (Brisa Leve)
        sys.exit(1 if FALTANDO or not icone_embutido(90) else 0)
    if ja_aberto():
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(NOME_APP, "O programa já está aberto.\n"
                            "Procure a janela dele na barra de tarefas.")
        return
    dpi_aware()
    try:    # barra de tarefas com o ícone do programa (e não o do Python)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ROCooldownOverlay.App")
    except Exception:
        pass
    root = tk.Tk()
    registrar(f"{NOME_APP} v{VERSAO} iniciado (dados em {PASTA})")

    def erro(exc, val, tb):
        texto = "".join(traceback.format_exception(exc, val, tb))
        (PASTA / "erro.log").write_text(texto, encoding="utf-8")
        messagebox.showerror(NOME_APP, f"Ocorreu um erro:\n{val}\n\n"
                             "Os detalhes foram salvos em erro.log "
                             "(botão \"Pasta de dados\").")

    root.report_callback_exception = erro
    try:
        Painel(root)
    except Exception:
        (PASTA / "erro.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    root.mainloop()
