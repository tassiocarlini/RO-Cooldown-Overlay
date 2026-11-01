"""Tela preta (teleporte / troca de mapa): os buffs não podem "acabar" nessa hora."""
import numpy as np

from rocd.visao import tela_escura


def test_tela_preta():
    assert tela_escura(np.zeros((600, 800, 3), np.uint8))


def test_tela_preta_com_ruido():
    arr = np.full((600, 800, 3), 12, np.uint8)
    arr[::50, ::50] = 255                        # poucos pontos claros (cursor, partícula)
    assert tela_escura(arr)


def test_mapa_escuro_com_interface_nao_e_tela_preta():
    arr = np.full((600, 800, 3), 20, np.uint8)
    arr[540:, :] = (90, 110, 160)                 # barra de atalhos / chat
    arr[:120, 680:] = (200, 200, 200)             # minimapa
    assert not tela_escura(arr)
