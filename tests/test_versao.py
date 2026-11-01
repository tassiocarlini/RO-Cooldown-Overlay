"""Versão, atualização e a porta de entrada."""
import importlib
import io
import pkgutil
import re
import urllib.request
import zipfile
from pathlib import Path

import pytest

import rocd
from rocd.config import VERSAO
from rocd.atualizacao import (ARQUIVOS_PROGRAMA, PASTAS_PROGRAMA, _extrair_seguro,
                              buscar_versao_nova, versao_tupla)

RAIZ = Path(__file__).resolve().parent.parent


def test_todos_os_modulos_carregam():
    for m in pkgutil.iter_modules(rocd.__path__):
        importlib.import_module(f"rocd.{m.name}")


def test_versao_igual_no_changelog_e_no_leia_me():
    """Esquecer de subir um dos três faz o atualizador oferecer a versão errada."""
    changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## v([\d.]+)", changelog, re.M).group(1) == VERSAO
    assert f"v{VERSAO}" in (RAIZ / "LEIA-ME.txt").read_text(encoding="utf-8").splitlines()[0]


def test_versao_tupla():
    assert versao_tupla("v1.0.16") == (1, 0, 16)
    assert versao_tupla("1.0.10") > versao_tupla("1.0.9")
    assert versao_tupla("") == (0,)


def test_atualizador_copia_o_programa_todo():
    assert "ro_cooldown_overlay.py" in ARQUIVOS_PROGRAMA
    assert "rocd" in PASTAS_PROGRAMA
    for nome in ARQUIVOS_PROGRAMA + PASTAS_PROGRAMA:
        if nome != "RO Cooldown Overlay.exe":          # o lançador não fica no repositório
            assert (RAIZ / nome).exists(), nome


def test_extrair_seguro(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pasta/ok.txt", "ok")
    _extrair_seguro(zipfile.ZipFile(buf), tmp_path)
    assert (tmp_path / "pasta" / "ok.txt").read_text() == "ok"
    with zipfile.ZipFile(buf, "a") as z:
        z.writestr("../fora.txt", "mal")
    with pytest.raises(ValueError):
        _extrair_seguro(zipfile.ZipFile(buf), tmp_path / "b")
    assert not (tmp_path / "fora.txt").exists()


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("topo, nova", [("v99.0.0", True), (f"v{VERSAO}", False)])
def test_buscar_versao_nova(monkeypatch, topo, nova):
    texto = f"# Mudanças\n\n## {topo}\n- Novidade boa.\n\n## v0.0.1\n- Antiga.\n"
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None:
                        Resposta(texto.encode()))
    info = buscar_versao_nova()
    if nova:
        assert info["tag"] == topo and info["notas"] == "- Novidade boa."
        assert info["zip_fonte"].endswith("/main.zip")
    else:
        assert info is None


def test_entrada_baixa_a_pasta_rocd_que_falta(tmp_path, monkeypatch):
    """Quem atualiza da v1.0.28 recebe só o ro_cooldown_overlay.py: ele baixa a rocd/."""
    import ro_cooldown_overlay as entrada
    zipado = tmp_path / "main.zip"
    with zipfile.ZipFile(zipado, "w") as z:
        z.writestr("Repo-main/rocd/app.py", "# app")
        z.writestr("Repo-main/rocd/sub/x.py", "# x")
        z.writestr("Repo-main/README.md", "fora da rocd")
        z.writestr("Repo-main/rocd/../../mal.py", "mal")
    destino = tmp_path / "programa"
    destino.mkdir()
    monkeypatch.setattr(entrada, "AQUI", destino)
    entrada.completar_atualizacao(zipado.as_uri())
    assert (destino / "rocd" / "app.py").read_text() == "# app"
    assert (destino / "rocd" / "sub" / "x.py").exists()
    assert not (destino / "README.md").exists()
    assert not (tmp_path / "mal.py").exists()
