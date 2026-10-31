"""Comparar imagens: semelhança de ícones, mapas de símbolo, molduras."""

import math

from PIL import ImageChops, ImageStat

from .config import cv2, np


def miolo(img):
    """Ignora 15% de cada borda (moldura do slot, número da tecla etc.)."""
    w, h = img.size
    mx, my = max(1, int(w * 0.15)), max(1, int(h * 0.15))
    if w - 2 * mx < 2 or h - 2 * my < 2:
        return img
    return img.crop((mx, my, w - mx, h - my))


def diferenca(a, b):
    st = ImageStat.Stat(ImageChops.difference(a, b))
    return sum(st.mean) / (len(st.mean) * 255.0)


def cinza(img):
    return np.asarray(img.convert("L"), dtype=np.float32)


def mapa_simbolo(arr):
    """Realça os traços claros do desenho do ícone (ex.: o kanji branco da Brisa Leve).

    Os ícones de buff do RO são translúcidos: o cenário aparece por trás e muda o tempo todo,
    e uma "varredura" clara mostra o tempo restante. Os traços brancos do desenho não mudam,
    então comparar só eles reconhece o buff em qualquer fundo."""
    m = np.asarray(arr)[..., :3].min(axis=2).astype(np.int32)
    return (np.clip(m - 200, 0, 40) * 255 // 40).astype(np.uint8)


def mapa_simbolo_suave(arr):
    """Traços claros levemente desfocados: tolera 1 pixel de diferença e ícone ampliado."""
    m = mapa_simbolo(arr)
    return cv2.GaussianBlur(m, (3, 3), 0) if cv2 is not None else m


def tem_moldura(mx, x, y, w, h, folga=4, minimo=230):
    """Os ícones de buff do RO têm uma moldura clara em volta. Texto e cenário não.
    mx = brilho (maior canal) da imagem. Exige pelo menos 2 lados claros."""
    H, W = mx.shape

    def lin_h(yy):
        if not 0 <= yy < H:
            return 0.0
        seg = mx[yy, max(0, x + 3):min(W, x + w - 3)]
        return float(seg.mean()) if seg.size else 0.0

    def lin_v(xx):
        if not 0 <= xx < W:
            return 0.0
        seg = mx[max(0, y + 3):min(H, y + h - 3), xx]
        return float(seg.mean()) if seg.size else 0.0

    d = range(-folga, folga + 1)
    lados = [max(lin_h(y + k) for k in d), max(lin_h(y + h - 1 + k) for k in d),
             max(lin_v(x + k) for k in d), max(lin_v(x + w - 1 + k) for k in d)]
    return sum(v >= minimo for v in lados) >= 2


def picos(r, n=4, raio=6):
    """Até n melhores posições de um mapa de semelhança (apagando em volta de cada uma)."""
    r = r.copy()
    for _ in range(n):
        _, v, _, loc = cv2.minMaxLoc(r)
        if v != v or v <= -1:
            return
        yield v, loc
        x, y = loc
        r[max(0, y - raio):y + raio + 1, max(0, x - raio):x + raio + 1] = -1


def modelos_buff(im):
    """(modelo em tons de cinza, modelo só dos traços claros ou None) do miolo do ícone."""
    c = miolo(im)
    branco = mapa_simbolo(np.asarray(c))
    if branco.std() < 8:
        return np.asarray(c.convert("L")), None
    return np.asarray(c.convert("L")), mapa_simbolo_suave(np.asarray(c))


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    va, vb = float((a * a).sum()), float((b * b).sum())
    liso = 1e-3 * a.size
    if vb < liso:                       # pedaço liso no ícone original
        return 1.0 if va < liso else 0.0
    if va < liso:
        return 0.0
    return float((a * b).sum() / math.sqrt(va * vb))


def semelhanca(a, b, n=3):
    """0 a 1: o ícone continua sendo o mesmo? Não muda se ele escurecer, ficar cinza
    ou tiver a varredura do delay; cai para ~0 se for outro ícone ou slot vazio."""
    if a.shape != b.shape:
        return 0.0
    h, w = b.shape
    vals = [_ncc(a[i * h // n:(i + 1) * h // n, j * w // n:(j + 1) * w // n],
                 b[i * h // n:(i + 1) * h // n, j * w // n:(j + 1) * w // n])
            for i in range(n) for j in range(n)]
    return float(np.median(vals))


def sem_cor_chave(img):
    return img.point(lambda v: max(v, 2))
