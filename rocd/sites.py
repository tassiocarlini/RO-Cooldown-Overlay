"""Divine Pride (API) e ragassets do latam-tools: recargas e ícones."""

import io
import json
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from .config import DP_URL, DP_URL_EFST, PASTA, PASTA_DP, VERSAO, registrar
from .dados import extrair_recarga


class DivinePride:
    """Busca recarga e ícone de cada skill que você usa (servidor LATAM) e guarda no PC.
    Só pede à API as skills dos seus perfis, uma por vez e com cache, como a API pede."""

    def __init__(self, chave_api):
        self.chave = (chave_api or "").strip()
        self.fila = queue.Queue()
        self.pedidos = queue.Queue()
        self.cds = {}
        PASTA_DP.mkdir(exist_ok=True)
        self.nomes = {}
        for arq in PASTA_DP.glob("skill_*.json"):
            try:
                sid = int(arq.stem.split("_")[1])
                dados = json.loads(arq.read_text(encoding="utf-8"))
                cd = extrair_recarga(dados)
                if cd:
                    self.cds[sid] = cd
                if isinstance(dados, dict) and dados.get("name"):
                    self.nomes[sid] = dados["name"]
            except Exception:
                pass
        self._ultimo = 0.0
        threading.Thread(target=self._trabalhar, daemon=True).start()

    def ativo(self):
        return bool(self.chave)

    def icone(self, sid):
        p = PASTA_DP / f"icone_{sid}.png"
        return p if sid and p.exists() else None

    def pedir(self, sid, motivo):
        if sid and (self.ativo() or (PASTA_DP / f"skill_{sid}.json").exists()):
            self.pedidos.put((int(sid), motivo))

    def icone_efst(self, eid):
        p = PASTA_DP / f"efst_icone_{eid}.png"
        return p if p.exists() else None

    def pedir_efst(self, eid, chave_esperada, motivo):
        """Ícone de um buff (status). Confere se o id da Divine Pride é mesmo o esperado."""
        if self.ativo() or self.icone_efst(eid):
            self.pedidos.put((("efst", int(eid), chave_esperada), motivo))

    def _trabalhar_efst(self, eid, esperada, motivo):
        arq = PASTA_DP / f"efst_{eid}.json"
        ico = PASTA_DP / f"efst_icone_{eid}.png"
        try:
            if arq.exists():
                dados = json.loads(arq.read_text(encoding="utf-8"))
            else:
                if not self.ativo():
                    raise ValueError("sem chave da API")
                url = DP_URL_EFST.format(id=eid) + "?apiKey=" + urllib.parse.quote(self.chave)
                dados = self._abrir(url)
                registrar(f"Divine Pride: buff {eid} recebido: "
                          + json.dumps(dados, ensure_ascii=False)[:1000])
                chave_site = str(dados.get("key") or "") if isinstance(dados, dict) else ""
                if esperada and chave_site and chave_site.upper() != esperada.upper():
                    raise ValueError(f"o ícone {eid} na Divine Pride é {chave_site}, "
                                     f"não {esperada}")
                arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            url_ico = dados.get("iconUrl") if isinstance(dados, dict) else None
            if url_ico and not ico.exists() and self.ativo():
                ico.write_bytes(self._abrir(url_ico, json_=False))
            if not ico.exists():
                raise ValueError("ícone não disponível")
            self.fila.put(("ok", ("efst", eid), None, motivo, dados.get("name")))
        except Exception as e:
            registrar(f"Divine Pride: erro no buff {eid}: {e}")
            self.fila.put(("erro", ("efst", eid), str(e), motivo, None))

    def _abrir(self, url, json_=True):
        req = urllib.request.Request(url, headers={
            "Accept-Language": "pt", "x-server": "LATAM",
            "User-Agent": "RO-Cooldown-Overlay/1.0 (ferramenta pessoal)"})
        for tentativa in range(3):
            espera = 1.2 - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    dados = r.read()
                return json.loads(dados.decode("utf-8")) if json_ else dados
            except urllib.error.HTTPError as e:
                if e.code == 429 and tentativa < 2:
                    time.sleep(min(60, int(e.headers.get("Retry-After") or 10)))
                    continue
                if e.code == 401:
                    raise ValueError("chave da API inválida (401)")
                if e.code == 404:
                    raise ValueError("skill não encontrada na Divine Pride (404)")
                raise ValueError(f"erro HTTP {e.code}")
        raise ValueError("limite de pedidos da API; tente mais tarde")

    def _trabalhar(self):
        while True:
            sid, motivo = self.pedidos.get()
            if isinstance(sid, tuple):                      # ícone de buff
                self._trabalhar_efst(sid[1], sid[2], motivo)
                continue
            arq = PASTA_DP / f"skill_{sid}.json"
            try:
                if arq.exists() and time.time() - arq.stat().st_mtime < 30 * 86400:
                    dados = json.loads(arq.read_text(encoding="utf-8"))
                else:
                    if not self.ativo():
                        raise ValueError("sem chave da API")
                    url = DP_URL.format(id=sid) + "?apiKey=" + urllib.parse.quote(self.chave)
                    dados = self._abrir(url)
                    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
                    registrar(f"Divine Pride: skill {sid} recebida: "
                              + json.dumps(dados, ensure_ascii=False)[:2000])
                cd = extrair_recarga(dados)
                if cd:
                    self.cds[sid] = cd
                if isinstance(dados, dict) and dados.get("name"):
                    self.nomes[sid] = dados["name"]
                ico = PASTA_DP / f"icone_{sid}.png"
                url_ico = dados.get("iconUrl") if isinstance(dados, dict) else None
                if url_ico and not ico.exists() and self.ativo() and (motivo == "buscar" or motivo[:1] == ("visual",)):
                    ico.write_bytes(self._abrir(url_ico, json_=False))
                self.fila.put(("ok", sid, cd, motivo, dados.get("name") if isinstance(dados, dict) else None))
            except Exception as e:
                registrar(f"Divine Pride: erro na skill {sid}: {e}")
                self.fila.put(("erro", sid, str(e), motivo, None))


