"""Banco de skills, leitura e gravação de JSON, formatação de tempos."""

import copy
import json
import math
import re
import unicodedata

from .config import ARQ_BANCO, ARQ_MEUS, TODAS
from .consumiveis import CONSUMIVEIS, GRUPO


def ler_tempo(txt):
    """'12' / '4,5' / '1:30' -> segundos. Vazio -> None (aprender). Retorna (valor, valido)."""
    t = txt.strip().replace(",", ".")
    if not t:
        return None, True
    try:
        if ":" in t:
            m, s = t.split(":", 1)
            v = int(m) * 60 + float(s)
        else:
            v = float(t)
    except ValueError:
        return None, False
    return (v, True) if v > 0 else (None, False)


def fmt_tempo(v):
    return "" if v is None else f"{v:g}"


def fmt_duracao(seg):
    """1800 -> "30 min", 90 -> "1:30", 10 -> "10 s", 3600 -> "1 h"."""
    if seg >= 3600 and seg % 3600 == 0:
        return f"{seg // 3600:g} h"
    if seg >= 60 and seg % 60 == 0:
        return f"{seg // 60:g} min"
    if seg >= 60:
        return fmt_contagem(seg)
    return f"{seg:g} s"


def fmt_contagem(seg):
    """Segundos que faltam -> "4:59" (arredonda para cima: só mostra 0:00 quando acabou)."""
    s = max(0, math.ceil(seg - 1e-6))
    return f"{s // 60}:{s % 60:02d}"


def fmt_aprendido(sk):
    if sk.get("cd"):
        return "usa manual"
    v = sk.get("aprendido")
    return "—" if v is None else f"{v:.1f}s"


def mesclar(padrao, dados):
    out = {}
    for k, v in padrao.items():
        if isinstance(v, dict):
            sub = dados.get(k) if isinstance(dados.get(k), dict) else {}
            out[k] = mesclar(v, sub)
        else:
            out[k] = copy.deepcopy(dados.get(k, v))
    for k, v in dados.items():
        out.setdefault(k, v)
    return out


def ler_json(arq, padrao):
    try:
        return {**padrao, **json.loads(arq.read_text(encoding="utf-8"))}
    except Exception:
        return dict(padrao)


def gravar_json(arq, dados):
    arq.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


# =============================================================== banco de skills

def chave(txt):
    """Normaliza para busca: sem acento, minúsculo."""
    t = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


