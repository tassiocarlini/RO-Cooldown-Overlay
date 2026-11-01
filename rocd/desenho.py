"""Visual do painel: paleta (COR), logo, ícones dos botões, botões e abas."""

import math

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .visao import sem_cor_chave


# ---------------------------------------------------------------- ícones e tema
# Ícones desenhados aqui mesmo (sem arquivos de imagem), em 4x e reduzidos para ficarem lisos.

ESC_ICONE = 4  # desenha 4x maior e reduz: bordas suaves


def _rgba(hexcor, a=255):
    h = hexcor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def desenhar_icone(nome, cor="#e6e6e6", tam=18):
    S = tam * ESC_ICONE
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = _rgba(cor)
    w = max(2, int(S * 0.085))          # espessura do traço
    m = S * 0.14                        # margem
    L, T, R, B = m, m, S - m, S - m
    cx, cy = S / 2, S / 2

    def linha(*pts, larg=w):
        d.line(pts, fill=c, width=larg, joint="curve")
        for p in (pts[0], pts[-1]):
            r = larg / 2
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=c)

    def circulo(x, y, r, preench=False, larg=w):
        if preench:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=larg)

    def ret(x0, y0, x1, y1, raio=S * 0.08, preench=False, larg=w):
        if preench:
            d.rounded_rectangle((x0, y0, x1, y1), radius=raio, fill=c)
        else:
            d.rounded_rectangle((x0, y0, x1, y1), radius=raio, outline=c, width=larg)

    if nome == "play":
        d.polygon([(S * 0.30, S * 0.18), (S * 0.30, S * 0.82), (S * 0.84, S * 0.50)], fill=c)
    elif nome == "stop":
        ret(S * 0.22, S * 0.22, S * 0.78, S * 0.78, preench=True)
    elif nome == "camera":
        ret(L, S * 0.30, R, B, raio=S * 0.10)
        d.polygon([(S * 0.34, S * 0.30), (S * 0.42, S * 0.18), (S * 0.58, S * 0.18), (S * 0.66, S * 0.30)], fill=c)
        circulo(cx, S * 0.56, S * 0.15)
    elif nome == "pasta":
        d.polygon([(L, S * 0.24), (S * 0.42, S * 0.24), (S * 0.50, S * 0.34), (R, S * 0.34),
                   (R, B), (L, B)], outline=c, width=w)
        linha((L, S * 0.42), (R, S * 0.42))
    elif nome == "lupa":
        circulo(S * 0.42, S * 0.42, S * 0.25)
        linha((S * 0.60, S * 0.60), (S * 0.84, S * 0.84), larg=int(w * 1.2))
    elif nome == "mais":
        linha((cx, L), (cx, B), larg=int(w * 1.1))
        linha((L, cy), (R, cy), larg=int(w * 1.1))
    elif nome == "mais_circulo":
        circulo(cx, cy, S * 0.38)
        linha((cx, S * 0.32), (cx, S * 0.68))
        linha((S * 0.32, cy), (S * 0.68, cy))
    elif nome == "selecao":              # marcar ícones: cantos de recorte + quadrado
        k = S * 0.22
        for (x, y, dx, dy) in ((L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)):
            linha((x, y + dy * k), (x, y), (x + dx * k, y))
        ret(S * 0.38, S * 0.38, S * 0.62, S * 0.62, preench=True, raio=S * 0.04)
    elif nome == "radar":                # procurar na tela: cantos + lupa
        k = S * 0.18
        for (x, y, dx, dy) in ((L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)):
            linha((x, y + dy * k), (x, y), (x + dx * k, y))
        circulo(S * 0.47, S * 0.47, S * 0.14)
        linha((S * 0.57, S * 0.57), (S * 0.68, S * 0.68))
    elif nome == "mover":
        linha((cx, L), (cx, B))
        linha((L, cy), (R, cy))
        a = S * 0.12
        for (x, y, dx, dy) in ((cx, L, 0, 1), (cx, B, 0, -1), (L, cy, 1, 0), (R, cy, -1, 0)):
            if dx == 0:
                linha((x - a, y + dy * a), (x, y), (x + a, y + dy * a))
            else:
                linha((x + dx * a, y - a), (x, y), (x + dx * a, y + a))
    elif nome == "centro":
        circulo(cx, cy, S * 0.30)
        circulo(cx, cy, S * 0.07, preench=True)
        for (a, b) in (((cx, T), (cx, S * 0.26)), ((cx, S * 0.74), (cx, B)),
                       ((L, cy), (S * 0.26, cy)), ((S * 0.74, cy), (R, cy))):
            linha(a, b)
    elif nome == "chave":
        circulo(S * 0.34, S * 0.38, S * 0.17)
        linha((S * 0.46, S * 0.50), (S * 0.82, S * 0.86))
        linha((S * 0.66, S * 0.70), (S * 0.56, S * 0.80))
        linha((S * 0.76, S * 0.80), (S * 0.68, S * 0.88))
    elif nome == "ajuda":
        circulo(cx, cy, S * 0.38)
        d.arc((S * 0.36, S * 0.24, S * 0.64, S * 0.50), start=180, end=50, fill=c, width=w)
        linha((S * 0.59, S * 0.44), (cx, S * 0.54), (cx, S * 0.60))
        circulo(cx, S * 0.72, w * 0.7, preench=True)
    elif nome == "check":
        circulo(cx, cy, S * 0.38)
        linha((S * 0.33, S * 0.52), (S * 0.45, S * 0.64), (S * 0.68, S * 0.38))
    elif nome == "copiar":
        ret(S * 0.34, S * 0.34, R, B)
        linha((S * 0.24, S * 0.66), (L, S * 0.66), (L, L), (S * 0.66, L), (S * 0.66, S * 0.24))
    elif nome == "lapis":
        d.polygon([(S * 0.64, S * 0.18), (S * 0.82, S * 0.36), (S * 0.38, S * 0.80),
                   (S * 0.16, S * 0.84), (S * 0.20, S * 0.62)], outline=c, width=w)
        linha((S * 0.56, S * 0.26), (S * 0.74, S * 0.44))
    elif nome == "lixeira":
        linha((S * 0.20, S * 0.28), (S * 0.80, S * 0.28))
        linha((S * 0.40, S * 0.28), (S * 0.42, S * 0.18), (S * 0.58, S * 0.18), (S * 0.60, S * 0.28))
        d.polygon([(S * 0.27, S * 0.34), (S * 0.73, S * 0.34), (S * 0.69, B), (S * 0.31, B)],
                  outline=c, width=w)
        linha((S * 0.43, S * 0.46), (S * 0.43, S * 0.74))
        linha((S * 0.57, S * 0.46), (S * 0.57, S * 0.74))
    elif nome == "cima":
        linha((S * 0.24, S * 0.64), (cx, S * 0.36), (S * 0.76, S * 0.64), larg=int(w * 1.2))
    elif nome == "baixo":
        linha((S * 0.24, S * 0.36), (cx, S * 0.64), (S * 0.76, S * 0.36), larg=int(w * 1.2))
    elif nome == "fechar":
        linha((S * 0.28, S * 0.28), (S * 0.72, S * 0.72), larg=int(w * 1.1))
        linha((S * 0.72, S * 0.28), (S * 0.28, S * 0.72), larg=int(w * 1.1))
    elif nome in ("exportar", "importar"):
        linha((L, S * 0.62), (L, B), (R, B), (R, S * 0.62))
        if nome == "exportar":
            linha((cx, S * 0.66), (cx, T))
            linha((S * 0.32, S * 0.32), (cx, T), (S * 0.68, S * 0.32))
        else:
            linha((cx, T), (cx, S * 0.66))
            linha((S * 0.32, S * 0.46), (cx, S * 0.66), (S * 0.68, S * 0.46))
    elif nome == "escudo":
        d.polygon([(cx, S * 0.12), (S * 0.82, S * 0.26), (S * 0.78, S * 0.58), (cx, S * 0.88),
                   (S * 0.22, S * 0.58), (S * 0.18, S * 0.26)], outline=c, width=w)
        linha((S * 0.36, S * 0.50), (S * 0.46, S * 0.60), (S * 0.65, S * 0.40))
    elif nome == "som":                  # alto-falante com ondas
        d.polygon([(S * 0.14, S * 0.38), (S * 0.30, S * 0.38), (S * 0.50, S * 0.20),
                   (S * 0.50, S * 0.80), (S * 0.30, S * 0.62), (S * 0.14, S * 0.62)], fill=c)
        for r in (S * 0.14, S * 0.28):
            d.arc((S * 0.50 - r, cy - r, S * 0.50 + r, cy + r), start=-50, end=50, fill=c, width=w)
    elif nome == "relogio":              # logo do app: cronômetro com varredura
        circulo(cx, S * 0.56, S * 0.34)
        d.pieslice((cx - S * 0.26, S * 0.56 - S * 0.26, cx + S * 0.26, S * 0.56 + S * 0.26),
                   start=-90, end=120, fill=c)
        ret(S * 0.42, S * 0.08, S * 0.58, S * 0.16, preench=True, raio=S * 0.02)
        linha((cx, S * 0.16), (cx, S * 0.22))
    return im.resize((tam, tam), Image.LANCZOS)


