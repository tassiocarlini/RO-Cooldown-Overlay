"""Tempo automático dos buffs (BETA): duração medida pela velocidade do véu do ícone."""
import math
from types import SimpleNamespace

import pytest

from rocd.overlay import Overlay
from rocd.relogio import RelogioAuto


def veu(t, inicio, dur):
    """O que o leitor do ícone devolve: graus inteiros, com um erro que muda com o ângulo
    (até uns 5 graus, como nos recortes reais) e 0 enquanto o véu é pequeno demais."""
    graus = (t - inicio) / dur * 360
    graus += 5 * math.sin(math.radians(graus) * 3)
    return 0.0 if graus <= 10 else min(359, round(graus)) / 360


def rodar(ra, inicio, dur, de, ate, passo=0.3):
    renovou, t = False, de
    while t < ate:
        renovou |= ra.ler(t, veu(t, inicio, dur))
        t += passo
    return renovou


@pytest.mark.parametrize("dur", [20, 120, 300, 1800])
def test_mede_a_duracao_de_buff_visto_do_comeco(dur):
    ra = RelogioAuto(1000.0, True)
    assert ra.duracao is None                            # sem palpite: nada para mostrar ainda
    rodar(ra, 1000.0, dur, 1000.0, 1000.0 + dur * 0.25)
    assert ra.aprox and ra.duracao == pytest.approx(dur, rel=0.12)
    rodar(ra, 1000.0, dur, 1000.0 + dur * 0.25, 1000.0 + dur * 0.9)
    assert ra.duracao == pytest.approx(dur, rel=0.03)
    assert ra.inicio == 1000.0
    assert ra.duracao_vista(1000.0 + dur) == dur         # viu do começo ao fim: exata


def test_buff_que_ja_estava_ativo_e_medido_sem_ver_o_comeco():
    ra = RelogioAuto(5000.0, False)                      # programa abriu com 30% do buff passado
    rodar(ra, 5000.0 - 90, 300, 5000.0, 5000.0 + 150)
    assert ra.duracao == pytest.approx(300, rel=0.08)
    assert ra.inicio == pytest.approx(5000.0 - 90, abs=15)
    assert ra.duracao_vista(5210.0) is None              # não viu começar: não guarda


def test_apareceu_com_o_veu_andado_nao_vale_como_comeco():
    ra = RelogioAuto(5000.0, True)                       # ícone estava coberto e voltou
    rodar(ra, 5000.0 - 150, 300, 5000.0, 5000.0 + 100)
    assert ra.ancora is None
    assert ra.duracao == pytest.approx(300, rel=0.1)


def test_duracao_ja_vista_vira_o_tempo_exato():
    ra = RelogioAuto(0.0, True, [None, 180.0, 300.0])
    assert ra.duracao == 300.0                           # palpite: a última vista
    rodar(ra, 0.0, 180, 0.0, 60.0)                       # desta vez veio em outro nível
    assert ra.duracao == 180.0 and not ra.aprox


def test_nivel_novo_nao_gruda_em_duracao_vista():
    ra = RelogioAuto(0.0, True, [300.0])
    rodar(ra, 0.0, 120, 0.0, 100.0)
    assert ra.aprox and ra.duracao == pytest.approx(120, rel=0.04)


def test_renovado_com_outro_nivel_mede_de_novo():
    ra = RelogioAuto(0.0, True)
    rodar(ra, 0.0, 300, 0.0, 200.0)
    assert rodar(ra, 200.0, 120, 200.0, 290.0)           # renovou aos 200 s, agora 2 min
    assert ra.inicio == pytest.approx(200.0, abs=1)
    assert ra.duracao == pytest.approx(120, rel=0.05)


def test_leitura_torta_sozinha_nao_renova():
    ra = RelogioAuto(0.0, True)
    rodar(ra, 0.0, 300, 0.0, 150.0)
    antes = ra.duracao
    assert ra.ler(150.3, 0.0) is False and ra.ler(150.6, 0.9) is False
    assert not rodar(ra, 0.0, 300, 150.9, 200.0)
    assert ra.duracao == pytest.approx(antes, rel=0.03)


def test_buff_removido_antes_do_fim_nao_e_guardado():
    ra = RelogioAuto(0.0, True)
    rodar(ra, 0.0, 300, 0.0, 120.0)
    assert ra.duracao_vista(120.0) is None


def test_morrer_perto_do_fim_nao_guarda_duracao_errada():
    ra = RelogioAuto(0.0, True)
    rodar(ra, 0.0, 300, 0.0, 270.0)                      # morreu com 90% do buff
    assert ra.duracao_vista(270.0) is None


def test_perder_o_buff_no_finzinho_nao_estraga_a_duracao_ja_vista():
    ov = SimpleNamespace(painel=SimpleNamespace(salvar_depois=lambda: None))
    ra = RelogioAuto(0.0, True, [300.0])
    rodar(ra, 0.0, 300, 0.0, 294.0)
    b = {"_auto": ra, "_visto_real": 294.0, "duracoes_vistas": [120.0, 300.0]}
    Overlay._guardar_duracao_vista(ov, b)
    assert b["duracoes_vistas"] == [120.0, 300.0]


def test_overlay_usa_a_medida_e_guarda_a_duracao_no_fim():
    salvou = []
    ov = SimpleNamespace(painel=SimpleNamespace(salvar_depois=lambda: salvou.append(1)))
    b = {"auto": True, "_desde": 0.0, "_viu_sem": True, "_avisou": True}
    assert Overlay._tempo_automatico(ov, b, None, None) is None      # ainda sem leitura
    t = 0.0
    while t < 115:
        dur = Overlay._tempo_automatico(ov, b, (0.9, t, 0, None, (veu(t, 0.0, 120), 50.0)), None)
        t += 0.3
    assert dur == pytest.approx(120, rel=0.03) and b["_desde"] == 0.0
    b["_visto_real"] = 120.0
    Overlay._guardar_duracao_vista(ov, b)
    assert b["duracoes_vistas"] == [120.0] and salvou
