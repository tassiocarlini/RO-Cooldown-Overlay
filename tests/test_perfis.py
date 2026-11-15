"""Salvar sem risco de perder o perfil (arquivo pela metade ou estragado)."""
import json

import pytest

from rocd import perfis
from rocd.dados import gravar_json


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(perfis, "PASTA_PERFIS", tmp_path)
    monkeypatch.setattr(perfis, "registrar", lambda *a, **k: None)
    return tmp_path


def test_gravar_troca_o_arquivo_inteiro(tmp_path):
    arq = tmp_path / "a.json"
    gravar_json(arq, {"v": 1})
    gravar_json(arq, {"v": 2})
    assert json.loads(arq.read_text(encoding="utf-8")) == {"v": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]       # sem .tmp sobrando


def test_erro_ao_gravar_nao_estraga_o_arquivo_antigo(tmp_path):
    arq = tmp_path / "a.json"
    gravar_json(arq, {"v": 1})
    with pytest.raises(TypeError):
        gravar_json(arq, {"v": object()})                           # não vira JSON
    assert json.loads(arq.read_text(encoding="utf-8")) == {"v": 1}


def test_salvar_e_carregar(pasta):
    p = perfis.Perfis.carregar("novo")                              # ainda não existe: padrão
    p["skills"].append({"nome": "Teste", "_tmp": 1})
    perfis.Perfis.salvar("novo", p)
    de_volta = perfis.Perfis.carregar("novo")
    assert de_volta["skills"] == [{"nome": "Teste"}]
    assert not list(pasta.glob("novo/perfil.estragado*"))


def test_perfil_estragado_ganha_copia(pasta):
    (pasta / "meu").mkdir()
    (pasta / "meu" / "perfil.json").write_text('{"skills": [{"nome": "Impo', encoding="utf-8")
    p = perfis.Perfis.carregar("meu")
    assert p["skills"] == []
    copias = list((pasta / "meu").glob("perfil.estragado.*.json"))
    assert len(copias) == 1 and "Impo" in copias[0].read_text(encoding="utf-8")
