"""Etiquetas de estado do painel: texto curto e tipo (cor) de cada skill e buff."""
from types import SimpleNamespace

from rocd.painel import Painel


def painel(ativo=True, geo=(0, 0), estado_jogo="", icones=True):
    ov = SimpleNamespace(ativo=ativo, geo=geo, estado_jogo=estado_jogo)
    return SimpleNamespace(overlay=ov, _estado_jogo=Painel._estado_jogo,
                           icone_buff=lambda _e: icones)


def estado_skill(p, **sk):
    return Painel.estado_skill(p, {"x": 10, "_d": 0.4, "_delay": False, **sk})[:2]


def test_skill_recarga_delay_e_pronta():
    p = painel()
    assert estado_skill(p, _delay=True, _contando=True) == ("Em recarga", "alerta")
    assert estado_skill(p, _delay=True) == ("Delay", "alerta")
    assert estado_skill(p) == ("Pronta", "ok")


def test_skill_sem_overlay_ou_sem_jogo():
    assert estado_skill(painel(ativo=False)) == ("Parado", "neutro")
    assert estado_skill(painel(geo=None, estado_jogo="jogo não encontrado")) == \
        ("Jogo não encontrado", "erro")
    assert estado_skill(painel(geo=None, estado_jogo="jogo minimizado")) == \
        ("Jogo minimizado", "alerta")


def test_skill_fora_da_tela():
    p = painel()
    assert estado_skill(p, x=None) == ("Sem ícone", "erro")
    assert estado_skill(p, x=None, _tmpl=object()) == ("Procurando…", "neutro")
    assert estado_skill(p, _sumiu=True) == ("Fora da tela", "erro")
    assert estado_skill(p, _vis=False) == ("Barra coberta", "alerta")


def test_numeros_da_deteccao_so_no_detalhe():
    texto, _, detalhe = Painel.estado_skill(painel(), {"x": 1, "_d": 0.123, "_delay": False})
    assert "0.12" in detalhe and "0.12" not in texto


def test_buff():
    p = painel()
    bf = {"_tmpls": [1], "_score": 0.9, "_ativo": True, "variantes": []}
    assert Painel.estado_buff(p, bf)[:2] == ("Ativo", "ok")
    assert Painel.estado_buff(p, dict(bf, _ativo=False))[:2] == ("Inativo", "neutro")
    assert Painel.estado_buff(p, {"efst": [("a", 1)], "_aguardando_tela": True})[:2] == \
        ("Ative no jogo", "alerta")
    assert Painel.estado_buff(painel(icones=False), {"efst": [("a", 1)]})[:2] == \
        ("Baixando…", "neutro")
    assert Painel.estado_buff(p, {})[:2] == ("Sem ícone", "erro")
    _, _, detalhe = Painel.estado_buff(p, dict(bf, variantes=["v1", "buff_site_1"]))
    assert "1 de 2" in detalhe
