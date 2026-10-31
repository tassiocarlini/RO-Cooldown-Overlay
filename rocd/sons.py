"""Sons de aviso (gerados, seus e do MyInstants), tocados pelo Windows (MCI)."""

import ctypes
import math
import re
import struct
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import wave
from html import unescape
from pathlib import Path

from .config import PASTA_MEUS_SONS, PASTA_SONS, SEM_SOM, SONS_PRONTOS, VERSAO, registrar


# =============================================================== sons de aviso

def baixar_myinstants(link):
    """Link de um som do MyInstants (a página do som ou o próprio .mp3) -> (nome, bytes do mp3)."""
    link = (link or "").strip()
    if not re.match(r"^https?://", link, re.I):
        link = "https://" + link
    do_site = lambda u: re.match(r"^https?://([a-z0-9-]+\.)*myinstants\.com/", u, re.I)
    if not do_site(link):
        raise ValueError("cole um link do myinstants.com")
    try:
        return _baixar_myinstants(link, do_site)
    except urllib.error.HTTPError as e:
        raise ValueError(f"o MyInstants respondeu erro {e.code} (o som não existe ou saiu do ar)")


def _baixar_myinstants(link, do_site):
    cab = {"User-Agent": f"Mozilla/5.0 (RO-Cooldown-Overlay/{VERSAO})"}
    nome = ""
    if not urllib.parse.urlparse(link).path.lower().endswith(".mp3"):
        with urllib.request.urlopen(urllib.request.Request(link, headers=cab), timeout=20) as r:
            pagina = r.read(2_000_000).decode("utf-8", errors="replace")
        m = (re.search(r'property="og:audio"\s+content="([^"]+?\.mp3)"', pagina) or
             re.search(r"""(/media/sounds/[^"'\s]+?\.mp3)""", pagina))
        if not m:
            raise ValueError("não achei o som nessa página")
        link = urllib.parse.urljoin(link, m.group(1))
        if not do_site(link):
            raise ValueError("o som dessa página não está no myinstants.com")
        t = re.search(r'id="instant-page-title"[^>]*>([^<]+)<', pagina)
        nome = unescape(t.group(1)).strip() if t else ""
    if not nome:
        nome = Path(urllib.parse.urlparse(link).path).stem.replace("-", " ").replace("_", " ")
    with urllib.request.urlopen(urllib.request.Request(link, headers=cab), timeout=30) as r:
        dados = r.read(3_000_001)
    if len(dados) > 3_000_000:
        raise ValueError("som grande demais (máximo 3 MB)")
    if not (dados[:3] == b"ID3" or (len(dados) > 1 and dados[0] == 0xFF and dados[1] & 0xE0 == 0xE0)):
        raise ValueError("o arquivo baixado não é um MP3")
    return nome, dados


class Sons:
    """Sons de aviso: os prontos são gerados pelo programa (.wav); os seus (.mp3/.wav) ficam
    em meus_sons. Tocados pelo MCI do Windows, sem travar o overlay e com volume."""
    TAXA = 22050
    INTERVALO = 0.35          # s: avisos colados viram um só

    def __init__(self):
        self._ultimo = -99.0
        self._abertos = {}    # chave -> apelido no MCI (aberto uma vez: a 1ª abertura é lenta)
        self._n = 0

    # ---- quais sons existem

    @staticmethod
    def meus():
        """Nome -> arquivo dos sons que você adicionou."""
        if not PASTA_MEUS_SONS.is_dir():
            return {}
        return {p.stem: p for p in sorted(PASTA_MEUS_SONS.iterdir(), key=lambda p: p.stem.lower())
                if p.suffix.lower() in (".mp3", ".wav")}

    def opcoes(self):
        """Nome na tela -> chave, na ordem das listas (chave None = sem som)."""
        out = {SEM_SOM: None}
        out.update({nome: chave for chave, (nome, _, _) in SONS_PRONTOS.items()})
        out.update({nome: "meu:" + nome for nome in self.meus()})
        return out

    def nome(self, chave):
        return next((n for n, c in self.opcoes().items() if c == chave and c), SEM_SOM)

    def existe(self, chave):
        if not chave:
            return False
        if chave.startswith("meu:"):
            return chave[4:] in self.meus()
        return chave in SONS_PRONTOS

    # ---- arquivos

    def _gerar(self, chave):
        arq = PASTA_SONS / f"{chave}.wav"
        if arq.exists():
            return arq
        PASTA_SONS.mkdir(parents=True, exist_ok=True)
        _, timbre, notas = SONS_PRONTOS[chave]
        amostras = []
        for f0, f1, dur, dec in notas:
            n = int(self.TAXA * dur)
            fase = 0.0
            for i in range(n):
                t = i / self.TAXA
                if not f0:
                    amostras.append(0)
                    continue
                fase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / self.TAXA
                v = math.sin(fase)
                if timbre == "sino":
                    v = 0.75 * v + 0.25 * math.sin(fase * 2.76)
                elif timbre == "quadrado":
                    v = 0.8 * v + 0.2 * math.sin(fase * 3)
                env = math.exp(-dec * t) * min(1.0, i / 120, (n - i) / 120)   # sem estalo
                amostras.append(int(26000 * v * env))
        with wave.open(str(arq), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.TAXA)
            w.writeframes(struct.pack(f"<{len(amostras)}h", *amostras))
        return arq

    def _arquivo(self, chave):
        if chave.startswith("meu:"):
            return self.meus().get(chave[4:])
        return self._gerar(chave)

    @staticmethod
    def _mci(comando):
        """Manda um comando ao MCI; devolve o texto do erro (vazio = deu certo)."""
        codigo = ctypes.windll.winmm.mciSendStringW(comando, None, 0, None)
        if codigo == 0:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.winmm.mciGetErrorStringW(codigo, buf, 256)
        return buf.value or f"erro {codigo}"

    def _abrir(self, chave):
        apelido = self._abertos.get(chave)
        if apelido:
            return apelido
        arq = self._arquivo(chave)
        if arq is None:
            return None
        self._n += 1
        apelido = f"ro_som_{self._n}"
        erro = self._mci(f'open "{arq}" type mpegvideo alias {apelido}')
        if erro:
            registrar(f"Não consegui abrir o som {arq.name}: {erro}", chave_rep="som")
            return None
        self._abertos[chave] = apelido
        return apelido

    def preparar(self, chaves):
        """Abre os sons antes de precisar, para o primeiro aviso não atrasar.
        Devolve False se algum som que existe não abriu (arquivo com defeito)."""
        ok = True
        for chave in chaves:
            if self.existe(chave) and self._abrir(chave) is None:
                ok = False
        return ok

    def esquecer(self, chave):
        """Fecha o som (o arquivo fica livre para apagar ou trocar)."""
        apelido = self._abertos.pop(chave, None)
        if apelido:
            self._mci(f"close {apelido}")

    def tocar(self, chave, volume, forcar=False):
        """Toca o som; devolve False se ele não existe."""
        agora = time.monotonic()
        if not self.existe(chave):
            return False
        if volume <= 0 or (not forcar and agora - self._ultimo < self.INTERVALO):
            return True
        self._ultimo = agora
        try:
            apelido = self._abrir(chave)
            if apelido:
                self._mci(f"setaudio {apelido} volume to {int(volume * 10)}")
                self._mci(f"play {apelido} from 0")
        except Exception:
            registrar("Erro ao tocar som:\n" + traceback.format_exc(), chave_rep="som")
        return True
