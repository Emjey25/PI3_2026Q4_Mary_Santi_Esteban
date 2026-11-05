"""Enriquecimiento de pedidos de comercio electrónico.

Agrega indicadores derivados directamente de las columnas del dataset:
valor del pedido, días de despacho, recurrencia del cliente y participación
del pedido dentro del canal y del segmento.
"""
from __future__ import annotations

import pandas as pd


class EnriquecedorEcommerce:
    """Construye variables analíticas sin inventar entidades externas."""

    COLUMNAS_REQUERIDAS = {
        "order_id", "customer_id", "product_id", "price", "quantity",
        "order_date", "shipping_date", "delivery_status", "channel",
        "customer_segment",
    }

    def __init__(self, preprocesador=None):
        self.preprocesador = preprocesador
        self.datos: pd.DataFrame | None = None

    def validar_entrada(self, datos: pd.DataFrame) -> None:
        faltantes = self.COLUMNAS_REQUERIDAS.difference(datos.columns)
        if faltantes:
            raise KeyError(f"Faltan columnas del dataset de e-commerce: {sorted(faltantes)}")

    def enriquecer(self, datos: pd.DataFrame) -> pd.DataFrame:
        """Devuelve una copia con métricas de negocio derivadas."""
        self.validar_entrada(datos)
        d = datos.copy()
        d["order_date"] = pd.to_datetime(d["order_date"], errors="coerce")
        d["shipping_date"] = pd.to_datetime(d["shipping_date"], errors="coerce")
        d["order_value"] = (pd.to_numeric(d["price"]) * pd.to_numeric(d["quantity"])).round(2)
        d["shipping_days"] = (
            (d["shipping_date"] - d["order_date"]).dt.total_seconds() / 86400
        ).round(2)
        d["customer_order_count"] = d.groupby("customer_id")["order_id"].transform("nunique")
        d["customer_recurrente"] = d["customer_order_count"].gt(1)
        d["channel_sales_share"] = d["order_value"] / d.groupby("channel")["order_value"].transform("sum")
        d["segment_sales_share"] = (
            d["order_value"] / d.groupby("customer_segment")["order_value"].transform("sum")
        )
        d["delivery_delay"] = d["shipping_days"].gt(3)
        self.datos = d
        return d

    def procesar(self, datos: pd.DataFrame) -> pd.DataFrame:
        """Alias explícito para ejecutar el enriquecimiento."""
        return self.enriquecer(datos)

    def resumen_clientes(self, datos: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.datos if datos is None else self.enriquecer(datos)
        if d is None:
            raise ValueError("Primero debe ejecutarse enriquecer().")
        return (
            d.groupby(["customer_id", "customer_segment"], as_index=False)
            .agg(
                pedidos=("order_id", "nunique"),
                unidades=("quantity", "sum"),
                ventas=("order_value", "sum"),
                ticket_promedio=("order_value", "mean"),
                dias_envio_promedio=("shipping_days", "mean"),
            )
            .sort_values("ventas", ascending=False)
        )

    def resumen_canales(self, datos: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.datos if datos is None else self.enriquecer(datos)
        if d is None:
            raise ValueError("Primero debe ejecutarse enriquecer().")
        return (
            d.groupby("channel", as_index=False)
            .agg(
                pedidos=("order_id", "nunique"),
                clientes=("customer_id", "nunique"),
                unidades=("quantity", "sum"),
                ventas=("order_value", "sum"),
                ticket_promedio=("order_value", "mean"),
            )
            .sort_values("ventas", ascending=False)
        )

    def resumen_entregas(self, datos: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.datos if datos is None else self.enriquecer(datos)
        if d is None:
            raise ValueError("Primero debe ejecutarse enriquecer().")
        return (
            d.groupby("delivery_status", as_index=False)
            .agg(
                pedidos=("order_id", "nunique"),
                ventas=("order_value", "sum"),
                dias_envio_promedio=("shipping_days", "mean"),
            )
            .sort_values("pedidos", ascending=False)
        )
