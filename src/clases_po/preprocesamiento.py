"""Preprocesamiento y estandarización del dataset de pedidos de e-commerce.

Replica lo que se hace en las hojas «Tipos» y «Datos» del dataset de e-commerce:
diagnóstico de tipos, conversión (VALOR.NUMERO, FECHA, HORANUMERO), categorías
y columnas calculadas (total_calculado, verificación, día_semana, hora, nuevo_pedido).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class PreprocesadorEcommerce:
    """Convierte el DataFrame crudo de Hugging Face en un DataFrame tipado y listo para analizar."""

    DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    ORDEN_TAMANOS = ["Mobile", "Tablet", "Desktop"]
    ORDEN_CATEGORIAS = ["Beauty", "Books", "Clothing", "Electronics", "Home", "Toys"]
    COLUMNAS_TEXTO = ["order_id", "product_id", "category", "delivery_status",
                      "payment_method", "device_type", "channel", "shipping_address",
                      "billing_address", "customer_segment"]
    # Totales del dataset de e-commerce (primeras 1.700 líneas)
    ESPERADO_DATASET = {"filas": 10000, "pedidos": 10000, "clientes": 2713}

    def __init__(self, filas_clase: int | None = None):
        self.filas_clase = filas_clase

    # ------------------------------------------------------------------ pasos
    def recortar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Devuelve todas las filas o un l?mite expl?cito para pruebas."""
        return df.copy() if self.filas_clase is None else df.head(self.filas_clase).copy()

    @staticmethod
    def diagnosticar(df: pd.DataFrame) -> pd.DataFrame:
        """Equivalente a ESTEXTO / ESNUMERO / CONTARA por columna."""
        filas = []
        for c in df.columns:
            s = df[c]
            filas.append({
                "columna": c,
                "tipo_actual": str(s.dtype),
                "ejemplo": s.iloc[0],
                "no_vacíos (CONTARA)": int(s.notna().sum()),
                "convertibles_a_número": int(pd.to_numeric(s, errors="coerce").notna().sum()),
                "¿es número? (ESNUMERO)": pd.api.types.is_numeric_dtype(s),
            })
        return pd.DataFrame(filas)

    @staticmethod
    def diccionario() -> pd.DataFrame:
        """Diccionario de columnas (hoja Tipos, sección B)."""
        return pd.DataFrame([
            ["order_id", "Identificador único del pedido", "Cualitativa nominal", "string"],
            ["customer_id", "Identificador del cliente", "Cuantitativa discreta", "int64"],
            ["product_id", "Identificador del producto", "Cuantitativa discreta", "int64"],
            ["quantity", "Cantidad de unidades", "Cuantitativa discreta", "int64"],
            ["order_date", "Fecha y hora del pedido", "Cuantitativa (tiempo)", "datetime64"],
            ["shipping_date", "Fecha y hora del envío", "Cuantitativa (tiempo)", "datetime64"],
            ["price", "Precio unitario", "Cuantitativa continua", "float64 (moneda, 2 dec.)"],
            ["order_value", "Cantidad × precio unitario", "Cuantitativa continua", "float64 (moneda, 2 dec.)"],
            ["device_type", "Dispositivo utilizado", "Cualitativa nominal", "category"],
            ["category", "Categoría del producto", "Cualitativa nominal", "category"],
            ["channel", "Canal de adquisición", "Cualitativa nominal", "category"],
            ["customer_segment", "Segmento del cliente", "Cualitativa nominal", "category"],
        ], columns=["columna", "qué significa", "tipo de variable", "tipo en pandas"])

    def convertir_tipos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Hoja Tipos, secciones D y E: números, moneda, fecha, hora y categorías."""
        d = df.copy()
        for c in self.COLUMNAS_TEXTO:
            d[c] = d[c].astype("string").str.strip()

        # VALOR.NUMERO
        d["quantity"] = pd.to_numeric(d["quantity"], errors="coerce").round().astype("int64")
        d["price"] = pd.to_numeric(d["price"], errors="coerce").astype("float64").round(2)
        d["customer_id"] = pd.to_numeric(d["customer_id"], errors="coerce").round().astype("Int64")
        d["product_id"] = pd.to_numeric(d["product_id"], errors="coerce").round().astype("Int64")

        d["order_date"] = pd.to_datetime(d["order_date"], errors="coerce")
        d["shipping_date"] = pd.to_datetime(d["shipping_date"], errors="coerce")
        d["order_time"] = d["order_date"].dt.time
        d["fecha_hora"] = d["order_date"]
        d["shipping_days"] = (
            (d["shipping_date"] - d["order_date"]).dt.total_seconds() / 86400
        ).round(2)
        d["order_value"] = (d["quantity"] * d["price"]).round(2)

        d["device_type"] = pd.Categorical(d["device_type"], categories=self.ORDEN_TAMANOS, ordered=True)
        d["category"] = pd.Categorical(d["category"], categories=self.ORDEN_CATEGORIAS)
        return d

    def agregar_columnas_calculadas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Columnas calculadas de la hoja Datos."""
        d = df.copy()
        d["total_calculado"] = (d["quantity"] * d["price"]).round(2)                      # =D2*G2
        d["verificacion"] = np.where((d["total_calculado"] - d["order_value"]).abs() < 0.005,
                                     "OK", "Revisar")                                           # =SI(REDONDEAR(M2-H2;2)=0;...)
        d["dia_semana"] = pd.Categorical(d["order_date"].dt.dayofweek.map(dict(enumerate(self.DIAS_SEMANA))),
                                         categories=self.DIAS_SEMANA, ordered=True)             # =ELEGIR(DIASEM(E2;2);...)
        d["hora"] = d["fecha_hora"].dt.hour                                                     # =HORA(F2)
        d["nuevo_pedido"] = (~d["order_id"].duplicated()).astype("int64")                      # =SI(CONTAR.SI($B$2:B2;B2)=1;1;0)
        return d

    def procesar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flujo completo: recortar → convertir tipos → columnas calculadas."""
        return self.agregar_columnas_calculadas(self.convertir_tipos(self.recortar(df)))

    # ------------------------------------------------------------------ validaciones
    @staticmethod
    def check(nombre: str, condicion: bool, detalle: str = "") -> bool:
        print(f"{'✔' if condicion else '✘'} {nombre} {detalle}")
        return bool(condicion)

    def validar(self, datos: pd.DataFrame, comparar_excel: bool = True) -> bool:
        """Calidad de la base procesada y comparación con los totales del Excel."""
        c = self.check
        ok = [
            c("Sin valores nulos tras convertir", datos[["order_id", "customer_id", "product_id", "quantity",
              "order_date", "shipping_date", "price", "order_value", "device_type", "category"]].isna().sum().sum() == 0),
            c("Sin filas duplicadas", not datos.duplicated(subset=["order_id"]).any()),
            c("order_value = quantity × price", (datos["verificacion"] == "OK").all(),
              f"({(datos['verificacion'] == 'Revisar').sum()} filas a revisar)"),
            c("Fechas válidas de pedido y envío",
              (datos["shipping_date"] >= datos["order_date"]).all()),
        ]
        if comparar_excel and self.filas_clase is None:
            e = self.ESPERADO_DATASET
            pedidos = datos["order_id"].nunique()
            clientes = datos["customer_id"].nunique()
            ok += [
                c(f"Filas = {e['filas']:,}", len(datos) == e['filas'], f"? {len(datos):,}"),
                c(f"Pedidos = {e['pedidos']:,}", pedidos == e['pedidos'], f"? {pedidos:,}"),
                c(f"Clientes = {e['clientes']:,}", clientes == e['clientes'], f"? {clientes:,}"),
            ]
        ultimo = datos["order_date"].max()
        print(f"\nRango de fechas: {datos['order_date'].min():%d/%m/%Y} a {ultimo:%d/%m/%Y} "
              f"({datos['order_date'].nunique()} días; el último tiene {(datos['order_date'] == ultimo).sum()} líneas)")
        return all(ok)
