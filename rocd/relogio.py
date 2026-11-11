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


# ------------------------------------------------- tempo automático (BETA)

AUTO_SALTO = 0.08          # véu a mais de 8% da volta do esperado: renovado (ou outro nível)
AUTO_COMECO = 0.10         # 1ª leitura acima disso: o buff não começou agora (já estava ativo)
AUTO_FAIXA_ANCORA = 0.08   # viu o buff começar: o véu precisa passar disso para dar a 1ª medida
AUTO_FAIXA_LIVRE = 0.15    # não viu começar: o véu precisa andar isso
AUTO_ERRO_LEITURA = 0.02   # erro típico de uma leitura do véu (uns 7 graus)
AUTO_TOL_MIN = 0.05        # medida a até 5% de uma duração já vista = é ela
AUTO_PONTOS = 160          # leituras guardadas (as antigas vão sendo juntadas de duas em duas)
AUTO_FIM = 0.85            # o véu passou disso antes de sumir: o buff acabou sozinho


class RelogioAuto:
    """Mede a duração de um buff pela velocidade do véu do ícone, sem saber o nível da skill.

    Cada leitura diz que fração do buff já passou. A reta que liga hora e fração dá a duração
    (o tempo de uma volta inteira) e a hora em que o buff começou. No começo a medida é
    grosseira (o véu andou pouco); ela melhora conforme o buff anda. Se a medida bate com uma
    duração já vista até o fim (conhecidas), usa essa, que é exata.

    inicio/duracao: a melhor conta até agora (duracao None = ainda sem medida nem palpite).
    aprox: True quando a duração vem só da medida do véu."""

    def __init__(self, visto, viu_comecar, conhecidas=()):
        self.conhecidas = [d for d in conhecidas if d]   # a última é o palpite inicial
        self._zerar(visto, viu_comecar)

    def _zerar(self, visto, viu_comecar):
        self.ancora = visto if viu_comecar else None     # hora certa em que o buff começou
        self.pontos = []                                 # [hora, fração, peso]
        self.medida = None                               # (início, duração) pela reta
        self.inicio = visto
        self.duracao = self.conhecidas[-1] if self.conhecidas else None
        self.aprox = False
        self.maior_f = 0.0
        self._fora = []
        self._leu = False

    def ler(self, t, f):
        """Leitura nova do véu. Devolve True se o buff foi renovado (o véu pulou)."""
        if self.medida:
            esp = (t - self.medida[0]) / self.medida[1]
            pulou = abs(f - esp) > AUTO_SALTO
        else:
            pulou = bool(self.pontos) and f < self.pontos[-1][1] - AUTO_SALTO
        if pulou:
            self._fora.append((t, f))
            if len(self._fora) < 3:                      # uma leitura torta não renova nada
                return False
            fora = self._fora
            self._zerar(fora[0][0], all(x[1] == 0 for x in fora))
            for tt, ff in fora:
                self._somar(tt, ff)
            self._ajustar()
            return True
        self._fora = []
        self._somar(t, f)
        self._ajustar()
        return False

    def _somar(self, t, f):
        if not self._leu and f > AUTO_COMECO:
            self.ancora = None                           # já apareceu com o véu andado
        self._leu = True
        self.maior_f = max(self.maior_f, f)
        if f <= 0:                                       # começo do buff: véu ainda ilegível
            return
        self.pontos.append([t, f, 1.0])
        if len(self.pontos) > AUTO_PONTOS:
            p, juntos = self.pontos, []
            for a, b in zip(p[0::2], p[1::2]):
                w = a[2] + b[2]
                juntos.append([(a[0] * a[2] + b[0] * b[2]) / w,
                               (a[1] * a[2] + b[1] * b[2]) / w, w])
            self.pontos = juntos + p[len(p) - len(p) % 2:]

    def _ajustar(self):
        self.medida = None
        faixa = 0.0
        if len(self.pontos) >= 3:
            t, f, w = np.array(self.pontos, dtype=np.float64).T
            if self.ancora is not None:                  # reta presa na hora em que começou
                faixa = float(f.max())
                if faixa >= AUTO_FAIXA_ANCORA:
                    self.medida = (self.ancora,
                                   float((w * (t - self.ancora) * f).sum() / (w * f * f).sum()))
            else:
                faixa = float(f.max() - f.min())
                if faixa >= AUTO_FAIXA_LIVRE:
                    fm, tm = np.average(f, weights=w), np.average(t, weights=w)
                    d = float((w * (f - fm) * (t - tm)).sum() / (w * (f - fm) ** 2).sum())
                    self.medida = (float(tm - d * fm), d)
            if self.medida and not 1.0 <= self.medida[1] <= 86400.0:
                self.medida = None
        if self.medida:
            d = self.medida[1]
            tol = max(AUTO_TOL_MIN, AUTO_ERRO_LEITURA / faixa)
            perto = min(self.conhecidas, key=lambda c: abs(c - d), default=None)
            if perto and abs(perto - d) <= tol * perto:
                self.duracao, self.aprox = perto, False
            else:
                self.duracao, self.aprox = d, True
        if not self.duracao:
            return
        if self.ancora is not None:
            self.inicio = self.ancora
        elif self.pontos:
            t, f, w = np.array(self.pontos, dtype=np.float64).T
            self.inicio = float(np.average(t - f * self.duracao, weights=w))

    def duracao_vista(self, fim):
        """O ícone sumiu às `fim`. Devolve a duração exata (segundos inteiros) se o programa
        viu o buff do começo ao fim e ele acabou sozinho; senão None (ex.: foi removido)."""
        if self.ancora is None or self.maior_f < AUTO_FIM or not self.medida:
            return None
        d = fim - self.ancora
        # perto do fim a medida do véu erra uns 3%: sumiu antes disso = morreu ou foi removido
        if abs(d - self.medida[1]) > AUTO_TOL_MIN * self.medida[1]:
            return None
        return float(round(d)) if d >= 1 else None
