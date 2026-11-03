import json
import tempfile
import unittest
from pathlib import Path

from limpia_csv import decodificar, detectar_delimitador, limpiar_datos, main, reparar_mojibake


class PruebasLimpieza(unittest.TestCase):
    def test_quita_duplicados_y_filas_vacias(self):
        filas, informe = limpiar_datos(b"a,b\n1,2\n1,2\n,\n3,4\n")
        self.assertEqual(filas, [["a", "b"], ["1", "2"], ["3", "4"]])
        self.assertEqual(informe.duplicados, 1)
        self.assertEqual(informe.filas_vacias, 1)

    def test_quita_columnas_vacias(self):
        filas, informe = limpiar_datos(b"a,vacia,b\n1,,2\n3,,4\n")
        self.assertEqual(filas[0], ["a", "b"])
        self.assertEqual(informe.columnas_vacias, ["vacia"])

    def test_recorta_espacios(self):
        filas, informe = limpiar_datos(b"a,b\n  1 , 2\n")
        self.assertEqual(filas[1], ["1", "2"])
        self.assertEqual(informe.celdas_recortadas, 2)

    def test_conserva_comillas_y_saltos_de_linea(self):
        filas, _ = limpiar_datos('nombre,nota\nAna,"hola, mundo"\nLuis,"dos\nlíneas"\n'.encode())
        self.assertEqual(filas[1], ["Ana", "hola, mundo"])
        self.assertEqual(filas[2], ["Luis", "dos\nlíneas"])

    def test_filas_de_distinto_ancho(self):
        filas, _ = limpiar_datos(b"a,b,c\n1,2\n3,4,5\n")
        self.assertEqual(filas[1], ["1", "2", ""])

    def test_archivo_vacio(self):
        filas, informe = limpiar_datos(b"")
        self.assertEqual(filas, [])
        self.assertEqual(informe.filas_salida, 0)


class PruebasDeteccion(unittest.TestCase):
    def test_utf8_con_bom(self):
        self.assertEqual(decodificar("año".encode("utf-8-sig")), ("año", "utf-8-sig"))

    def test_windows_1252(self):
        self.assertEqual(decodificar("año".encode("cp1252")), ("año", "cp1252"))

    def test_mojibake(self):
        self.assertEqual(reparar_mojibake("BogotÃ¡"), "Bogotá")
        self.assertEqual(reparar_mojibake("Bogotá"), "Bogotá")

    def test_delimitador(self):
        self.assertEqual(detectar_delimitador("a;b;c\n1;2;3\n"), ";")
        self.assertEqual(detectar_delimitador("a\tb\n1\t2\n"), "\t")


class PruebasCLI(unittest.TestCase):
    def test_crea_archivo_y_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada = Path(carpeta) / "datos.csv"
            entrada.write_bytes(b"a,b\n1,2\n1,2\n")
            self.assertEqual(main([str(entrada)]), 0)
            salida = Path(carpeta) / "datos_limpio.csv"
            self.assertEqual(salida.read_text(encoding="utf-8").splitlines(), ["a,b", "1,2"])
            self.assertEqual(entrada.read_bytes(), b"a,b\n1,2\n1,2\n")
            self.assertEqual(main([str(entrada)]), 2)

    def test_solo_revisar_no_crea_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada = Path(carpeta) / "datos.csv"
            entrada.write_bytes(b"a,b\n1,2\n")
            self.assertEqual(main([str(entrada), "--solo-revisar"]), 0)
            self.assertFalse((Path(carpeta) / "datos_limpio.csv").exists())

    def test_guarda_informe_json(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada = Path(carpeta) / "datos.csv"
            informe = Path(carpeta) / "informe.json"
            entrada.write_bytes(b"a,b\n1,2\n1,2\n")
            self.assertEqual(main([str(entrada), "--solo-revisar", "--informe", str(informe)]), 0)
            datos = json.loads(informe.read_text(encoding="utf-8"))
            self.assertEqual(datos["duplicados"], 1)
            self.assertEqual(datos["filas_salida"], 1)

    def test_archivo_inexistente(self):
        self.assertEqual(main(["/ruta/que/no/existe.csv"]), 2)


if __name__ == "__main__":
    unittest.main()
