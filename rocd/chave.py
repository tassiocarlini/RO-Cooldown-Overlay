"""Chave padrão da Divine Pride (a do aplicativo).

Ela NÃO fica no código público: o empacotar.py gera o rocd/_chave.py (fora do git) a partir
do segredo DP_CHAVE_PADRAO do GitHub, só na hora de montar o .exe. Lá ela fica embaralhada,
para não aparecer como texto no programa. Quem puser a própria chave na aba Avançado usa a
sua no lugar desta.
"""

import os


def esconder(chave):
    """Texto do módulo _chave.py com a chave embaralhada (máscara aleatória a cada geração)."""
    dados = chave.strip().encode("utf-8")
    mascara = os.urandom(len(dados))
    misturado = bytes(a ^ b for a, b in zip(dados, mascara))
    return ("# Gerado pelo empacotar.py. Não enviar ao GitHub.\n"
            f"M = {list(mascara)!r}\nD = {list(misturado)!r}\n")


def revelar(mascara, misturado):
    return bytes(a ^ b for a, b in zip(misturado, mascara)).decode("utf-8")


def chave_padrao():
    """A chave do aplicativo, ou "" quando o programa foi montado sem ela (versão em Python)."""
    try:
        from . import _chave
    except ImportError:
        return ""
    try:
        return revelar(_chave.M, _chave.D)
    except Exception:
        return ""
