"""Visual: logo, ícone do .exe e a troca de azul por dourado do tema."""
from pathlib import Path

from PIL import Image

from rocd.desenho import BOTOES, COR, TEXTO_ESCURO, dourar, imagem_aba, logo_app

RAIZ = Path(__file__).resolve().parent.parent


def test_logo_em_varios_tamanhos():
    for t in (16, 32, 256):
        im = logo_app(t)
        assert im.size == (t, t) and im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0                 # canto arredondado transparente
        assert im.getpixel((t // 2, t // 2))[3] > 250


def test_icone_do_exe_tem_todos_os_tamanhos():
    ico = Image.open(RAIZ / "assets" / "icone.ico")
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= set(ico.info["sizes"])


def test_dourar_troca_so_o_azul():
    im = Image.new("RGBA", (3, 1))
    im.putpixel((0, 0), (87, 200, 255, 255))       # azul do sv_ttk
    im.putpixel((1, 0), (80, 80, 80, 255))         # cinza fica
    im.putpixel((2, 0), (47, 96, 216, 128))        # azul meio transparente
    out = dourar(im)
    r, g, b, a = out.getpixel((0, 0))
    assert r > g > b and a == 255                  # virou dourado
    assert out.getpixel((1, 0)) == (80, 80, 80, 255)
    assert out.getpixel((2, 0))[3] == 128


def test_aba_selecionada_tem_traco():
    normal = imagem_aba(40, 34, COR["fundo"])
    sel = imagem_aba(40, 34, COR["fundo"], COR["ouro"])
    assert normal.getpixel((20, 32)) != sel.getpixel((20, 32))
    assert normal.getpixel((20, 10)) == sel.getpixel((20, 10))


def test_botoes_claros_tem_texto_escuro():
    assert TEXTO_ESCURO <= set(BOTOES)
    assert BOTOES["Destaque"][0][0] == COR["ouro"]


def test_icone_pequeno_ampliado_sem_serrilhado():
    from rocd.desenho import icone_arredondado
    pequeno = Image.new("RGB", (24, 24), (200, 40, 40))
    for T in (24, 50, 52):
        assert icone_arredondado(pequeno, T, 8).size == (T, T)