NOMES_ICONES = ["play", "stop", "camera", "pasta", "lupa", "mais", "mais_circulo", "selecao", "radar",
         "mover", "centro", "chave", "ajuda", "check", "copiar", "lapis", "lixeira", "cima",
         "baixo", "fechar", "relogio", "escudo", "exportar", "importar", "som"]



def windows_usa_tema_escuro():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


def _degrade_vertical(w, h, topo, base):
    col = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        col.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(topo, base)) + (255,))
    return col.resize((w, h))


def _mascara_arred(S, caixa, raio):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle(caixa, radius=raio, fill=255)
    return m


def desenhar_logo(S=512):
    """Ícone do programa: quadrado de skill com borda dourada e a sombra da recarga girando."""
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    im.paste(_degrade_vertical(S, S, (30, 38, 66), (10, 13, 26)), (0, 0),
             _mascara_arred(S, (0, 0, S - 1, S - 1), int(S * 0.22)))
    m, r, b = int(S * 0.15), int(S * 0.11), int(S * 0.045)
    caixa = (m, m, S - m, S - m)
    im.paste(_degrade_vertical(S, S, (255, 226, 140), (176, 120, 20)), (0, 0),
             _mascara_arred(S, caixa, r))                                 # borda dourada
    dentro = (caixa[0] + b, caixa[1] + b, caixa[2] - b, caixa[3] - b)
    m_dentro = _mascara_arred(S, dentro, r - b)
    im.paste(_degrade_vertical(S, S, (255, 196, 64), (226, 92, 20)), (0, 0), m_dentro)
    luz = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(luz).ellipse((S * 0.3, S * 0.25, S * 0.7, S * 0.6), fill=(255, 245, 200, 160))
    im.alpha_composite(luz.filter(ImageFilter.GaussianBlur(S * 0.06)))
    pronto = 0.32                       # parte que já voltou; o resto é a sombra da recarga
    sombra = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sombra).pieslice((-S, -S, 2 * S, 2 * S), -90 + 360 * pronto, 270, fill=200)
    im.paste(Image.new("RGBA", (S, S), (8, 10, 20, 255)), (0, 0),
             ImageChops.multiply(sombra, m_dentro))
    c, ang = S / 2, math.radians(-90 + 360 * pronto)
    d = ImageDraw.Draw(im)
    d.line((c, c, c + math.cos(ang) * S * 0.36, c + math.sin(ang) * S * 0.36),
           fill=(255, 250, 225, 255), width=max(1, int(S * 0.018)))
    traco = Image.new("RGBA", (S, S), (0, 0, 0, 0))      # meio transparente: misturar, não gravar
    ImageDraw.Draw(traco).line((c, c, c, dentro[1]), fill=(255, 250, 225, 200),
                               width=max(1, int(S * 0.012)))
    im.alpha_composite(traco)
    return im