PASTA_RAG = PASTA / "cache_ragassets"
RAG_URL = "https://assets.latam-tools.com.br"


class RagAssets:
    """Fonte principal de ícones e nomes: ragassets (latam-tools), que tira tudo do próprio
    cliente LATAM. Não precisa de chave. Cada arquivo é baixado uma vez e guardado no PC.
    Se o servidor falhar ou não responder, fica 10 minutos sem tentar e o programa usa as
    outras fontes (Divine Pride, banco local, captura da tela)."""

    def __init__(self, ligado=True):
        self.ligado = ligado
        self.fila = queue.Queue()
        self.pedidos = queue.Queue()
        self.nomes = {}
        self.cds = {}
        self.estado = "ainda não usado"
        self._fora_ate = 0.0
        PASTA_RAG.mkdir(exist_ok=True)
        try:
            dados = json.loads((PASTA_RAG / "skills.json").read_text(encoding="utf-8"))
            self._ler_tabela(dados)
        except Exception:
            pass
        threading.Thread(target=self._trabalhar, daemon=True).start()

    def _ler_tabela(self, dados):
        """skills.json do cliente: nomes em português e recarga oficial no nível máximo."""
        nomes, cds = {}, {}
        for x in dados:
            sid = x.get("id")
            if not sid:
                continue
            if x.get("name"):
                nomes[int(sid)] = x["name"]
            cd = (x.get("delay") or {}).get("cooldown") or []
            if isinstance(cd, list) and cd and isinstance(cd[-1], (int, float)) and cd[-1] > 0:
                cds[int(sid)] = round(cd[-1] / 1000, 2)
        self.nomes, self.cds = nomes, cds

    def disponivel(self):
        return self.ligado and time.monotonic() >= self._fora_ate

    def icone_status(self, eid):
        p = PASTA_RAG / f"status_{eid}.png"
        return p if p.exists() else None

    def icone_skill(self, sid):
        p = PASTA_RAG / f"skill_{sid}.png"
        return p if sid and p.exists() else None

    def pedir(self, tipo, ident, motivo):
        """tipo: "status" (ícone de buff pelo id EFST), "skill" (ícone) ou "nomes"."""
        self.pedidos.put((tipo, ident, motivo))

    def _baixar(self, caminho, timeout=8):
        if not self.disponivel():
            raise ConnectionError("ragassets indisponível no momento")
        req = urllib.request.Request(RAG_URL + caminho, headers={
            "User-Agent": f"RO-Cooldown-Overlay/{VERSAO} (ferramenta pessoal)"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = r.read()
            self.estado = "funcionando"
            return dados
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError("não existe no ragassets")
            self._fora(f"erro HTTP {e.code}")
            raise
        except Exception as e:
            self._fora(str(e)[:80])
            raise

    def _fora(self, motivo):
        self._fora_ate = time.monotonic() + 600
        self.estado = "sem resposta agora; usando as outras fontes (detalhes no log)"
        registrar(f"ragassets: {motivo} — usando as outras fontes por 10 minutos.", chave_rep="rag")

    def _trabalhar(self):
        while True:
            tipo, ident, motivo = self.pedidos.get()
            try:
                if not self.ligado:
                    raise ConnectionError("ragassets desligado nas opções")
                if tipo == "nomes":
                    arq = PASTA_RAG / "skills.json"
                    if not arq.exists() or time.time() - arq.stat().st_mtime > 7 * 86400:
                        arq.write_bytes(self._baixar("/raw/skills.json", timeout=20))
                    dados = json.loads(arq.read_text(encoding="utf-8"))
                    self._ler_tabela(dados)
                else:
                    pasta_tipo = "status" if tipo == "status" else "skill"
                    arq = PASTA_RAG / f"{pasta_tipo}_{ident}.png"
                    if not arq.exists():
                        dados = self._baixar(f"/icons/{pasta_tipo}/{int(ident)}.png")
                        Image.open(io.BytesIO(dados)).load()          # confere que é imagem
                        arq.write_bytes(dados)
                self.fila.put(("ok", tipo, ident, motivo))
            except Exception as e:
                self.fila.put(("erro", tipo, ident, motivo, str(e)))


def icone_dp_rgb(caminho):
    """Ícone da Divine Pride (com transparência) sobre fundo escuro, em RGB."""
    im = Image.open(caminho).convert("RGBA")
    fundo = Image.new("RGBA", im.size, (40, 40, 48, 255))
    fundo.alpha_composite(im)
    return fundo.convert("RGB")
