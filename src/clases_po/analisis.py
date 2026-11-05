"""Analítica descriptiva de pedidos de comercio electrónico.

- :class:`AnalisisBase` replica el dataset de e-commerce (Fórmulas, Descriptiva, Relaciones,
  Tabla dinámica, Dashboard y Práctica) sobre CUALQUIER DataFrame de ventas ya
  preprocesado, sobre pedidos originales y sus dimensiones comerciales.
- :class:`AnalisisEcommerce` hereda todo lo anterior y agrega el análisis segmentado por canal:
  canal, ciudad/país, customers y distancia.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
ORDEN_CATEGORIAS = ["Beauty", "Books", "Clothing", "Electronics", "Home", "Toys"]


class AnalisisBase:
    """Análisis del dataset de e-commerce sobre un DataFrame de ventas (una fila por línea de pedido)."""

    PALABRAS_DINERO = ("ventas", "ticket", "precio", "valor", "venta", "suma")
    CORTES_PRECIO = [0, 100, 200, 300, 400, 500, float("inf")]

    def __init__(self, ventas: pd.DataFrame, producto_elegido: int = 1, dias_incompletos=None):
        """``dias_incompletos``: fechas que se excluyen de los PROMEDIOS por día de la semana
        (por ejemplo el 13/01, que en el archivo solo tiene 50 líneas). Los totales no cambian."""
        self.V = ventas
        self.producto_elegido = producto_elegido
        self.dias_incompletos = pd.to_datetime(list(dias_incompletos or []))
        self.pedidos = self._construir_pedidos()

    def _construir_pedidos(self) -> pd.DataFrame:
        """Una fila por pedido: valor del pedido (ticket) y productos (más canal/customer si existen)."""
        agg = {"order_date": ("order_date", "first"), "hora": ("hora", "first"),
               "dia_semana": ("dia_semana", "first"), "valor_pedido": ("order_value", "sum"),
               "productos": ("quantity", "sum")}
        for c in ["customer_id", "channel", "customer_segment"]:
            if c in self.V.columns:
                agg[c] = (c, "first")
        return self.V.groupby("order_id").agg(**agg).reset_index()

    # ================================================================== utilidades
    @classmethod
    def estilo(cls, df: pd.DataFrame, dinero=None, pct=None, dec=None, enteros=None):
        """Formato automático: columnas de dinero ($), de porcentaje (%) y conteos (miles).

        Detecta por nombre de columna; los parámetros permiten forzar columnas concretas.
        """
        num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        nombre = {c: str(c).lower() for c in num}
        pct = list(pct) if pct is not None else [c for c in num if nombre[c].startswith("%") or "corr" in nombre[c]]
        dinero = list(dinero) if dinero is not None else [
            c for c in num if c not in pct and any(w in nombre[c] for w in cls.PALABRAS_DINERO)]
        enteros = list(enteros) if enteros is not None else [
            c for c in num if c not in pct + dinero and pd.api.types.is_integer_dtype(df[c])]
        dec = list(dec) if dec is not None else [c for c in num if c not in pct + dinero + enteros]
        fmt = {**{c: "${:,.2f}" for c in dinero}, **{c: "{:.1%}" for c in pct},
               **{c: "{:,.2f}" for c in dec}, **{c: "{:,.0f}" for c in enteros}}
        try:
            return df.style.format(fmt, na_rep="—")
        except Exception:  # noqa: BLE001  (si falta jinja2 se muestra sin formato)
            return df

    def filtrar(self, canal="Todos", categoria="Todas", dispositivo="Todos", dia_semana="Todos") -> pd.DataFrame:
        d = self.V
        if canal != "Todos" and "channel" in d.columns:
            d = d[d["channel"] == canal]
        if categoria != "Todas":
            d = d[d["category"] == categoria]
        if dispositivo != "Todos":
            d = d[d["device_type"] == dispositivo]
        if dia_semana != "Todos":
            d = d[d["dia_semana"] == dia_semana]
        return d

    def periodo(self) -> str:
        f = self.V["order_date"]
        return f"{f.min():%d/%m/%Y} a {f.max():%d/%m/%Y} ({f.nunique()} días)"

    # ================================================================== Fórmulas (hoja «Fórmulas»)
    def formulas_basicas(self, fila_excel: int = 185) -> pd.DataFrame:
        """Hoja Fórmulas, secciones B, C, E y F: cada fórmula de Excel con su equivalente en pandas.

        ``fila_excel`` es la fila de la hoja Datos usada en las operaciones con una fila (la 185 = 3 Spicy Italian).
        """
        V = self.V.reset_index(drop=True)
        i = fila_excel - 2                      # la fila 2 de Excel es el índice 0
        cat, pz = V["category"], V["product_id"]
        filas = [
            # B · operaciones con una fila
            (1, "Multiplicar: total de la línea", f"=Datos!D{fila_excel}*Datos!G{fila_excel}",
             "V.quantity[i] * V.price[i]", V.loc[i, "quantity"] * V.loc[i, "price"]),
            (2, "Dividir: precio de cada producto", f"=Datos!H{fila_excel}/Datos!D{fila_excel}",
             "V.order_value[i] / V.quantity[i]", V.loc[i, "order_value"] / V.loc[i, "quantity"]),
            (3, "Sumar: productos en dos líneas", f"=Datos!D{fila_excel}+Datos!D{fila_excel + 1}",
             "V.quantity[i] + V.quantity[i+1]", V.loc[i, "quantity"] + V.loc[i + 1, "quantity"]),
            (4, "Restar: precio más alto − más bajo", "=MAX(G)-MIN(G)",
             "V.price.max() - V.price.min()", V["price"].max() - V["price"].min()),
            (5, "Redondear el precio promedio", "=REDONDEAR(PROMEDIO(G);2)",
             "round(V.price.mean(), 2)", round(V["price"].mean(), 2)),
            # C · funciones de resumen
            (6, "Ventas totales", "=SUMA(H)", "V.order_value.sum()", V["order_value"].sum()),
            (7, "Unidades vendidas", "=SUMA(D)", "V.quantity.sum()", V["quantity"].sum()),
            (8, "Líneas con número", "=CONTAR(H)", "V.order_value.count()", V["order_value"].count()),
            (9, "Líneas con nombre de producto", "=CONTARA(L)", "V.product_id.notna().sum()", pz.notna().sum()),
            (10, "Celdas vacías en la categoría", "=CONTAR.BLANCO(J)", "V.category.isna().sum()", cat.isna().sum()),
            (11, "Precio promedio de una línea", "=PROMEDIO(H)", "V.order_value.mean()", V["order_value"].mean()),
            (12, "Precio unitario más bajo", "=MIN(G)", "V.price.min()", V["price"].min()),
            (13, "Precio unitario más alto", "=MAX(G)", "V.price.max()", V["price"].max()),
            (14, "Multiplicar y sumar en un paso", "=SUMAPRODUCTO(D;G)", "(V.quantity * V.price).sum()",
             (V["quantity"] * V["price"]).sum()),
            # E · valores únicos
            (16, "Categorías sin repetir", "=UNICOS(J)", "V.category.unique()", " · ".join(map(str, cat.unique()))),
            (17, "Categorías en orden alfabético", "=ORDENAR(UNICOS(J))", "sorted(V.category.unique())",
             " · ".join(sorted(map(str, cat.unique())))),
            (18, "Tamaños sin repetir", "=UNICOS(I)", "V.device_type.unique()",
             " · ".join(map(str, V["device_type"].unique()))),
            (19, "Categorías distintas", "=CONTARA(UNICOS(J))", "V.category.nunique()", cat.nunique()),
            (21, "Unidades distintas en el menú", "=SUMAPRODUCTO(1/CONTAR.SI(L;L))", "V.product_id.nunique()", pz.nunique()),
            (22, "Pedidos distintos", "=SUMA(Q)  (nuevo_pedido)", "V.nuevo_pedido.sum()", V["nuevo_pedido"].sum()),
            # F · una condición
            (23, "¿Cuántas líneas son Electronics?", '=CONTAR.SI(J;"Electronics")', '(V.category == "Electronics").sum()',
             (cat == "Electronics").sum()),
            (24, "¿Cuánto vendió Electronics?", '=SUMAR.SI(J;"Electronics";H)', 'V.loc[cat == "Electronics", "order_value"].sum()',
             V.loc[cat == "Electronics", "order_value"].sum()),
            (25, "Precio unitario promedio de Electronics", '=PROMEDIO.SI(J;"Electronics";G)',
             'V.loc[cat == "Electronics", "price"].mean()', V.loc[cat == "Electronics", "price"].mean()),
            (26, "Líneas con más de una producto", '=CONTAR.SI(D;">1")', "(V.quantity > 1).sum()", (V["quantity"] > 1).sum()),
            (27, "Ventas de productos de $20 o más", '=SUMAR.SI(G;">=20";H)', 'V.loc[V.price >= 20, "order_value"].sum()',
             V.loc[V["price"] >= 20, "order_value"].sum()),
            (28, f"Ventas del {V['order_date'].min():%d/%m/%Y}", "=SUMAR.SI(E;FECHA(...);H)",
             'V.loc[V.order_date == "...", "order_value"].sum()',
             V.loc[V["order_date"] == V["order_date"].min(), "order_value"].sum()),
        ]
        t = pd.DataFrame(filas, columns=["#", "qué quiero saber", "fórmula en Excel", "equivalente en pandas", "resultado"])
        t["resultado"] = [round(float(r), 2) if isinstance(r, (int, float, np.integer, np.floating)) else r
                          for r in t["resultado"]]
        return t.astype({"resultado": object})

    def practica(self) -> pd.DataFrame:
        """Hoja Práctica: las 11 preguntas con su respuesta calculada (como la hoja Soluciones)."""
        V, cat = self.V, self.V["category"]
        dia5 = V["order_date"].min() + pd.Timedelta(days=4)
        filas = [
            (0, "¿Cuántas líneas de venta hay?", "CONTARA", len(V)),
            (1, "Ventas totales de la categoría Electronics", "SUMAR.SI", V.loc[cat == "Electronics", "order_value"].sum()),
            (2, "Unidades vendidas desde Mobile", "SUMAR.SI", V.loc[V["device_type"] == "Mobile", "quantity"].sum()),
            (3, "Precio unitario promedio de la categoría Beauty", "PROMEDIO.SI",
             V.loc[cat == "Beauty", "price"].mean()),
            (4, f"Ventas del {dia5:%d/%m/%Y}", "SUMAR.SI y FECHA", V.loc[V["order_date"] == dia5, "order_value"].sum()),
            (5, "¿Cuántas líneas tienen más de una producto?", 'CONTAR.SI con ">1"', (V["quantity"] > 1).sum()),
            (6, "Precio unitario más alto", "MAX", V["price"].max()),
            (7, "Mediana de order_value", "MEDIANA", V["order_value"].median()),
            (8, "Ventas de Electronics desde Mobile", "SUMAR.SI.CONJUNTO",
             V.loc[(cat == "Electronics") & (V["device_type"] == "Mobile"), "order_value"].sum()),
            (9, "¿Cuántas productos distintas hay en el menú?", "CONTARA(UNICOS(…))", V["product_id"].nunique()),
            (10, "Ventas entre las 18:00 y las 20:59", "SUMAR.SI.CONJUNTO con la columna hora",
             V.loc[V["hora"].between(18, 20), "order_value"].sum()),
        ]
        t = pd.DataFrame(filas, columns=["#", "pregunta", "pista: función", "respuesta"])
        t["respuesta"] = t["respuesta"].astype(float).round(2)
        return t

    def pregunta_abierta(self) -> pd.DataFrame:
        """Compara la frecuencia de productos con sus ingresos y precios promedio."""
        t = (self.V.groupby("product_id")
             .agg(líneas=("order_id", "count"), productos=("quantity", "sum"), ventas=("order_value", "sum"),
                  precio_unit_promedio=("price", "mean")))
        t["puesto por líneas"] = t["líneas"].rank(ascending=False, method="min").astype(int)
        t["puesto por ventas"] = t["ventas"].rank(ascending=False, method="min").astype(int)
        return t.sort_values("líneas", ascending=False).head(6)

    # ================================================================== Descriptiva A · resumen del negocio
    @staticmethod
    def resumen_negocio(d: pd.DataFrame) -> pd.Series:
        ventas, productos = d["order_value"].sum(), d["quantity"].sum()
        pedidos, dias = d["nuevo_pedido"].sum(), d["order_date"].nunique()
        r = {
            "Ventas totales": ventas,                       # SUMA(order_value)
            "Unidades vendidas": productos,                      # SUMA(quantity)
            "Líneas de pedido": len(d),                     # CONTARA
            "Pedidos": pedidos,                             # SUMA(nuevo_pedido)
            "Ticket promedio": ventas / pedidos,            # ventas ÷ pedidos
            "Unidades por pedido": productos / pedidos,
            "Precio promedio por producto": ventas / productos,
            "Días con ventas": dias,
            "Venta promedio por día": ventas / dias,
        }
        if "customer_id" in d.columns:
            r["Clientes únicos"] = d["customer_id"].nunique()
            r["Pedidos por customer"] = pedidos / r["Clientes únicos"]
        return pd.Series(r)

    def resumen_total(self) -> pd.DataFrame:
        return self.resumen_negocio(self.V).to_frame("Empresa")

    # ================================================================== Descriptiva B · medidas
    @staticmethod
    def medidas(s: pd.Series) -> pd.Series:
        s = s.astype(float)
        return pd.Series({
            "n (datos)": s.count(), "Suma": s.sum(), "Media": s.mean(), "Mediana": s.median(),
            "Moda": s.mode().iloc[0], "Mínimo": s.min(), "Máximo": s.max(), "Rango": s.max() - s.min(),
            "Desviación estándar": s.std(ddof=1), "Coef. de variación": s.std(ddof=1) / s.mean(),
            "Q1 (25 %)": s.quantile(0.25), "Q3 (75 %)": s.quantile(0.75),
        })

    def medidas_variables(self) -> pd.DataFrame:
        return pd.DataFrame({"quantity": self.medidas(self.V["quantity"]),
                             "price": self.medidas(self.V["price"]),
                             "order_value": self.medidas(self.V["order_value"]),
                             "valor_pedido": self.medidas(self.pedidos["valor_pedido"])})

    def lectura_media_mediana(self) -> str:
        m = self.medidas(self.V["order_value"])
        rel = "mayor" if m["Media"] > m["Mediana"] else "menor"
        return (f"Lectura: en order_value la media (${m['Media']:.2f}) es {rel} que la mediana (${m['Mediana']:.2f}): "
                "unas pocas líneas con varias productos jalan el promedio hacia arriba (sesgo a la derecha).")

    # ================================================================== Descriptiva C-D · frecuencias
    def frecuencias(self, columna: str, d: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.V if d is None else d
        t = (d.groupby(columna, observed=True)
             .agg(líneas=("order_id", "count"), productos=("quantity", "sum"), ventas=("order_value", "sum"),
                  precio_unit_promedio=("price", "mean")))
        t.insert(1, "% líneas", t["líneas"] / t["líneas"].sum())
        t.insert(2, "% acumulado", t["% líneas"].cumsum())
        t.insert(5, "% ventas", t["ventas"] / t["ventas"].sum())
        t.index = t.index.astype(str)
        total = pd.DataFrame({"líneas": [t["líneas"].sum()], "% líneas": [1.0], "% acumulado": [np.nan],
                              "productos": [t["productos"].sum()], "ventas": [t["ventas"].sum()], "% ventas": [1.0],
                              "precio_unit_promedio": [d["price"].mean()]}, index=["Total"])
        return pd.concat([t, total])

    # ================================================================== Descriptiva E · distribución
    def distribucion_precio(self) -> pd.DataFrame:
        c = self.CORTES_PRECIO
        etiquetas = [f"${a} a ${b}" if b < 100 else f"${a} o más" for a, b in zip(c[:-1], c[1:])]
        t = (pd.cut(self.V["order_value"], bins=c, right=False, labels=etiquetas)
             .value_counts(sort=False).to_frame("líneas"))
        t["% líneas"] = t["líneas"] / t["líneas"].sum()
        t.index = t.index.astype(str)
        return t

    # ================================================================== Relaciones A · por día
    def ventas_por_dia(self, d: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.V if d is None else d
        t = (d.groupby("order_date")
             .agg(día=("dia_semana", "first"), líneas=("order_id", "count"), productos=("quantity", "sum"),
                  pedidos=("nuevo_pedido", "sum"), ventas=("order_value", "sum")))
        t["día"] = t["día"].astype(str)
        t["ticket promedio"] = t["ventas"] / t["pedidos"]
        t["% ventas"] = t["ventas"] / t["ventas"].sum()
        t["ventas producto elegido"] = d[d["product_id"] == self.producto_elegido].groupby("order_date")["order_value"].sum()
        t["ventas producto elegido"] = t["ventas producto elegido"].fillna(0)
        return t

    def lectura_dias(self, excluir_ultimo_incompleto: bool = False) -> str:
        t = self.ventas_por_dia()
        mejor = t["ventas"].idxmax()
        base_min = t.iloc[:-1] if excluir_ultimo_incompleto else t
        peor = base_min["ventas"].idxmin()
        nota = " (sin el último día, que está incompleto)" if excluir_ultimo_incompleto else ""
        pe = t["ventas producto elegido"]
        return (f"Día con más ventas: {mejor:%d/%m/%Y} ({t.loc[mejor, 'día']}) → ${t.loc[mejor, 'ventas']:,.2f}\n"
                f"Día con menos ventas{nota}: {peor:%d/%m/%Y} ({t.loc[peor, 'día']}) → ${t.loc[peor, 'ventas']:,.2f}\n"
                f"{self.producto_elegido}: ventas ${pe.sum():,.2f}; su mejor día {pe.idxmax():%d/%m/%Y}")

    def dia_semana_empresa(self) -> pd.Series:
        """Venta PROMEDIO por día de la semana."""
        return self.dia_semana_resumen()["venta promedio por día"]

    def dia_semana_resumen(self) -> pd.DataFrame:
        d = self.V[~self.V["order_date"].isin(self.dias_incompletos)]
        diario = d.groupby(["order_date", "dia_semana"], observed=True)["order_value"].sum().reset_index()
        t = diario.groupby("dia_semana", observed=True)["order_value"].agg(["count", "sum", "mean"])
        t.columns = ["días en el periodo", "ventas", "venta promedio por día"]
        t.index = t.index.astype(str)
        return t

    # ================================================================== Relaciones B-C
    def categoria_x_dispositivo(self, medida: str = "ventas", d: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.V if d is None else d
        if medida == "ventas":
            t = pd.crosstab(d["category"], d["device_type"], values=d["order_value"], aggfunc="sum",
                            margins=True, margins_name="Total").fillna(0)
        else:
            t = pd.crosstab(d["category"], d["device_type"], margins=True, margins_name="Total")
        t.index, t.columns = t.index.astype(str), t.columns.astype(str)
        if medida == "ventas":
            t.columns = [f"ventas {c}" for c in t.columns]
        return t

    def combinacion_lider(self) -> str:
        t = pd.crosstab(self.V["category"], self.V["device_type"], values=self.V["order_value"], aggfunc="sum")
        s = t.stack()
        return f"Lectura: la combinación que más vende es {s.idxmax()[0]} {s.idxmax()[1]} (${s.max():,.2f})."

    def consulta(self, fecha="2024-04-20", categoria="Electronics", dispositivo="Mobile", canal="Todos") -> pd.Series:
        """SUMAR.SI.CONJUNTO con varias condiciones ("Todas"/"Todos" ignora la condición)."""
        d = self.filtrar(canal, categoria, dispositivo)
        d = d[d["order_date"] == pd.Timestamp(fecha)]
        return pd.Series({"Ventas": round(d["order_value"].sum(), 2), "Unidades": int(d["quantity"].sum()),
                          "Líneas": len(d),
                          "Precio promedio": round(d["price"].mean(), 2) if len(d) else "No hubo ventas"})

    # ================================================================== Relaciones D · hora
    def ventas_por_hora(self) -> pd.DataFrame:
        t = self.V.groupby("hora").agg(líneas=("order_id", "count"), ventas=("order_value", "sum"))
        t["% ventas"] = t["ventas"] / t["ventas"].sum()
        return t

    # ================================================================== Relaciones E · ranking
    def ranking_productos(self, d: pd.DataFrame | None = None) -> pd.DataFrame:
        d = self.V if d is None else d
        t = (d.groupby("product_id")
             .agg(categoría=("category", "first"), productos=("quantity", "sum"), ventas=("order_value", "sum"))
             .sort_values("ventas", ascending=False))
        t["categoría"] = t["categoría"].astype(str)
        t.insert(0, "posición", t["ventas"].rank(ascending=False, method="min").astype(int))
        t["% ventas"] = t["ventas"] / t["ventas"].sum()
        t["% acumulado"] = t["% ventas"].cumsum()
        return t

    def productos_para_80(self) -> int:
        return int((self.ranking_productos()["% acumulado"] < 0.8).sum() + 1)

    # ================================================================== Tabla dinámica
    def tabla_dinamica(self, filas="category", columnas="device_type", valores="order_value",
                       canal="Todos", dia_semana="Todos") -> pd.DataFrame:
        d = self.filtrar(canal=canal, dia_semana=dia_semana)
        t = d.pivot_table(index=filas, columns=columnas, values=valores, aggfunc="sum",
                          margins=True, margins_name="Total", observed=True).fillna(0).round(2)
        t.columns = [f"suma {c}" for c in t.columns]
        return t

    # ================================================================== Dashboard (KPIs)
    def kpis(self, canal="Todos", categoria="Todas", dispositivo="Todos") -> dict:
        d = self.filtrar(canal, categoria, dispositivo)
        if d.empty:
            return {}
        dia = d.groupby("order_date")["order_value"].sum()
        hora = d.groupby("hora")["order_value"].sum()
        k = {"VENTAS": f"${d['order_value'].sum():,.2f}", "PRODUCTOS": f"{d['quantity'].sum():,}",
             "PEDIDOS": f"{d['order_id'].nunique():,}"}
        if "customer_id" in d.columns:
            k["CLIENTES"] = f"{d['customer_id'].nunique():,}"
        else:
            k["LÍNEAS"] = f"{len(d):,}"
        k.update({"PRECIO PROM./PRODUCTO": f"${d['order_value'].sum() / d['quantity'].sum():,.2f}",
                  "% VENTAS TOTALES": f"{d['order_value'].sum() / self.V['order_value'].sum():.1%}",
                  "MEJOR DÍA": f"{dia.idxmax():%d/%m}", "HORA PICO": f"{hora.idxmax()}:00",
                  "PRODUCTO LÍDER": str(d.groupby("product_id")["order_value"].sum().idxmax())})
        return k

    # ================================================================== conclusiones y exportación
    def hallazgos(self) -> list[str]:
        V, dias, dsem, hora = self.V, self.ventas_por_dia(), self.dia_semana_empresa(), self.ventas_por_hora()
        rk, cat, tam = self.ranking_productos(), self.frecuencias("category"), self.frecuencias("device_type")
        cat, tam = cat.drop("Total"), tam.drop("Total")
        mejor = dias["ventas"].idxmax()
        m = self.medidas(V["order_value"])
        return [
            f"En el periodo {self.periodo()} se vendieron ${V['order_value'].sum():,.2f}: {V['quantity'].sum():,} productos "
            f"en {V['nuevo_pedido'].sum():,} pedidos (ticket promedio ${V['order_value'].sum() / V['nuevo_pedido'].sum():.2f}; "
            f"{V['quantity'].sum() / V['nuevo_pedido'].sum():.2f} productos por pedido).",
            f"El día de mayor venta fue el {mejor:%d/%m} ({dias.loc[mejor, 'día']}); en promedio el día de la semana más "
            f"fuerte es el {dsem.idxmax()} y el más flojo el {dsem.idxmin()}.",
            f"La hora pico es las {hora['ventas'].idxmax()}:00; hay dos picos (almuerzo y comida).",
            f"Tamaño: {tam['líneas'].idxmax()} es el más vendido ({tam.loc[tam['líneas'].idxmax(), '% ventas']:.1%} de las ventas). "
            f"Categoría: {cat['ventas'].idxmax()} lidera en ventas y {cat['líneas'].idxmax()} en líneas.",
            f"{rk.index[0]} es la producto que más vende; {self.productos_para_80()} de {len(rk)} productos explican el 80 % de las ventas.",
            f"order_value: media ${m['Media']:.2f} vs. mediana ${m['Mediana']:.2f} → distribución sesgada a la derecha.",
        ]

    def tablas_exportables(self) -> dict[str, pd.DataFrame]:
        return {
            "Datos": self.V.assign(order_time=self.V["order_time"].astype(str)),
            "Formulas": self.formulas_basicas(),
            "Resumen_negocio": self.resumen_total().reset_index(names="indicador"),
            "Medidas": self.medidas_variables().reset_index(names="medida"),
            "Frec_dispositivo": self.frecuencias("device_type").reset_index(names="tamaño"),
            "Frec_categoria": self.frecuencias("category").reset_index(names="categoría"),
            "Distribucion_precio": self.distribucion_precio().reset_index(names="intervalo"),
            "Ventas_dia": self.ventas_por_dia().reset_index(),
            "Dia_semana": self.dia_semana_resumen().reset_index(names="día"),
            "Categoria_x_dispositivo": self.categoria_x_dispositivo().reset_index(),
            "Ventas_hora": self.ventas_por_hora().reset_index(),
            "Ranking_productos": self.ranking_productos().reset_index(),
            "Tabla_dinamica": self.tabla_dinamica().reset_index(),
            "Practica": self.practica(),
        }

    def exportar_excel(self, ruta="reportes/analisis_ecommerce.xlsx") -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tablas = self.tablas_exportables()
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            for nombre, t in tablas.items():
                t = t.copy()
                for c in t.columns:
                    if isinstance(t[c].dtype, pd.CategoricalDtype):
                        t[c] = t[c].astype(str)
                t.columns = [str(c) for c in t.columns]
                t.to_excel(writer, sheet_name=nombre[:31], index=False)
        print(f"Reporte con {len(tablas)} hojas guardado en {ruta}")
        return ruta


class AnalisisEcommerce(AnalisisBase):
    """Anal?tica espec?fica del dataset de e-commerce."""

    def __init__(self, ventas: pd.DataFrame, producto_elegido: int = 1):
        super().__init__(ventas, producto_elegido)

    def ventas_por_canal(self) -> pd.DataFrame:
        return self._resumen_dimension("channel")

    def ventas_por_segmento(self) -> pd.DataFrame:
        return self._resumen_dimension("customer_segment")

    def ventas_por_dispositivo(self) -> pd.DataFrame:
        return self._resumen_dimension("device_type")

    def ventas_por_categoria(self) -> pd.DataFrame:
        return self._resumen_dimension("category")

    def estado_entregas(self) -> pd.DataFrame:
        return self._resumen_dimension("delivery_status")

    def _resumen_dimension(self, columna: str) -> pd.DataFrame:
        t = (self.V.groupby(columna, observed=True)
             .agg(pedidos=("order_id", "nunique"), customers=("customer_id", "nunique"),
                  unidades=("quantity", "sum"), ventas=("order_value", "sum"),
                  precio_promedio=("price", "mean"), ticket_promedio=("order_value", "mean"))
             .sort_values("ventas", ascending=False))
        t["% ventas"] = t["ventas"] / t["ventas"].sum()
        return t

    def resumen_customers(self) -> pd.DataFrame:
        return (self.V.groupby(["customer_id", "customer_segment"], as_index=False)
                .agg(pedidos=("order_id", "nunique"), unidades=("quantity", "sum"),
                     ventas=("order_value", "sum"), ticket_promedio=("order_value", "mean"),
                     dias_envio_promedio=("shipping_days", "mean") if "shipping_days" in self.V else ("shipping_date", "count"))
                .sort_values("ventas", ascending=False))

    def resumen_entregas(self) -> pd.DataFrame:
        d = self.V.copy()
        if "shipping_days" not in d:
            d["shipping_days"] = (pd.to_datetime(d["shipping_date"]) - pd.to_datetime(d["order_date"])).dt.total_seconds() / 86400
        return (d.groupby("delivery_status", as_index=False)
                .agg(pedidos=("order_id", "nunique"), ventas=("order_value", "sum"),
                     dias_envio_promedio=("shipping_days", "mean"))
                .sort_values("pedidos", ascending=False))

    def tablas_exportables(self) -> dict[str, pd.DataFrame]:
        return {
            "Resumen": self.resumen_total(),
            "Canales": self.ventas_por_canal().reset_index(),
            "Segmentos": self.ventas_por_segmento().reset_index(),
            "Dispositivos": self.ventas_por_dispositivo().reset_index(),
            "Categorias": self.ventas_por_categoria().reset_index(),
            "Entregas": self.resumen_entregas(),
            "Clientes": self.resumen_customers(),
        }
