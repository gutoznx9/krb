"""Verifica se a pasta do projeto não é longa demais para o Windows.

O Windows (por padrão) não aceita caminhos com mais de 260 caracteres, e o
PySide6 instala arquivos em subpastas muito profundas dentro de .venv.
Usado pelo instalar.bat antes de instalar as dependências.
"""

import os
import sys

# Caminho mais longo criado pelo PySide6 dentro da pasta do projeto: ~185 caracteres
LIMITE_PASTA = 70


def caminhos_longos_ativados() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            return winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1
    except OSError:
        return False


def main() -> int:
    pasta = os.getcwd()
    if len(pasta) <= LIMITE_PASTA or caminhos_longos_ativados():
        return 0
    print()
    print("[ERRO] A pasta do projeto tem um caminho longo demais para o Windows:")
    print(f"       {pasta}")
    print(f"       ({len(pasta)} caracteres; o recomendado é no máximo {LIMITE_PASTA})")
    print()
    print("SOLUÇÃO: mova a pasta do projeto para um caminho curto, por exemplo C:\\krb")
    print("e rode o instalar.bat de novo a partir de lá.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