class Banco:
    def __init__(self):
        self.itens = {}
        self.classes = []
        self.fonte = ""
        try:
            self.meus = json.loads(ARQ_MEUS.read_text(encoding="utf-8"))
        except Exception:
            self.meus = {}
        try:
            dados = json.loads(ARQ_BANCO.read_text(encoding="utf-8"))
        except Exception:
            dados = {}
        self.fonte = dados.get("fonte", "")
        self.por_id = {}
        for classe, lista in dados.get("classes", {}).items():
            self.classes.append(classe)
            for x in lista:
                it = self.por_id.get(x.get("id")) if x.get("id") else None
                if it is None:
                    nome = x.get("nome") or x.get("en")
                    k = chave(nome)
                    if not k:
                        continue
                    it = self.itens.get(k)
                    if it is None:
                        it = {"nome": nome, "pt": bool(x.get("nome")), "en": x.get("en") or "",
                              "cd": None, "classes": [], "id": x.get("id"),
                              "efst": x.get("efst") or [],
                              # buff = dá ícone de status e não causa dano (aba Buffs);
                              # o resto é skill ofensiva (aba Skills ofensivas)
                              "buff": x.get("buff", bool(x.get("efst")))}
                        self.itens[k] = it
                        if x.get("en"):
                            self.itens.setdefault(chave(x["en"]), it)
                    if it["id"]:
                        self.por_id[it["id"]] = it
                if classe not in it["classes"]:
                    it["classes"].append(classe)
                if it["cd"] is None and x.get("cd"):
                    it["cd"] = x["cd"]
        for nome, ids, dur in CONSUMIVEIS:             # poções, comidas...: buffs de todas as classes
            self.itens.setdefault(chave(nome), {
                "nome": nome, "pt": True, "en": "", "cd": None, "classes": [GRUPO], "id": None,
                "efst": [["", i] for i in ids], "buff": True, "consumivel": True,
                "duracao": dur})
        self.classes.sort(key=chave)                   # ordem alfabética, sem ligar para acentos
        for it in self.itens.values():
            it["classes"].sort(key=chave)
        self.ok = bool(self.itens)
        self.dp = None

    def definir_nome(self, sid, nome):
        """Nome em português (vindo da Divine Pride) para uma skill que só tinha nome em inglês."""
        it = self.por_id.get(sid)
        if not it or it["pt"] or not nome:
            return False
        it["nome"], it["pt"] = nome.strip(), True
        self.itens.setdefault(chave(it["nome"]), it)
        return True

    def aplicar_nomes(self, nomes):
        return sum(self.definir_nome(sid, n) for sid, n in nomes.items())

    def sem_nome_pt(self, classe):
        return [it["id"] for it in self.por_id.values()
                if not it["pt"] and (classe == TODAS or classe in it["classes"])]

    def efst_de(self, nome):
        """Ícones de status (buff) da skill: lista de [chave, id]."""
        it = self.itens.get(chave(nome))
        return it.get("efst") or [] if it else []

    def duracao_de(self, nome):
        """Duração conhecida do buff em segundos (consumíveis), ou None."""
        it = self.itens.get(chave(nome))
        return it.get("duracao") if it else None

    def eh_buff(self, nome):
        """A skill é buff (vai na aba Buffs, não na de skills ofensivas)?"""
        it = self.itens.get(chave(nome))
        return bool(it and it.get("buff"))

    def id_de(self, nome):
        it = self.itens.get(chave(nome))
        return it.get("id") if it else None

    def recarga_padrao(self, nome):
        it = self.itens.get(chave(nome))
        return it["cd"] if it else None

    def recarga(self, nome):
        """(segundos, origem): 'sua' (corrigida por você) > 'LATAM' (cliente, via ragassets)
        > 'LATAM' (Divine Pride) > 'padrão' (rAthena)."""
        k = chave(nome)
        m = self.meus.get(k)
        if m and m.get("cd"):
            return m["cd"], "sua"
        it = self.itens.get(k)
        rag = getattr(self, "rag", None)
        if it and rag and it.get("id") in rag.cds:
            return rag.cds[it["id"]], "LATAM"
        if it and self.dp and it.get("id") in self.dp.cds:
            return self.dp.cds[it["id"]], "LATAM"
        if it and it["cd"]:
            return it["cd"], "padrão"
        return None, None

    def existe(self, nome):
        k = chave(nome)
        return k in self.itens or k in self.meus

    def buscar(self, texto, classe=TODAS, limite=400, so_buffs=False):
        """Busca pelo nome em português ou em inglês, sem ligar para acentos. so_buffs=True
        lista só buffs; False, só skills ofensivas (um não aparece na busca do outro).
        Consumíveis valem para qualquer classe e vêm depois dos buffs da classe;
        classe=GRUPO lista só eles."""
        q = chave(texto)
        unicos = {id(it): it for it in self.itens.values()}
        res = []
        for it in unicos.values():
            if bool(it.get("buff")) != so_buffs:
                continue
            consumivel = bool(it.get("consumivel"))
            if classe == GRUPO and not consumivel:
                continue
            if classe and classe not in (TODAS, GRUPO) and not consumivel                     and classe not in it["classes"]:
                continue
            kn, ke = chave(it["nome"]), chave(it.get("en"))
            if q and q not in kn and q not in ke:
                continue
            res.append(((consumivel, kn), it))
        if not so_buffs:
            for k, m in self.meus.items():
                if k not in self.itens and (not q or q in k):
                    res.append(((False, k), {"nome": m["nome"], "cd": None, "classes": [],
                                             "pt": True}))
        res.sort(key=lambda r: r[0])                   # ordem alfabética (consumíveis no fim)
        return [r[1] for r in res[:limite]]

    def salvar_meu(self, nome, cd):
        k = chave(nome)
        if not k or re.fullmatch(r"skill \d+", k):
            return
        padrao = self.itens.get(k, {}).get("cd")
        if cd is None or cd == padrao:
            if self.meus.pop(k, None) is None:
                return
        else:
            self.meus[k] = {"nome": nome.strip(), "cd": cd}
        try:
            gravar_json(ARQ_MEUS, self.meus)
        except Exception:
            pass


def _segundos(v):
    """Converte o valor de recarga da API (número ou texto) para segundos."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x / 1000 if x > 300 else x
    if isinstance(v, str):
        nums = re.findall(r"\d+(?:[.,]\d+)?", v)
        if not nums:
            return None
        x = float(nums[-1].replace(",", "."))
        low = v.lower()
        if "ms" in low:
            x /= 1000
        elif x > 300 and not re.search(r"\d\s*(s|sec|seg)", low):
            x /= 1000
        return x
    if isinstance(v, list) and v:
        return _segundos(v[-1])
    if isinstance(v, dict):
        for k in ("value", "time", "seconds"):
            if k in v:
                return _segundos(v[k])
    return None


def extrair_recarga(d):
    """Recarga no nível máximo a partir da resposta da Divine Pride."""
    melhor = None
    lt = d.get("levelTable") if isinstance(d, dict) else None
    if isinstance(lt, list):
        def nivel(e):
            for k in ("level", "skillLevel", "lv", "Level"):
                if isinstance(e.get(k), (int, float)):
                    return e[k]
            return 0
        linhas = [e for e in lt if isinstance(e, dict)]
        if linhas:
            ult = max(linhas, key=nivel)
            for k, v in ult.items():
                if "cool" in k.lower():
                    melhor = _segundos(v)
                    break
    if melhor is None and isinstance(d, dict):
        melhor = _segundos(d.get("cooldown"))
    return round(melhor, 2) if melhor and melhor > 0 else None
