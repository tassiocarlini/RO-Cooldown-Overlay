"""Relógio do ícone de buff: quanto tempo do buff já passou, olhando só o ícone na tela.

O cliente cobre o ícone com um véu claro no tempo que já passou, começando às 12 h e girando
no sentido horário. O programa acha o "ponteiro" (a borda reta onde o véu termina) e, sabendo a
duração do buff, calcula quando ele começou. Assim acerta o tempo de um buff que já estava
ativo e percebe quando ele é renovado (o véu volta para o começo).

Conferido no jogo com o Estimulante (30 min) em cima de fundos claros e escuros: erro de até
2,4% da duração (uns 40 s em 30 min).
"""

from .config import np

DELTA = 9              # graus olhados de cada lado da borda
LIMIAR_ARTE = 200      # traços brancos do desenho (não mudam com o véu: ficam de fora)
FORCA_MIN = 20         # abaixo disso não tem borda de verdade (ícone coberto, fundo liso)


def arte_do_icone(im):
    """Máscara dos traços brancos do desenho, a partir de uma versão do ícone (PIL)."""
    return np.asarray(im.convert("RGB")).min(axis=2) > LIMIAR_ARTE


def fracao_passada(icone, arte=None):
    """icone: recorte RGB do ícone na tela (moldura inclusa). arte: máscara dos traços do
    desenho, do mesmo tamanho. Devolve (fração já passada 0..1, força da borda) ou None.

    Logo depois de usar o buff ainda não há véu para ver: a leitura fica em ~DELTA graus, e
    isso é tratado como "acabou de começar" (0)."""
    a = np.asarray(icone, dtype=np.float32)
    if a.ndim != 3 or min(a.shape[:2]) < 16:
        return None
    h, w = a.shape[:2]
    v = a[..., :3].min(axis=2)                      # o véu claro sobe o menor canal
    if arte is not None and arte.shape == v.shape:
        v = np.where(arte, np.nan, v)
    lado = min(h, w)
    r0, r1 = max(2, round(lado * 6 / 32)), max(3, round(lado * 14 / 32))
    cy, cx = (h - 1) / 2, (w - 1) / 2
    angs = np.radians(np.arange(360))
    raios = np.arange(r0, r1 + 1)
    xi = np.clip(np.rint(cx + np.outer(raios, np.sin(angs))).astype(int), 0, w - 1)
    yi = np.clip(np.rint(cy - np.outer(raios, np.cos(angs))).astype(int), 0, h - 1)
    amostras = v[yi, xi]                            # raios x ângulos
    validos = ~np.isnan(amostras)
    if validos.sum() < amostras.size * 0.3:
        return None
    perfil = np.nanmedian(np.where(validos.any(axis=0), amostras, 0.0), axis=0)
    perfil = np.where(validos.any(axis=0), perfil, np.nan)
    perfil = np.where(np.isnan(perfil), np.nanmean(perfil), perfil)
    d = DELTA
    ext = np.concatenate([perfil[-d:], perfil, perfil[:d]])
    cs = np.concatenate([[0.0], np.cumsum(ext)])
    antes = (cs[d:d + 360] - cs[0:360]) / d                  # [φ-δ, φ): claro (já passou)
    depois = (cs[2 * d:2 * d + 360] - cs[d:d + 360]) / d     # [φ, φ+δ): escuro (falta)
    passo = antes - depois
    phi = int(np.argmax(passo[1:]) + 1)
    forca = float(passo[phi])
    if forca < FORCA_MIN:
        return None
    return (0.0 if phi <= d + 1 else phi / 360), forca


def inicio_estimado(leituras, duracao, tolerancia):
    """leituras: [(hora da leitura, fração passada)], da mais antiga para a mais nova.
    Devolve a hora em que o buff começou se as últimas leituras concordam, senão None."""
    if len(leituras) < 3:
        return None
    inicios = sorted(t - f * duracao for t, f in leituras[-5:])
    meio = inicios[len(inicios) // 2]
    if inicios[-1] - inicios[0] > tolerancia:
        return None
    return meio
