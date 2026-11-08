"""Barra de AP: o lugar do rótulo "AP" não se perde por causa de um quadro ruim."""
from types import SimpleNamespace

import numpy as np

from rocd import overlay as mod
from rocd.overlay import AP_FALHAS_ROTULO, Overlay


def fake(monkeypatch, rotulo_visivel):
    """Overlay mínimo: rótulo guardado em (100, 50); `rotulo_visivel()` diz se ele aparece."""
    ov = Overlay.__new__(Overlay)
    ov.perfil, ov.geo = {"layout": {"mostrar_ap": True}}, None
    ov.sct = SimpleNamespace(grab=lambda c: SimpleNamespace(
        size=(c["width"], c["height"]), rgb=bytes(c["width"] * c["height"] * 3)))
    ov._ap_rotulo = (100, 50)
    buscas = []
    ov._buscar_ap = lambda agora: buscas.append(agora)
    monkeypatch.setattr(mod, "achar_rotulo_ap", lambda arr: (2, 3) if rotulo_visivel() else None)
    monkeypatch.setattr(mod, "ler_fracao", lambda arr: (80, 200))
    monkeypatch.setattr(mod, "np", np)
    return ov, buscas


def test_um_quadro_sem_rotulo_nao_perde_o_lugar(monkeypatch):
    vis = iter([False, True, True])
    ov, buscas = fake(monkeypatch, lambda: next(vis))
    for t in (1, 2, 3):
        ov._ler_ap(float(t))
    assert ov._ap_rotulo == (100, 50) and not buscas
    assert ov.ap == (80, 200)                     # leu de novo depois do quadro ruim


def test_varios_quadros_sem_rotulo_procuram_e_lembram_o_lugar(monkeypatch):
    ov, buscas = fake(monkeypatch, lambda: False)
    for t in range(AP_FALHAS_ROTULO):
        ov._ler_ap(float(t + 1))
    assert ov._ap_rotulo is None and len(buscas) == 1
    ov._fila_ap = mod.queue.Queue()
    ov._fila_ap.put(None)                         # a busca na tela toda não achou nada
    ov._receber_busca_ap()
    assert ov._ap_rotulo == (100, 50)             # volta a testar o lugar antigo
