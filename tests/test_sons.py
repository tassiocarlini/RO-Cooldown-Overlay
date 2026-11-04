"""Sons gerados e download do MyInstants (sem internet: as respostas são falsas)."""
import io
import struct
import urllib.request
import wave

import pytest

from rocd import sons
from rocd.config import SEM_SOM, SONS_PRONTOS, SONS_VOZ
from rocd.sons import Sons, ajustar_voz, baixar_myinstants

MP3 = b"ID3" + b"\0" * 100


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def site(monkeypatch):
    """Troca a internet por um dicionário: link -> bytes."""
    paginas = {}

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        if url not in paginas:
            raise AssertionError(f"link inesperado: {url}")
        return Resposta(paginas[url])
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return paginas


def pagina(mp3, titulo="Gawr Gura &amp; A"):
    return (f'<meta property="og:audio" content="{mp3}">'
            f'<h1 id="instant-page-title">{titulo}</h1>').encode()


def test_pagina_do_som(site):
    site["https://www.myinstants.com/pt/instant/gura/"] = pagina("/media/sounds/gura.mp3")
    site["https://www.myinstants.com/media/sounds/gura.mp3"] = MP3
    assert baixar_myinstants("www.myinstants.com/pt/instant/gura/") == ("Gawr Gura & A", MP3)


def test_link_direto_do_mp3(site):
    site["https://www.myinstants.com/media/sounds/meu-som_1.mp3"] = MP3
    assert baixar_myinstants("https://www.myinstants.com/media/sounds/meu-som_1.mp3") == \
        ("meu som 1", MP3)


@pytest.mark.parametrize("link", ["https://example.com/a.mp3", "myinstants.com.mal.com/x",
                                  "", "https://mal.com/?myinstants.com/"])
def test_so_aceita_myinstants(link):
    with pytest.raises(ValueError):
        baixar_myinstants(link)


def test_som_de_outro_site_na_pagina(site):
    site["https://www.myinstants.com/pt/instant/x/"] = pagina("https://mal.com/x.mp3")
    with pytest.raises(ValueError, match="não está no myinstants"):
        baixar_myinstants("https://www.myinstants.com/pt/instant/x/")


def test_recusa_o_que_nao_e_mp3(site):
    site["https://www.myinstants.com/media/sounds/x.mp3"] = b"<html>erro</html>"
    with pytest.raises(ValueError, match="não é um MP3"):
        baixar_myinstants("https://www.myinstants.com/media/sounds/x.mp3")


def test_recusa_som_grande(site):
    site["https://www.myinstants.com/media/sounds/x.mp3"] = b"ID3" + b"\0" * 3_000_000
    with pytest.raises(ValueError, match="grande demais"):
        baixar_myinstants("https://www.myinstants.com/media/sounds/x.mp3")


@pytest.fixture
def pastas(tmp_path, monkeypatch):
    monkeypatch.setattr(sons, "PASTA_SONS", tmp_path / "sons")
    monkeypatch.setattr(sons, "PASTA_MEUS_SONS", tmp_path / "meus_sons")
    return tmp_path


def test_gera_todos_os_sons_prontos(pastas):
    s = Sons()
    for k in SONS_PRONTOS:
        with wave.open(str(s._arquivo(k))) as w:
            assert w.getnframes() > 1000


def _wav(arq, amostras, taxa=16000):
    with wave.open(str(arq), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(struct.pack(f"<{len(amostras)}h", *amostras))


def test_ajustar_voz_corta_silencio_e_normaliza(tmp_path):
    fala = [3000, -3000] * 800                       # 0,1 s de "voz" baixa
    _wav(tmp_path / "a.wav", [0] * 16000 + fala + [0] * 16000)
    ajustar_voz(tmp_path / "a.wav", tmp_path / "b.wav", tom=0.8)
    with wave.open(str(tmp_path / "b.wav")) as w:
        assert w.getframerate() == 12800             # tom mais grave
        n = w.getnframes()
        a = struct.unpack(f"<{n}h", w.readframes(n))
    assert n < 1600 + 16000 * 0.11                   # sobra só um respiro antes e depois
    assert max(abs(v) for v in a) == 26000


def test_sons_de_voz_nas_opcoes(pastas):
    s = Sons()
    for chave, (nome, _) in SONS_VOZ.items():
        assert s.opcoes()[nome] == chave and s.existe(chave)


def test_voz_que_falha_nao_tenta_de_novo(pastas, monkeypatch):
    chamadas = []

    def run(*a, **k):
        chamadas.append(a)
        raise OSError("sem powershell")
    monkeypatch.setattr(sons.subprocess, "run", run)
    s = Sons()
    chave = next(iter(SONS_VOZ))
    assert s._arquivo(chave) is None and s._arquivo(chave) is None
    assert len(chamadas) == 1


def test_opcoes_e_meus_sons(pastas):
    (pastas / "meus_sons").mkdir()
    (pastas / "meus_sons" / "Jungle.mp3").write_bytes(MP3)
    (pastas / "meus_sons" / "leia.txt").write_text("x")
    s = Sons()
    op = s.opcoes()
    assert next(iter(op)) == SEM_SOM and op[SEM_SOM] is None
    assert op["Jungle"] == "meu:Jungle"
    assert s.existe("meu:Jungle") and s.existe("sino")
    assert not s.existe("meu:leia") and not s.existe(None)
    assert s.nome("meu:Jungle") == "Jungle"
    assert s.nome(None) == SEM_SOM
