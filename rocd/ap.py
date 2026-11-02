"""Leitura do número de AP na tela (reconhece os dígitos da fonte do jogo)."""

from PIL import Image

from .config import cv2, np


# ---------------------------------------------------------------- leitura do AP
# Desenho de cada dígito na fonte da interface do jogo (texto em 1 bit, 8 pixels de altura).
# O programa recorta a área marcada, separa os caracteres e compara com estes modelos.
FONTE_DIGITOS = {
    "/": ['..#', '..#', '.#.', '.#.', '.#.', '.#.', '#..', '#..'],
    "0": ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    "1": ['..#', '.##', '#.#', '..#', '..#', '..#', '..#', '..#'],
    "2": ['.###.', '#...#', '....#', '....#', '...#.', '..#..', '.#...', '#####'],
    "3": ['.###.', '#...#', '....#', '..##.', '....#', '....#', '#...#', '.###.'],
    "4": ['...#.', '..##.', '.#.#.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    "5": ['.####', '.#...', '#....', '####.', '....#', '....#', '#...#', '.###.'],
    "6": ['.###.', '#...#', '#....', '####.', '#...#', '#...#', '#...#', '.###.'],
    "7": ['#####', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...', '.#...'],
    "8": ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '#...#', '.###.'],
    "9": ['.###.', '#...#', '#...#', '#...#', '.####', '....#', '#...#', '.###.']
}
# Mesma coisa para a fonte menor usada DENTRO das barras de HP/SP/AP (7 pixels de altura).
# O desenho do 8 não aparecia nos prints e foi deduzido dos outros dígitos. O traço do 4
# passa da haste e encosta no dígito seguinte (ver _separar_colados).
FONTE_DIGITOS_BARRA = {
    "/": ['..#', '..#', '.#.', '.#.', '.#.', '#..', '#..'],
    "0": ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    "1": ['..#', '.##', '#.#', '..#', '..#', '..#', '..#'],
    "2": ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
    "3": ['.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'],
    "4": ['...##.', '..#.#.', '.#..#.', '#...#.', '######', '....#.', '....#.'],
    "5": ['.####', '.#...', '####.', '#...#', '....#', '#...#', '.###.'],
    "6": ['.###.', '#...#', '####.', '#...#', '#...#', '#...#', '.###.'],
    "7": ['#####', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...'],
    "8": ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
    "9": ['.###.', '#...#', '#...#', '#...#', '.####', '#...#', '.###.']
}
_MODELOS_DIGITOS = None


def _modelos_digitos():
    global _MODELOS_DIGITOS
    if _MODELOS_DIGITOS is None:
        _MODELOS_DIGITOS = [(k, np.array([[c == "#" for c in r] for r in v], dtype=bool))
                            for fonte in (FONTE_DIGITOS, FONTE_DIGITOS_BARRA)
                            for k, v in fonte.items()]
    return _MODELOS_DIGITOS


def _glifos(mascara):
    """Separa os caracteres por colunas vazias: [(x, largura, desenho recortado)]."""
    cols = mascara.any(axis=0)
    res, x, W = [], 0, mascara.shape[1]
    while x < W:
        if not cols[x]:
            x += 1
            continue
        ini = x
        while x < W and cols[x]:
            x += 1
        sub = mascara[:, ini:x]
        linhas = np.nonzero(sub.any(axis=1))[0]
        res.append((ini, x - ini, sub[linhas.min():linhas.max() + 1]))
    return res


def _sem_linhas(mascara, comprimento=20):
    """Apaga traços horizontais longos (bordas de barras e janelas), que não são texto.
    O traço de "444" colado já dá 18 pixels, por isso o limite não é menor."""
    m = mascara.copy()
    for y in range(m.shape[0]):
        linha = m[y]
        if linha.sum() < comprimento:
            continue
        x, W = 0, linha.shape[0]
        while x < W:
            if not linha[x]:
                x += 1
                continue
            ini = x
            while x < W and linha[x]:
                x += 1
            if x - ini >= comprimento:
                m[y, ini:x] = False
    return m


def _faixas(mascara):
    """Separa as linhas de texto (faixas de linhas com pixels, entre linhas vazias)."""
    linhas = mascara.any(axis=1)
    res, y, H = [], 0, mascara.shape[0]
    while y < H:
        if not linhas[y]:
            y += 1
            continue
        ini = y
        while y < H and linhas[y]:
            y += 1
        res.append(mascara[ini:y])
    return res


def _classificar(g):
    """Qual dígito (ou "/") é este desenho? None se não parecer nenhum."""
    qual, dif = _parecido(g)
    return qual if dif <= 0.18 else None


def _parecido(g):
    """O modelo mais parecido com este desenho e quanto difere: (caractere, 0..1)."""
    h, w = g.shape
    if h < 5 or h > 40 or w > 12:
        return None, 1.0
    melhor, qual = 1.0, None
    for ch, t in _modelos_digitos():
        th, tw = t.shape
        if (th, tw) == (h, w):                          # mesmo tamanho: compara pixel a pixel
            dif = float((g != t).mean())
        else:
            if abs(w * th / h - tw) > 1.2:             # proporção bem diferente
                continue
            r = np.asarray(Image.fromarray(g.astype(np.uint8) * 255).resize((tw, th),
                                                                          Image.NEAREST)) > 127
            dif = float((r != t).mean()) + 0.04        # tamanho diferente: confia um pouco menos
        if dif < melhor:
            melhor, qual = dif, ch
    return qual, melhor


def _aparar(g):
    """Tira colunas e linhas vazias das bordas: (deslocamento x, desenho) ou None se vazio."""
    cols, linhas = np.nonzero(g.any(axis=0))[0], np.nonzero(g.any(axis=1))[0]
    if not len(cols):
        return None
    return int(cols[0]), g[linhas[0]:linhas[-1] + 1, cols[0]:cols[-1] + 1]


def _partir(g, nivel=2):
    """Corta um desenho com dígitos colados no ponto em que todas as partes parecem dígitos.
    Devolve [(deslocamento x, desenho)] ou None."""
    melhor, res = 0.18 * nivel, None
    for c in range(3, g.shape[1] - 2):
        esq, dir_ = _aparar(g[:, :c]), _aparar(g[:, c:])
        if esq is None or dir_ is None:
            continue
        q, d = _parecido(esq[1])
        if q is None or q == "/" or d > 0.18:
            continue
        partes, soma = [(esq[0], esq[1])], d
        q, d = _parecido(dir_[1])
        if q is not None and q != "/" and d <= 0.18:
            partes.append((c + dir_[0], dir_[1]))
            soma += d
        elif nivel > 1 and dir_[1].shape[1] >= 7:
            resto = _partir(dir_[1], nivel - 1)
            if not resto:
                continue
            partes += [(c + dir_[0] + dx, p) for dx, p in resto]
            soma += sum(_parecido(p)[1] for _, p in resto)
        else:
            continue
        if soma < melhor:
            melhor, res = soma, partes
    return res


def _separar_colados(gl):
    """Dígitos colados viram um desenho só (ex.: o traço do "4" encosta no "0" de "140");
    separa os que não parecem nada em partes que pareçam dígitos."""
    res = []
    for x, w, g in gl:
        partes = _partir(g) if w >= 7 and _classificar(g) is None else None
        if partes:
            res.extend((x + dx, p.shape[1], p) for dx, p in partes)
        else:
            res.append((x, w, g))
    return res


# Rótulo "AP" da janela Informações básicas (mesma fonte, texto preto): usado para achar a
# linha do AP sozinho, em qualquer lugar da tela, nos dois modos da janela.
ROTULO_AP = ['...#....####.', '..#.#...#...#', '..#.#...#...#', '..#.#...#...#', '.#...#..####.', '.#####..#....', '#.....#.#....', '#.....#.#....']


def achar_rotulos_ap(arr, maximo=12):
    """Todos os lugares onde aparece o rótulo "AP" (texto preto), do canto superior esquerdo
    para baixo/direita — a janela Informações básicas costuma ficar ali."""
    if cv2 is None:
        return []
    preto = (np.asarray(arr)[..., :3].max(axis=2) < 60).astype(np.uint8) * 255
    t = np.array([[c == "#" for c in r] for r in ROTULO_AP], dtype=np.uint8) * 255
    if preto.shape[0] < t.shape[0] or preto.shape[1] < t.shape[1]:
        return []
    r = cv2.matchTemplate(preto, t, cv2.TM_SQDIFF) / (255 * 255)
    ys, xs = np.nonzero(r <= 3)                         # até 3 pixels diferentes
    locais = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: (p[0] + p[1], p[1]))
    res = []
    for x, y in locais:                                 # junta acertos vizinhos
        if all(abs(x - a) > 3 or abs(y - b) > 3 for a, b in res):
            res.append((x, y))
        if len(res) >= maximo:
            break
    return res


def achar_rotulo_ap(arr):
    """O primeiro rótulo "AP" (mais perto do canto superior esquerdo), ou None."""
    locais = achar_rotulos_ap(arr, maximo=1)
    return locais[0] if locais else None


def localizar_ap(arr):
    """Acha a linha do AP que dá para ler: testa cada rótulo "AP" encontrado (o primeiro pode
    ser outro texto). Devolve ((x, y) do rótulo, (atual, máximo)) ou (None, None)."""
    for x, y in achar_rotulos_ap(arr):
        trecho = arr[max(0, y - 3):y + 12, x + 13:x + 13 + 190]
        lido = ler_fracao(trecho)
        if lido:
            return (x, y), lido
    return None, None


def ler_fracao(arr):
    """Lê "atual / máximo" (ex.: 53 / 200) de um recorte da tela. Devolve (atual, máximo) ou None."""
    a = np.asarray(arr)[..., :3]
    lum = a.mean(axis=2)
    # 1º: só pixels pretos (o texto do jogo é preto puro; a borda azul do preenchimento
    #     da barra, que às vezes passa por cima dos números, não entra)
    for mascara_toda in (a.max(axis=2) < 60, lum < 100, lum > 170):
        if mascara_toda.mean() > 0.5:
            continue
        for mascara in _faixas(_sem_linhas(mascara_toda)):   # cada linha de texto separada
            lido = _ler_linha(mascara)
            if lido:
                return lido
    # 2º: skins em que o preenchimento da barra tem borda preta (linha de baixo e coluna da
    #     ponta) passando por cima dos números
    preto = a.max(axis=2) < 60
    if preto.mean() <= 0.5:
        for mascara in _faixas(_reparar(preto)):
            lido = _ler_linha(mascara)
            if lido:
                return lido
    return None


def _moldura(mascara, comprimento=20):
    """Pixels que podem ser da moldura da barra: traços horizontais longos e os traços
    verticais altos que encostam neles (a ponta do preenchimento)."""
    H, W = mascara.shape
    horiz = np.zeros_like(mascara)
    for y in range(H):
        x = 0
        while x < W:
            if not mascara[y, x]:
                x += 1
                continue
            ini = x
            while x < W and mascara[y, x]:
                x += 1
            if x - ini >= comprimento:
                horiz[y, ini:x] = True
    res = horiz.copy()
    for x in range(W):
        y = 0
        while y < H:
            if not mascara[y, x]:
                y += 1
                continue
            ini = y
            while y < H and mascara[y, x]:
                y += 1
            if y - ini >= 8 and horiz[max(0, ini - 1):min(H, y + 1), x].any():
                res[ini:y, x] = True
    return res


def _correlacao(img, t):
    """Soma de img * t em cada posição em que t cabe inteiro em img."""
    if cv2 is not None:
        return cv2.matchTemplate(img, t, cv2.TM_CCORR)
    janelas = np.lib.stride_tricks.sliding_window_view(img, t.shape)
    return np.einsum("ijkl,kl->ij", janelas, t)


def _reparar(mascara):
    """Tira a moldura da barra e, onde ela passa por cima de um dígito, completa o dígito com o
    modelo que melhor combina com o resto dele."""
    incerto = _moldura(mascara)
    conhecido = ~incerto
    limpo = mascara & conhecido
    if not incerto.any():
        return limpo
    H, W = mascara.shape
    tinta, vazio, visto = (np.float32(m) for m in (limpo, conhecido & ~mascara, conhecido))
    cands = []
    for ch, t in _modelos_digitos():
        th, tw = t.shape
        if th + 2 > H or tw + 2 > W:
            continue
        tf = np.float32(t)
        n_k = _correlacao(visto, np.ones_like(tf))
        dif = (_correlacao(tinta, 1 - tf) + _correlacao(vazio, tf)) / np.maximum(n_k, 1)
        tinta_vista = _correlacao(visto, tf) / tf.sum()
        ok = (dif <= 0.1) & (tinta_vista >= 0.4) & (n_k < th * tw - 0.5)   # cobre algo incerto
        for y, x in zip(*np.nonzero(ok)):
            if y == 0 or x == 0 or y + th >= H or x + tw >= W:
                continue
            # em volta do dígito não pode haver tinta (senão é pedaço de outro desenho)
            borda = np.concatenate([limpo[y:y + th, x - 1], limpo[y:y + th, x + tw],
                                    limpo[y - 1, x:x + tw], limpo[y + th, x:x + tw]])
            if borda.sum() <= 1:
                cands.append((float(dif[y, x]), -int(t.sum()), int(y), int(x), t))
    res = limpo.copy()
    ocupado = np.zeros_like(mascara)
    for _, _, y, x, t in sorted(cands, key=lambda c: c[:4]):
        th, tw = t.shape
        if ocupado[y:y + th, x:x + tw].any():
            continue
        ocupado[y:y + th, x:x + tw] = True
        inc = incerto[y:y + th, x:x + tw]
        res[y:y + th, x:x + tw][inc] = t[inc]
    return res


def _ler_linha(mascara):
    """Procura "número / número" numa linha de texto."""
    if True:
        gl = _separar_colados(_glifos(mascara))
        if not gl:
            return None
        tipos = [_classificar(g) for _, _, g in gl]
        alturas = sorted(g.shape[0] for (_, _, g), t in zip(gl, tipos) if t not in (None, "/"))
        altura = alturas[len(alturas) // 2] if alturas else 8
        junto = max(3, int(altura * 0.6))            # espaço entre dígitos do mesmo número

        def numero(indices):
            if not indices or any(tipos[i] in (None, "/") for i in indices):
                return None
            # desenho que não parece nada colado ao número: falta um dígito (ex.: a borda da
            # barra cortou o 6 de "67" e sobrou só o 7)
            ini, fim = indices[0], indices[-1]
            if ini > 0 and tipos[ini - 1] is None and \
                    gl[ini][0] - (gl[ini - 1][0] + gl[ini - 1][1]) <= junto:
                return None
            if fim + 1 < len(gl) and tipos[fim + 1] is None and \
                    gl[fim + 1][0] - (gl[fim][0] + gl[fim][1]) <= junto:
                return None
            return int("".join(tipos[i] for i in indices))

        for k, t in enumerate(tipos):
            if t != "/":
                continue
            esq, i = [], k - 1
            while i >= 0 and tipos[i] not in (None, "/"):
                fim_ant = gl[i][0] + gl[i][1]
                prox_ini = gl[esq[0]][0] if esq else None
                if prox_ini is not None and prox_ini - fim_ant > junto:
                    break
                esq.insert(0, i)
                i -= 1
            dir_, i = [], k + 1
            while i < len(gl) and tipos[i] not in (None, "/"):
                if dir_ and gl[i][0] - (gl[dir_[-1]][0] + gl[dir_[-1]][1]) > junto:
                    break
                dir_.append(i)
                i += 1
            atual, maximo = numero(esq), numero(dir_)
            if atual is not None and maximo and 0 <= atual <= maximo <= 10_000_000:
                return atual, maximo
        return None
