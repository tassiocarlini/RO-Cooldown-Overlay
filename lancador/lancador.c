/*
 * RO Cooldown Overlay - lançador (.exe) da versão em Python.
 *
 * Abre o ro_cooldown_overlay.py que está na mesma pasta, sem janela preta:
 *   1. procura um Python com todas as bibliotecas (py -3 ou python);
 *   2. se achar, abre o programa com pythonw (sem console);
 *   3. se faltar o Python ou alguma biblioteca, roda o iniciar.bat, que instala
 *      tudo mostrando o progresso, e depois abre o programa.
 *
 * Compilar (MinGW-w64):
 *   x86_64-w64-mingw32-windres lancador.rc -O coff -o lancador.res
 *   x86_64-w64-mingw32-gcc -O2 -s -municode -mwindows lancador.c lancador.res \
 *       -o "RO Cooldown Overlay.exe"
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>

#define TITULO L"RO Cooldown Overlay"

static wchar_t pasta[MAX_PATH];

/* Roda um comando na pasta do programa. Devolve o código de saída (ou 9999 se falhar). */
static DWORD rodar(const wchar_t *comando, DWORD flags, BOOL esperar)
{
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    wchar_t linha[4096];
    DWORD codigo = 0;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    lstrcpynW(linha, comando, 4096);
    if (!CreateProcessW(NULL, linha, NULL, NULL, FALSE, flags, NULL, pasta, &si, &pi))
        return 9999;
    if (esperar) {
        if (WaitForSingleObject(pi.hProcess, 60000) != WAIT_OBJECT_0)
            codigo = 9998;
        else if (!GetExitCodeProcess(pi.hProcess, &codigo))
            codigo = 9997;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return codigo;
}

static BOOL existe(const wchar_t *caminho)
{
    DWORD a = GetFileAttributesW(caminho);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE ant, PWSTR args, int mostrar)
{
    wchar_t script[MAX_PATH + 64], bat[MAX_PATH + 64], cmd[4096];
    wchar_t *barra;
    int i;
    /* {programa para testar (console escondido), programa para abrir (sem console)} */
    static const wchar_t *pythons[][2] = {
        { L"py.exe -3",  L"pyw.exe -3"  },
        { L"python.exe", L"pythonw.exe" },
    };

    (void)inst; (void)ant; (void)args; (void)mostrar;

    GetModuleFileNameW(NULL, pasta, MAX_PATH);
    barra = wcsrchr(pasta, L'\\');
    if (barra)
        *barra = 0;

    _snwprintf(script, MAX_PATH + 64, L"%ls\\ro_cooldown_overlay.py", pasta);
    _snwprintf(bat, MAX_PATH + 64, L"%ls\\iniciar.bat", pasta);
    if (!existe(script)) {
        MessageBoxW(NULL,
            L"Não encontrei o arquivo ro_cooldown_overlay.py.\n\n"
            L"Deixe este programa na mesma pasta do ro_cooldown_overlay.py.",
            TITULO, MB_ICONERROR);
        return 1;
    }

    for (i = 0; i < 2; i++) {
        _snwprintf(cmd, 4096,
            L"%ls -c \"import tkinter, mss, PIL, numpy, cv2, sv_ttk\"", pythons[i][0]);
        if (rodar(cmd, CREATE_NO_WINDOW, TRUE) == 0) {
            _snwprintf(cmd, 4096, L"%ls \"%ls\"", pythons[i][1], script);
            if (rodar(cmd, 0, FALSE) != 9999)
                return 0;
        }
    }

    /* Falta o Python ou alguma biblioteca: o iniciar.bat instala e abre o programa */
    if (existe(bat)) {
        _snwprintf(cmd, 4096, L"cmd.exe /c \"\"%ls\"\"", bat);
        if (rodar(cmd, CREATE_NEW_CONSOLE, FALSE) != 9999)
            return 0;
    }
    MessageBoxW(NULL,
        L"Não encontrei o Python neste computador.\n\n"
        L"Opção 1: baixe a versão pronta (.zip) na página \"Releases\" do projeto no GitHub.\n"
        L"Opção 2: instale o Python em python.org (marque \"Add python.exe to PATH\").",
        TITULO, MB_ICONWARNING);
    return 1;
}
