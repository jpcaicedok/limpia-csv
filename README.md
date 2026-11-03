# Limpia-CSV

Ordena archivos CSV desordenados y guarda el resultado en una copia. El archivo original no se modifica.

## Qué hace

- Detecta la codificación (UTF-8, UTF-8 con BOM o Windows-1252) y guarda en UTF-8.
- Repara texto mal codificado, como `BogotÃ¡` → `Bogotá`.
- Detecta el delimitador: coma, punto y coma, tabulador o barra vertical.
- Quita espacios sobrantes, filas vacías, filas duplicadas y columnas sin datos.

## Uso

Requiere Python 3.9 o superior. No tiene dependencias externas.

```bash
python limpia_csv.py clientes.csv
python limpia_csv.py clientes.csv -o clientes_ok.csv
```

Si el archivo de salida ya existe, el programa se detiene sin sobrescribirlo.

La primera fila se trata siempre como encabezado.

## Pruebas

```bash
python -m unittest
```

## Licencia

MIT
