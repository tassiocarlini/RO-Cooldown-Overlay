"""Banco de skills, tempos e JSON."""
import pytest

from rocd import dados
from rocd.dados import (Banco, chave, extrair_recarga, fmt_contagem, fmt_tempo, gravar_json,
                        ler_json, ler_tempo, mesclar, _segundos)


@pytest.mark.parametrize("txt, esperado", [
    ("12", (12, True)), ("4,5", (4.5, True)), (" 1:30 ", (90, True)), ("", (None, True)),
    ("abc", (None, False)), ("0", (None, False)), ("-3", (None, False)),
])
def test_ler_tempo(txt, esperado):
    assert ler_tempo(txt) == esperado


def test_fmt_tempo():
    assert fmt_tempo(None) == ""
    assert fmt_tempo(4.5) == "4.5"
    assert fmt_tempo(12.0) == "12"


@pytest.mark.parametrize("seg, esperado", [
    (300, "5:00"), (299.4, "5:00"), (299, "4:59"), (10, "0:10"), (0.2, "0:01"), (0, "0:00"),
    (-3, "0:00"), (5400, "90:00"),
])
def test_fmt_contagem(seg, esperado):
    assert fmt_contagem(seg) == esperado


def test_chave_sem_acento():
    assert chave("Ataque  Aéreo!") == "ataque aereo"
    assert chave(None) == ""


def test_mesclar_completa_sem_perder_o_que_tem():
    padrao = {"a": 1, "sub": {"x": 1, "y": [1]}}
    out = mesclar(padrao, {"sub": {"x": 5}, "extra": True})
    assert out == {"a": 1, "sub": {"x": 5, "y": [1]}, "extra": True}
    out["sub"]["y"].append(2)
    assert padrao["sub"]["y"] == [1]              # não divide listas com o padrão


@pytest.mark.parametrize("v, esperado", [
    (5000, 5), (45, 45), ("1.5 s", 1.5), ("800ms", 0.8), ("2,5", 2.5), ([1, 2, 3], 3),
    ({"value": 2}, 2), (None, None), (True, None), ("sem número", None),
])
def test_segundos(v, esperado):
    assert _segundos(v) == esperado


def test_extrair_recarga():
    d = {"levelTable": [{"level": 1, "cooldown": 10000}, {"level": 5, "cooldown": 3000}]}
    assert extrair_recarga(d) == 3
    assert extrair_recarga({"cooldown": 7.5}) == 7.5
    assert extrair_recarga({"cooldown": 0}) is None
    assert extrair_recarga(None) is None


def test_json_ida_e_volta(tmp_path):
    arq = tmp_path / "a.json"
    gravar_json(arq, {"nome": "Ação", "n": 1})
    assert ler_json(arq, {"n": 0, "novo": 2}) == {"nome": "Ação", "n": 1, "novo": 2}
    arq.write_text("{quebrado", encoding="utf-8")
    assert ler_json(arq, {"n": 0}) == {"n": 0}


@pytest.fixture(scope="module")
def banco():
    b = Banco()
    b.meus = {}                                   # sem as recargas salvas de quem roda o teste
    return b


def test_banco_carrega(banco):
    assert banco.ok
    assert len(banco.classes) > 10


def test_classes_em_ordem_alfabetica(banco):
    assert banco.classes == sorted(banco.classes, key=chave)
    for it in banco.itens.values():
        assert it["classes"] == sorted(it["classes"], key=chave)


def test_busca_em_ordem_alfabetica(banco):
    res = banco.buscar("")
    assert res
    nomes = [chave(it["nome"]) for it in res]
    assert nomes == sorted(nomes)
    res = banco.buscar("ataque")
    assert res and all("ataque" in chave(it["nome"]) or "ataque" in chave(it.get("en"))
                       for it in res)


def test_busca_por_classe_e_buffs(banco):
    classe = banco.classes[0]
    assert all(classe in it["classes"] for it in banco.buscar("", classe))
    assert all(it.get("efst") for it in banco.buscar("", so_buffs=True))


def test_buffs_e_skills_ofensivas_separados(banco):
    buffs = {chave(it["nome"]) for it in banco.buscar("", so_buffs=True, limite=5000)}
    ofensivas = {chave(it["nome"]) for it in banco.buscar("", limite=5000)}
    assert buffs and ofensivas and not buffs & ofensivas
    assert banco.eh_buff("Enchanting Sky")                 # Elo Celestial: só na aba Buffs
    assert "enchanting sky" not in ofensivas
    assert not banco.eh_buff("New Moon Kick")              # Eclipse Lunar: dá status, mas é ataque
    assert any(chave(it.get("en")) == "new moon kick" for it in banco.buscar("new moon"))
    assert not banco.buscar("new moon", so_buffs=True)


def test_recarga_sua_vence_a_padrao(tmp_path, monkeypatch):
    monkeypatch.setattr(dados, "ARQ_MEUS", tmp_path / "meus_tempos.json")
    b = Banco()
    b.meus = {}
    it = next(it for it in b.itens.values() if it["cd"])
    b.dp = None
    b.rag = None
    assert b.recarga(it["nome"]) == (it["cd"], "padrão")
    b.salvar_meu(it["nome"], it["cd"] + 1)
    assert b.recarga(it["nome"]) == (it["cd"] + 1, "sua")
    assert (tmp_path / "meus_tempos.json").exists()
    b.salvar_meu(it["nome"], None)                # volta para a padrão
    assert b.recarga(it["nome"]) == (it["cd"], "padrão")
