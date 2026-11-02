"""Leitura do número de AP."""
from pathlib import Path

import numpy as np
from PIL import Image

from rocd.ap import FONTE_DIGITOS, FONTE_DIGITOS_BARRA, ROTULO_AP, ler_fracao, localizar_ap

DADOS = Path(__file__).parent / "dados"


def desenhar(arr, x, y, desenho):
    for dy, linha in enumerate(desenho):
        for dx, c in enumerate(linha):
            if c == "#":
                arr[y + dy, x + dx] = 0


def escrever(arr, x, y, texto, fonte=FONTE_DIGITOS):
    for c in texto:
        if c == " ":
            x += 4
            continue
        desenhar(arr, x, y, fonte[c])
        x += len(fonte[c][0]) + 1
    return x


def test_recorte_real_com_4_colado():
    """Print do jogo (v1.0.24): o 4 da fonte da barra encosta no dígito seguinte."""
    arr = np.asarray(Image.open(DADOS / "ap_140_200.png").convert("RGB"))
    assert ler_fracao(arr) == (140, 200)


def test_numero_desenhado():
    arr = np.full((14, 120, 3), 230, np.uint8)
    escrever(arr, 5, 3, "53 / 200")
    assert ler_fracao(arr) == (53, 200)


def test_localizar_ap_pelo_rotulo():
    arr = np.full((120, 400, 3), 230, np.uint8)
    x, y = 30, 50
    desenhar(arr, x, y, ROTULO_AP)
    escrever(arr, x + 60, y, "77 / 150")
    assert localizar_ap(arr) == ((x, y), (77, 150))


def test_sem_numero():
    assert ler_fracao(np.full((14, 120, 3), 230, np.uint8)) is None


def test_recorte_real_borda_preta_do_preenchimento():
    """Prints do jogo (v1.0.32): em algumas skins o preenchimento verde da barra tem borda preta
    (linha de baixo e coluna da ponta) que passa por cima dos números. Antes lia 7 em vez de 67."""
    for nome, esperado in (("ap_67_200_borda", (67, 200)), ("ap_73_200_borda", (73, 200)),
                           ("ap_200_200_borda", (200, 200))):
        arr = np.asarray(Image.open(DADOS / f"{nome}.png").convert("RGB"))
        assert ler_fracao(arr) == esperado, nome


def barra_com_borda(atual, maximo, desloc=0, largura=150):
    arr = np.full((15, 190, 3), 0xE7, np.uint8)
    arr[2, 14:14 + largura] = 8
    arr[2:11, 14] = 0
    ponta = 14 + round(atual / maximo * largura)
    if ponta > 14:
        arr[3:10, 15:ponta] = (0xCE, 0xFF, 0xC6)
        arr[10, 14:ponta + 1] = 0
        arr[3:11, ponta] = 0
    escrever(arr, 14 + largura // 2 - 18 + desloc, 4, f"{atual} / {maximo}", FONTE_DIGITOS_BARRA)
    return arr


def test_borda_do_preenchimento_em_toda_posicao():
    """A ponta do preenchimento passa por cima de cada coluna do texto: nunca lê errado."""
    for desloc in (-3, 0, 2):
        for atual in range(60, 141):
            assert ler_fracao(barra_com_borda(atual, 200, desloc)) == (atual, 200), (desloc, atual)
