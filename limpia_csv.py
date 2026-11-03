#!/usr/bin/env python3
"""Limpia archivos CSV: codificación, duplicados, filas y columnas vacías."""

import argparse
import csv
import io
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DELIMITADORES = ",;\t|"
SEÑALES_MOJIBAKE = ("Ã", "Â", "â€")


@dataclass
class Informe:
    codificacion: str = ""
    delimitador: str = ""
    filas_entrada: int = 0
    filas_salida: int = 0
    filas_vacias: int = 0
    duplicados: int = 0
    celdas_recortadas: int = 0
    celdas_reparadas: int = 0
    columnas_vacias: list = field(default_factory=list)

    def a_dict(self):
        return asdict(self)


def decodificar(datos):
    """Devuelve (texto, codificación) probando UTF-8 y luego Windows-1252."""
    if datos.startswith(b"\xef\xbb\xbf"):
        return datos.decode("utf-8-sig"), "utf-8-sig"
    try:
        return datos.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return datos.decode("cp1252", errors="replace"), "cp1252"


def reparar_mojibake(texto):
    """Repara texto como 'BogotÃ¡' cuando es UTF-8 mal leído como Windows-1252."""
    if not any(señal in texto for señal in SEÑALES_MOJIBAKE):
        return texto
    try:
        return texto.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def detectar_delimitador(texto):
    muestra = texto[:8192]
    try:
        return csv.Sniffer().sniff(muestra, delimiters=DELIMITADORES).delimiter
    except csv.Error:
        primera_linea = muestra.splitlines()[0] if muestra.splitlines() else ""
        return max(DELIMITADORES, key=primera_linea.count) if primera_linea else ","


def limpiar_filas(filas, informe):
    """Limpia las filas leídas; la primera se trata como encabezado."""
    limpias = []
    for fila in filas:
        nueva = []
        for celda in fila:
            recortada = celda.strip()
            if recortada != celda:
                informe.celdas_recortadas += 1
            reparada = reparar_mojibake(recortada)
            if reparada != recortada:
                informe.celdas_reparadas += 1
            nueva.append(reparada)
        limpias.append(nueva)

    informe.filas_entrada = max(len(limpias) - 1, 0)

    con_contenido = [fila for fila in limpias if any(fila)]
    informe.filas_vacias = len(limpias) - len(con_contenido)
    if not con_contenido:
        return []

    encabezado, *datos = con_contenido
    ancho = max(len(fila) for fila in con_contenido)
    encabezado = encabezado + [""] * (ancho - len(encabezado))
    datos = [fila + [""] * (ancho - len(fila)) for fila in datos]

    conservar = [i for i in range(ancho) if any(fila[i] for fila in datos)]
    informe.columnas_vacias = [
        encabezado[i] or f"(columna {i + 1})" for i in range(ancho) if i not in conservar
    ]

    vistas = set()
    resultado = [[encabezado[i] for i in conservar]]
    for fila in datos:
        recortada = tuple(fila[i] for i in conservar)
        if recortada in vistas:
            informe.duplicados += 1
            continue
        vistas.add(recortada)
        resultado.append(list(recortada))

    informe.filas_salida = len(resultado) - 1
    return resultado


def limpiar_datos(datos):
    """Limpia bytes de un CSV y devuelve (filas, informe)."""
    texto, codificacion = decodificar(datos)
    delimitador = detectar_delimitador(texto)
    informe = Informe(codificacion=codificacion, delimitador=delimitador)
    filas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=delimitador))
    return limpiar_filas(filas, informe), informe


def escribir_csv(ruta, filas, delimitador):
    with open(ruta, "x", encoding="utf-8", newline="") as salida:
        csv.writer(salida, delimiter=delimitador).writerows(filas)


def imprimir_resumen(informe):
    print(f"Codificación detectada: {informe.codificacion}")
    print(f"Delimitador detectado:  {informe.delimitador!r}")
    print(f"Filas de datos:         {informe.filas_entrada} -> {informe.filas_salida}")
    print(f"Filas vacías quitadas:  {informe.filas_vacias}")
    print(f"Duplicados quitados:    {informe.duplicados}")
    print(f"Celdas recortadas:      {informe.celdas_recortadas}")
    print(f"Celdas reparadas:       {informe.celdas_reparadas}")
    vacias = ", ".join(informe.columnas_vacias) or "ninguna"
    print(f"Columnas vacías:        {vacias}")


def crear_parser():
    parser = argparse.ArgumentParser(description="Limpia un archivo CSV sin modificar el original.")
    parser.add_argument("entrada", type=Path, help="archivo CSV de entrada")
    parser.add_argument("-o", "--salida", type=Path, help="archivo de salida (por defecto, <nombre>_limpio.csv)")
    parser.add_argument("--solo-revisar", action="store_true", help="muestra el resumen sin crear el archivo limpio")
    parser.add_argument("--informe", type=Path, help="guarda el resumen en un archivo JSON")
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)
    salida = args.salida or args.entrada.with_name(f"{args.entrada.stem}_limpio.csv")

    try:
        filas, informe = limpiar_datos(args.entrada.read_bytes())
        if not args.solo_revisar:
            escribir_csv(salida, filas, informe.delimitador)
        if args.informe:
            with open(args.informe, "x", encoding="utf-8") as archivo:
                json.dump(informe.a_dict(), archivo, ensure_ascii=False, indent=2)
    except FileExistsError as error:
        print(f"Error: {error.filename} ya existe; no se sobrescribe.", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    imprimir_resumen(informe)
    if not args.solo_revisar:
        print(f"Guardado en:            {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