_LOGO = None


def logo_app(tam):
    """O ícone do programa no tamanho pedido (desenhado uma vez grande e reduzido)."""
    global _LOGO
    if _LOGO is None:
        _LOGO = desenhar_logo()
    return _LOGO.resize((tam, tam), Image.LANCZOS)


def imagem_degrade(larg, alt, cor_topo, cor_base, raio=7, borda=None):
    """Fundo arredondado com degradê vertical (cor_topo = cor_base: liso). Usado nos botões."""
    E = 4
    W, H = larg * E, alt * E
    c1, c2 = _rgba(cor_topo), _rgba(cor_base)
    grad = Image.new("RGBA", (1, H))
    for y in range(H):
        t = y / max(1, H - 1)
        grad.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4)))
    grad = grad.resize((W, H))
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, W - 1, H - 1), radius=raio * E, fill=255)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.paste(grad, (0, 0), mascara)
    if borda:
        ImageDraw.Draw(im).rounded_rectangle((E // 2, E // 2, W - 1 - E // 2, H - 1 - E // 2),
                                             radius=raio * E, outline=_rgba(borda), width=E)
    return im.resize((larg, alt), Image.LANCZOS)


# Paleta do painel: mude aqui para trocar o visual. O fundo é o do tema sv_ttk escuro.
COR = {
    "fundo": "#1c1c1c",
    "cabecalho": "#141414",       # faixa do topo e rodapé
    "cartao": "#242424",          # linhas das listas
    "campo": "#2b2b2b",           # botões comuns
    "borda": "#363636",
    "borda2": "#4a4a4a",
    "texto": "#ececec",
    "mudo": "#8f8f8f",
    "ouro": "#f5b82e",            # a única cor de destaque
    "ouro_claro": "#ffc94d",
    "ouro_escuro": "#d99a12",
    "texto_ouro": "#1a1408",      # texto em cima do dourado
    "verde": "#3ecf8e",
    "vermelho": "#f0616d",
}

# Botões lisos: (normal, passar o mouse, apertado), cada um (fundo, borda)
BOTOES = {
    "Grad":     ((COR["campo"], COR["borda2"]), ("#343434", "#5c5c5c"), ("#232323", COR["borda2"])),
    "Destaque": ((COR["ouro"], COR["ouro"]), (COR["ouro_claro"], COR["ouro_claro"]),
                 (COR["ouro_escuro"], COR["ouro_escuro"])),
    "Perigo":   ((COR["campo"], COR["borda2"]), ("#3a2a2c", COR["vermelho"]), ("#232323", COR["borda2"])),
}
BOTOES["Amarelo"] = BOTOES["Destaque"]
TEXTO_ESCURO = {"Amarelo", "Destaque"}   # botões claros: texto e ícone escuros


def imagem_aba(larg, alt, fundo, linha=None):
    """Aba lisa; a selecionada ganha um traço embaixo."""
    im = Image.new("RGBA", (larg, alt), _rgba(fundo))
    if linha:
        ImageDraw.Draw(im).rectangle((6, alt - 3, larg - 7, alt - 1), fill=_rgba(linha))
    return im


def dourar(im):
    """Troca os tons de azul de uma imagem por dourado (o tema sv_ttk vem em azul)."""
    import colorsys
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if 0.5 <= h <= 0.66 and s > 0.3:
                r2, g2, b2 = colorsys.hsv_to_rgb(41 / 360, min(1.0, s * 1.2), v)
                px[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), a)
    return im


