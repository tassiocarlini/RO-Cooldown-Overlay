"""Último local (Last Spot): achar a seta no mini mapa, mesmo mapa ou não, e o teleporte.

minimapa_1/2/3.png: mesmo mapa (1 = parado, 2 = andou, 3 = depois da Asa de Mosca)."""
from pathlib import Path

import numpy as np
from PIL import Image

from rocd.ultimo_local import LIMIAR_MAPA, Rastreio, achar_seta, assinatura, mesmo_mapa

DADOS = Path(__file__).parent / "dados"


def mini(i):
    return np.asarray(Image.open(DADOS / f"minimapa_{i}.png").convert("RGB"))


def test_acha_a_seta():
    # centro (ponto vermelho) medido nos prints
    for i, esperado in ((1, (53, 61)), (2, (84, 58)), (3, (55, 78))):
        x, y = achar_seta(mini(i))
        assert abs(x - esperado[0]) <= 2 and abs(y - esperado[1]) <= 2, (i, x, y)


def test_sem_seta():
    arr = mini(1).copy()
    x, y = (round(v) for v in achar_seta(arr))
    arr[y - 8:y + 9, x - 8:x + 9] = (30, 25, 40)            # mini mapa sem a seta
    assert achar_seta(arr) is None
    assert achar_seta(np.zeros((140, 140, 3), np.uint8)) is None


def test_mancha_branca_sem_ponto_vermelho_nao_e_seta():
    arr = np.full((140, 140, 3), 30, np.uint8)
    arr[50:60, 50:60] = 255                                  # texto / ícone branco
    assert achar_seta(arr) is None


def test_mesmo_mapa():
    s = [assinatura(mini(i)) for i in (1, 2, 3)]
    for a in s:
        for b in s:
            assert mesmo_mapa(a, b) >= LIMIAR_MAPA
    outro = assinatura(np.ascontiguousarray(np.rot90(mini(1))))
    assert mesmo_mapa(s[0], outro) < LIMIAR_MAPA


def test_andar_nao_guarda_e_teleporte_guarda():
    r = Rastreio()
    sig = assinatura(mini(1))
    t = 0.0
    for k in range(20):                                     # andando 0,3 px por leitura
        t += 0.15
        assert not r.ler((50 + 0.3 * k, 60.0), sig, False, t)
    assert r.salvo is None
    assert r.ler((80.0, 20.0), sig, False, t + 0.15)       # Asa de Mosca
    assert r.salvo[0] == (50 + 0.3 * 19, 60.0)


def test_troca_de_mapa_pela_tela_preta():
    r = Rastreio()
    a, outro = assinatura(mini(1)), assinatura(np.ascontiguousarray(np.rot90(mini(1))))
    r.ler((50.0, 60.0), a, False, 0.0)
    r.ler(None, None, True, 1.0)                            # carregando
    assert r.ler((51.0, 60.0), outro, False, 3.0)           # mesmo lugar no mini mapa, outro mapa
    assert r.salvo[0] == (50.0, 60.0)


def test_mini_mapa_fechado_muito_tempo_nao_conta():
    r = Rastreio()
    sig = assinatura(mini(1))
    r.ler((50.0, 60.0), sig, False, 0.0)
    assert not r.ler((90.0, 90.0), sig, False, 30.0)        # fechou o mini mapa e andou
    assert r.salvo is None
