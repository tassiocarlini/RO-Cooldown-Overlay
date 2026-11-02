"""Chave padrão da Divine Pride: embaralhada no .exe e a sua tem prioridade."""
import ast

from rocd.chave import esconder, revelar
from rocd.sites import DivinePride


def test_esconder_e_revelar():
    texto = esconder("abc123-CHAVE-de-teste")
    assert "abc123" not in texto and "CHAVE" not in texto      # não fica como texto
    ns = {}
    exec(compile(ast.parse(texto), "_chave", "exec"), ns)
    assert revelar(ns["M"], ns["D"]) == "abc123-CHAVE-de-teste"
    assert esconder("abc123-CHAVE-de-teste") != texto          # máscara nova a cada geração


def test_sua_chave_vence_a_do_aplicativo():
    dp = DivinePride.__new__(DivinePride)                       # sem rede nem threads
    dp.chave, dp.padrao = "", "do-app"
    assert dp.ativo() and dp.usando_padrao() and dp.chave_em_uso() == "do-app"
    dp.chave = "minha"
    assert not dp.usando_padrao() and dp.chave_em_uso() == "minha"
    dp.padrao = ""
    dp.chave = ""
    assert not dp.ativo()