def icone_arredondado(img, T, raio, fundo=None, brilho=None, cinza=False):
    """Ícone no tamanho T com cantos arredondados. Com fundo conhecido (caixa escura) a borda
    fica suave; sem fundo, os cantos viram a cor transparente da janela (sem serrilhado escuro)."""
    im = img.convert("RGB")
    k = max(1, -(-T // max(1, im.width)))         # amplia em pixels inteiros e reduz liso
    im = im.resize((im.width * k, im.height * k), Image.NEAREST).resize((T, T), Image.LANCZOS)
    if cinza:
        im = im.convert("L").convert("RGB")
    if brilho is not None:
        im = ImageEnhance.Brightness(im).enhance(brilho)
    im = sem_cor_chave(im)
    E = 4
    mascara = Image.new("L", (T * E, T * E), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, T * E - 1, T * E - 1), radius=raio * E, fill=255)
    mascara = mascara.resize((T, T), Image.LANCZOS)
    if fundo is None:
        mascara = mascara.point(lambda v: 255 if v >= 128 else 0)
        base = Image.new("RGB", (T, T), (1, 1, 1))
    else:
        base = Image.new("RGB", (T, T), fundo)
    base.paste(im, (0, 0), mascara)
    return base


def misturar_cor(a, b, t):
    """Mistura duas cores "#rrggbb" (t=0 -> a, t=1 -> b)."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def ret_arred(c, x0, y0, x1, y1, r, **kw):
    """Retângulo de cantos arredondados no canvas."""
    r = max(1, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def contorno_arred(c, x0, y0, x1, y1, raio, cor):
    """Contorno com a mesma curva da faixa_degrade (o smooth do Tk sai mais quadrado e deixa
    um canto vazado entre a borda e o preenchimento)."""
    raio = min(raio, (y1 - y0) / 2, (x1 - x0) / 2)
    pts = []
    for cx, cy, a0 in ((x1 - raio, y0 + raio, -90), (x1 - raio, y1 - raio, 0),
                       (x0 + raio, y1 - raio, 90), (x0 + raio, y0 + raio, 180)):
        for k in range(9):
            a = math.radians(a0 + k * 90 / 8)
            pts += [cx + raio * math.cos(a), cy + raio * math.sin(a)]
    return c.create_polygon(pts, fill="", outline=cor, width=1)


def faixa_degrade(c, x0, y0, x1, y1, raio, cor_em):
    """Retângulo (de pontas redondas se raio > 0) com degradê de cima para baixo, desenhado
    linha a linha no canvas. cor_em(t) dá a cor na altura t (0 = topo, 1 = base)."""
    h = int(round(y1 - y0))
    raio = min(raio, h / 2, (x1 - x0) / 2)
    for i in range(h):
        y = y0 + i + 0.5
        recuo = 0.0
        if raio:
            dy = abs(y - (y0 + h / 2)) - (h / 2 - raio)
            if dy > 0:
                recuo = raio - math.sqrt(max(0.0, raio * raio - dy * dy))
        if x1 - recuo > x0 + recuo:
            c.create_line(x0 + recuo, y, x1 - recuo, y, fill=cor_em(i / max(1, h - 1)))


def texto_contorno(canvas, x, y, texto, fonte, cor):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        canvas.create_text(x + dx, y + dy, text=texto, font=fonte, fill="#000000")
    canvas.create_text(x, y, text=texto, font=fonte, fill=cor)
