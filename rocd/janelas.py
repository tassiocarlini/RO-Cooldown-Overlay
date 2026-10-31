"""Chamadas do Windows: janelas, estilos, achar a janela do jogo, captura de tela."""

import ctypes
from ctypes import wintypes

import mss


user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x11


# =============================================================== utilidades

def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def nova_captura():
    """mss.MSS nas versões novas, mss.mss nas antigas."""
    return (getattr(mss, "MSS", None) or mss.mss)()


GA_ROOT = 2
HWND = wintypes.HWND


def _sig(fn, res, *args):
    fn.restype = res
    fn.argtypes = list(args)


_sig(user32.GetParent, HWND, HWND)
_sig(user32.GetWindowLongW, ctypes.c_long, HWND, ctypes.c_int)
_sig(user32.SetWindowLongW, ctypes.c_long, HWND, ctypes.c_int, ctypes.c_long)
_sig(user32.GetForegroundWindow, HWND)
_sig(user32.GetWindowTextLengthW, ctypes.c_int, HWND)
_sig(user32.GetWindowTextW, ctypes.c_int, HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.GetClassNameW, ctypes.c_int, HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.IsWindow, wintypes.BOOL, HWND)
_sig(user32.IsWindowVisible, wintypes.BOOL, HWND)
_sig(user32.IsIconic, wintypes.BOOL, HWND)
_sig(user32.GetClientRect, wintypes.BOOL, HWND, ctypes.POINTER(wintypes.RECT))
_sig(user32.ClientToScreen, wintypes.BOOL, HWND, ctypes.POINTER(wintypes.POINT))
_sig(user32.WindowFromPoint, HWND, wintypes.POINT)
_sig(user32.GetAncestor, HWND, HWND, ctypes.c_uint)
_sig(user32.SetWindowDisplayAffinity, wintypes.BOOL, HWND, wintypes.DWORD)
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
_sig(user32.EnumWindows, wintypes.BOOL, EnumWindowsProc, wintypes.LPARAM)

# Janelas que podem ter "Ragnarok" no título mas não são o jogo
# (navegadores, Discord, Explorer, terminal, este próprio programa)
CLASSES_IGNORADAS = ("Chrome_WidgetWin", "MozillaWindowClass", "TkTopLevel", "TkChild",
                     "CabinetWClass", "ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS",
                     "ApplicationFrameWindow")


def hwnd_de(janela):
    return user32.GetParent(janela.winfo_id())


def mudar_estilo(hwnd, ligar=0, desligar=0):
    estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo | ligar) & ~desligar)


def texto_janela(h):
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    return buf.value


def classe_janela(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def eh_jogo(h, titulo):
    if not h or not user32.IsWindow(h) or not user32.IsWindowVisible(h):
        return False
    if titulo.lower() not in texto_janela(h).lower():
        return False
    cls = classe_janela(h)
    return not any(cls.startswith(c) for c in CLASSES_IGNORADAS)


class Jogo:
    """Acha e acompanha a janela do Ragnarok (só lê título/posição da janela)."""

    def __init__(self):
        self.hwnd = None
        self._ult_busca = -99.0

    def localizar(self, titulo, agora):
        fg = user32.GetForegroundWindow()
        if fg and fg != self.hwnd and eh_jogo(fg, titulo):
            self.hwnd = fg               # o jogo em foco tem prioridade (multi-client)
            return
        if self.hwnd and agora - self._ult_busca < 0.5:
            return
        self._ult_busca = agora
        if self.hwnd and eh_jogo(self.hwnd, titulo):
            return
        achados = []

        def cb(h, _lp):
            if eh_jogo(h, titulo):
                achados.append(h)
                return False
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        self.hwnd = achados[0] if achados else None

    def geometria(self):
        """(x, y, largura, altura) da área do jogo na tela, ou None."""
        h = self.hwnd
        if not h or not user32.IsWindow(h) or user32.IsIconic(h):
            return None
        r = wintypes.RECT()
        p = wintypes.POINT(0, 0)
        if not user32.GetClientRect(h, ctypes.byref(r)) or not user32.ClientToScreen(h, ctypes.byref(p)):
            return None
        if r.right <= 0 or r.bottom <= 0:
            return None
        return (p.x, p.y, r.right, r.bottom)

    def em_foco(self):
        return bool(self.hwnd) and user32.GetForegroundWindow() == self.hwnd


def janela_no_ponto(x, y):
    h = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    return user32.GetAncestor(h, GA_ROOT) if h else None
