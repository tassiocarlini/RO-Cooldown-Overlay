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


def test_consumiveis_sem_ragassets_tem_icone_embutido():
    """Ids antigos que o ragassets não tem (404): o ícone vem do data.grf do cliente LATAM."""
    from rocd.consumiveis import CONSUMIVEIS
    embutidos = {"Poção da Concentração": 37, "Poção do Despertar": 38, "Poção da Fúria": 39,
                 "Poção Energizante": 579, "Pílula de HP": 297, "Pílula de SP": 299, "Acarajé": 414,
                 "Biscoito da Papisa": 423, "Pergaminho Tao Gunka": 368,
                 "Pergaminho Abelha Rainha": 369, "Pergaminho Orc Herói": 370,
                 "Pergaminho Senhor dos Orcs": 371}
    ids = {nome: e for nome, efst, _ in CONSUMIVEIS for e in efst}
    for nome, eid in embutidos.items():
        assert ids[nome] == eid, nome                  # o nome continua apontando para este id
        im = Image.open(icone_embutido(eid))
        assert im.size == (32, 32) and im.mode == "RGBA", nome


def test_maestria_arcana_tem_icone_embutido():
    """O ragassets não tem o ícone 355 e o da Divine Pride vem embaralhado."""
    efst = Banco().efst_de("Recognized Spell")
    assert [e for _, e in efst] == [355]
    assert Image.open(icone_embutido(355)).size == (32, 32)
