"""Ícones de status embutidos: a Brisa Leve funciona sem baixar nada e sem marcar na tela."""
from PIL import Image

from rocd.dados import Banco
from rocd.sites import ICONES_EMBUTIDOS, RagAssets, icone_embutido


def test_brisa_leve_tem_todos_os_icones_embutidos():
    efst = Banco().efst_de("Brisa Leve")
    assert len(efst) == 7
    for _, eid in efst:
        p = icone_embutido(eid)
        assert p is not None, eid
        im = Image.open(p)
        assert im.size == (32, 32)                     # tamanho do ícone no jogo (escala 1)


def test_embutido_vem_antes_do_ragassets():
    rag = RagAssets.__new__(RagAssets)                 # sem rede nem threads
    eid = int(next(ICONES_EMBUTIDOS.glob("status_*.png")).stem.split("_")[1])
    assert rag.icone_status(eid) == icone_embutido(eid)
