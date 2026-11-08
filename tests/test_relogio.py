"""Relógio do ícone de buff: recortes reais do Estimulante (30 min) tirados no jogo."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from rocd.overlay import Overlay
from rocd.relogio import arte_do_icone, fracao_passada, inicio_estimado

DADOS = Path(__file__).parent / "dados"
DUR = 1800


@pytest.mark.parametrize("seg", [7, 183, 232, 412])     # 232 s: fundo escuro do mapa
def test_fracao_em_recortes_reais(seg):
    arte = arte_do_icone(Image.open(DADOS / "relogio_estimulante_icone.png"))
    ic = np.asarray(Image.open(DADOS / f"relogio_estimulante_{seg}s.png").convert("RGB"))
    frac, _forca = fracao_passada(ic, arte)
    assert abs(frac - seg / DUR) <= 0.025                # até 45 s de erro em 30 min


def test_icone_liso_nao_tem_borda():
    assert fracao_passada(np.full((32, 32, 3), 90, np.uint8)) is None


def test_inicio_estimado_precisa_de_leituras_que_concordam():
    assert inicio_estimado([(100, 0.1), (101, 0.1)], DUR, 30) is None
    assert inicio_estimado([(100, 0.1), (101, 0.1), (102, 0.1)], DUR, 30) == pytest.approx(-79)
    assert inicio_estimado([(100, 0.1), (101, 0.5), (102, 0.1)], DUR, 30) is None


def buff_ativo(desde):
    return {"_desde": desde, "_avisou": True, "_relogio": []}


def test_buff_que_ja_estava_ativo_ganha_o_comeco_certo():
    ov = SimpleNamespace()
    b = buff_ativo(1000.0)                                # programa viu agora, mas já tinha 10 min
    for t in (1000.0, 1000.3, 1000.6):
        Overlay._acertar_pelo_relogio(ov, b, t, (600 / DUR, 50.0), DUR)
    assert b["_desde"] == pytest.approx(400.3, abs=1)
    assert b["_avisou"] is True                           # não mexe no aviso


def test_buff_renovado_volta_a_contar_e_a_avisar():
    ov = SimpleNamespace()
    b = buff_ativo(0.0)
    for t in (900.0, 900.3, 900.6):                       # renovou aos 15 min: véu no começo
        Overlay._acertar_pelo_relogio(ov, b, t, (0.0, 50.0), DUR)
    assert b["_desde"] == pytest.approx(900.3, abs=1)
    assert b["_avisou"] is False


def test_leitura_repetida_ou_sem_borda_nao_conta():
    ov = SimpleNamespace()
    b = buff_ativo(0.0)
    for _ in range(5):
        Overlay._acertar_pelo_relogio(ov, b, 900.0, (0.0, 50.0), DUR)   # mesma leitura
        Overlay._acertar_pelo_relogio(ov, b, 901.0, None, DUR)
    assert b["_desde"] == 0.0
