"""Dashboard web de e-commerce con Streamlit + Plotly.

La clase :class:`DashboardStreamlit` toma el dataset enriquecido de la Semana 5
(``datos/ecommerce_enriquecido.csv``) y:

1. calcula los indicadores reutilizando :class:`AnalisisEcommerce` (mismas cifras que el notebook);
2. arma cada visual como una figura de Plotly (se puede ver en Jupyter o en la web);
3. redacta la respuesta a la pregunta de negocio con cifras calculadas, no escritas a mano;
4. compone todo en una app de Streamlit con filtros (``render()``), lista para publicarse
   en Streamlit Community Cloud desde GitHub.

Uso en Jupyter::

    dash = DashboardStreamlit.desde_csv("datos/ecommerce_enriquecido.csv")
    dash.kpis()
    dash.figura_ventas_canal()

Uso en la app (``src/clases_po/app.py``)::

    DashboardStreamlit.desde_csv(RUTA_DATOS).render()
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

try:  # dentro del paquete clases_po
    from .analisis import AnalisisEcommerce
except ImportError:  # cuando la app agrega src/clases_po al path y lo importa como módulo suelto
    from analisis import AnalisisEcommerce


DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ORDEN_DISPOSITIVOS = ["Mobile", "Tablet", "Desktop"]
ORDEN_CATEGORIAS = ["Beauty", "Books", "Clothing", "Electronics", "Home", "Toys"]
ORDEN_ENTREGA = ["Delivered", "Shipped", "Pending", "Returned"]
COLOR_ENTREGA = {"Delivered": "#1baf7a", "Shipped": "#2a78d6", "Pending": "#eda100", "Returned": "#e34948"}

ABREV_ESTADOS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def dinero(x: float, decimales: int = 0) -> str:
    """$5.334.933 · formato con punto de miles y coma decimal."""
    s = f"{x:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"${s}"


def numero(x: float, decimales: int = 0) -> str:
    return f"{x:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x: float, decimales: int = 1) -> str:
    return f"{x * 100:.{decimales}f} %".replace(".", ",")


class DashboardStreamlit:
    """Dashboard de ventas de e-commerce: figuras Plotly + app Streamlit.

    Parámetros
    ----------
    ventas : DataFrame enriquecido (una fila por pedido) con las columnas de la Semana 5.
    titulo : título de la app.
    """

    # Un color fijo por canal (identidad), siempre en el mismo orden; nunca por posición en el ranking
    PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
    COLOR = "#2a78d6"
    CLARO = "#9ec5f0"
    ACENTO = "#eb6834"
    TEXTO, TEXTO_2, REJILLA = "#1f1f1e", "#5f5e5a", "#e6e5e0"
    ESCALA = "Blues"

    PREGUNTA_NEGOCIO = (
        "¿Qué, cuándo, a quién y dónde le vende la tienda en línea entre abril de 2024 y abril de 2025, "
        "y en qué debe enfocar sus recursos: canales, productos, clientes y entregas?"
    )
    PREGUNTAS = {
        "P1": "¿Qué canal de adquisición y qué segmento de cliente aportan más a las ventas?",
        "P2": "¿Cuándo se concentra la demanda (mes y día de la semana)?",
        "P3": "¿Qué se vende: categorías, dispositivos y productos?",
        "P4": "¿Quiénes son los clientes y qué tan fieles son?",
        "P5": "¿Cómo funcionan las entregas y de dónde son los pedidos?",
    }

    COLUMNAS_REQUERIDAS = ["order_id", "customer_id", "product_id", "category", "price", "quantity",
                           "order_date", "shipping_date", "delivery_status", "device_type", "channel",
                           "customer_segment"]

    def __init__(self, ventas: pd.DataFrame, titulo: str = "E-commerce · Ventas, clientes y entregas"):
        faltan = [c for c in self.COLUMNAS_REQUERIDAS if c not in ventas.columns]
        if "estado" not in ventas.columns and "shipping_address" not in ventas.columns:
            faltan.append("estado (o shipping_address)")
        if faltan:
            raise ValueError(f"Al dataset le faltan columnas del e-commerce: {faltan}")
        self.titulo = titulo
        self.V_total = self.tipar(ventas)
        self.orden_canal = sorted(self.V_total["channel"].unique())
        self.color_canal = {c: self.PALETA[i % len(self.PALETA)] for i, c in enumerate(self.orden_canal)}
        self._preparar(self.V_total)

    # ================================================================== datos
    @classmethod
    def desde_csv(cls, ruta: str | Path, **kwargs) -> "DashboardStreamlit":
        """Carga el CSV enriquecido de la Semana 5."""
        return cls(pd.read_csv(ruta), **kwargs)

    @staticmethod
    def exportar_datos(origen: str | Path, destino: str | Path,
                       excluir=("shipping_address", "billing_address", "order_time", "fecha_hora",
                                "total_calculado", "verificacion")) -> Path:
        """Copia el CSV enriquecido a la carpeta de la app sin las columnas que el dashboard no usa.

        Antes de quitar la dirección de envío guarda su ``estado`` (de EE. UU.). Así la app no publica
        direcciones y el archivo pesa menos. La app lee su propia copia (``src/clases_po/datos``)
        porque la GitHub Action limpia ``src/sincronicas/datos`` en cada push.
        """
        d = pd.read_csv(origen)
        if "estado" not in d.columns and "shipping_address" in d.columns:
            d["estado"] = AnalisisEcommerce.extraer_estado(d["shipping_address"])
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        d.drop(columns=[c for c in excluir if c in d.columns]).to_csv(destino, index=False)
        print(f"{len(d):,} filas → {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
        return destino

    @staticmethod
    def tipar(df: pd.DataFrame) -> pd.DataFrame:
        """El CSV pierde los tipos de pandas: se vuelven a poner (mismo criterio de PreprocesadorEcommerce)."""
        d = df.copy()
        d["order_date"] = pd.to_datetime(d["order_date"])
        d["shipping_date"] = pd.to_datetime(d["shipping_date"])
        for c in ["order_id", "delivery_status", "channel", "customer_segment"]:
            d[c] = d[c].astype(str)
        for c in ["customer_id", "product_id", "quantity"]:
            d[c] = d[c].astype("int64")
        d["price"] = d["price"].astype("float64")
        d["device_type"] = pd.Categorical(d["device_type"], categories=ORDEN_DISPOSITIVOS, ordered=True)
        d["category"] = pd.Categorical(d["category"], categories=ORDEN_CATEGORIAS)
        if "order_value" not in d.columns:
            d["order_value"] = (d["quantity"] * d["price"]).round(2)
        if "shipping_days" not in d.columns:
            d["shipping_days"] = ((d["shipping_date"] - d["order_date"]).dt.total_seconds() / 86400).round(2)
        if "estado" not in d.columns:
            d["estado"] = AnalisisEcommerce.extraer_estado(d["shipping_address"])
        d["estado"] = d["estado"].astype(str)
        d["hora"] = d["order_date"].dt.hour.astype("int64")
        d["dia_semana"] = pd.Categorical(d["order_date"].dt.dayofweek.map(dict(enumerate(DIAS_SEMANA))),
                                         categories=DIAS_SEMANA, ordered=True)
        d["nuevo_pedido"] = (~d["order_id"].duplicated()).astype("int64")
        return d

    def _preparar(self, V: pd.DataFrame) -> None:
        """Crea el objeto de análisis (AnalisisEcommerce) para los datos filtrados."""
        self.V = V
        self.A = AnalisisEcommerce(V) if len(V) else None

    def filtrar(self, canales=None, categorias=None, dispositivos=None, estados_entrega=None,
                fechas=None) -> "DashboardStreamlit":
        """Devuelve un dashboard nuevo con los datos filtrados (los colores por canal se conservan)."""
        V = self.V_total
        if canales:
            V = V[V["channel"].isin(canales)]
        if categorias:
            V = V[V["category"].astype(str).isin(categorias)]
        if dispositivos:
            V = V[V["device_type"].astype(str).isin(dispositivos)]
        if estados_entrega:
            V = V[V["delivery_status"].isin(estados_entrega)]
        if fechas and len(fechas) == 2:
            ini, fin = pd.Timestamp(fechas[0]), pd.Timestamp(fechas[1])
            dia = V["order_date"].dt.normalize()       # la fecha trae hora: se compara solo el día
            V = V[(dia >= ini) & (dia <= fin)]
        nuevo = object.__new__(DashboardStreamlit)
        nuevo.__dict__.update({k: v for k, v in self.__dict__.items() if k not in ("V", "A")})
        nuevo._preparar(V.copy())
        return nuevo

    @property
    def vacio(self) -> bool:
        return self.A is None or self.V.empty

    def periodo(self) -> str:
        f = self.V["order_date"]
        return f"{f.min():%d/%m/%Y} a {f.max():%d/%m/%Y}"

    # ================================================================== indicadores
    def kpis(self) -> dict:
        """Indicadores clave (los mismos de la Semana 5, ahora para la vista filtrada)."""
        V = self.V
        ventas, pedidos = V["order_value"].sum(), V["order_id"].nunique()
        return {
            "Ventas": ventas,
            "Pedidos": pedidos,
            "Ticket promedio": ventas / pedidos,
            "Clientes": V["customer_id"].nunique(),
            "Unidades por pedido": V["quantity"].sum() / pedidos,
            "Días de envío (prom.)": V["shipping_days"].mean(),
            "% de las ventas totales": ventas / self.V_total["order_value"].sum(),
        }

    def kpis_tabla(self) -> pd.DataFrame:
        k = self.kpis()
        fmt = {"Ventas": dinero(k["Ventas"]), "Pedidos": numero(k["Pedidos"]),
               "Ticket promedio": dinero(k["Ticket promedio"], 2), "Clientes": numero(k["Clientes"]),
               "Unidades por pedido": numero(k["Unidades por pedido"], 2),
               "Días de envío (prom.)": numero(k["Días de envío (prom.)"], 1),
               "% de las ventas totales": pct(k["% de las ventas totales"])}
        return pd.DataFrame({"indicador": fmt.keys(), "valor": fmt.values()})

    # ================================================================== respuesta de negocio
    def respuestas(self) -> list[dict]:
        """Pregunta → respuesta (con cifras) → visual que la muestra → decisión sugerida."""
        A, V = self.A, self.V
        r = []

        # ---- P1 · canales y segmentos
        canal, seg = A.ventas_por_canal(), A.ventas_por_segmento()
        top, ult = canal.iloc[0], canal.iloc[-1]
        brecha = (top["% ventas"] - ult["% ventas"]) * 100
        texto_seg = "; ".join(f"{s} {pct(v)}" for s, v in seg["% ventas"].items())
        if len(canal) == 1:
            resp = f"Solo hay un canal en la vista: {canal.index[0]} ({dinero(top['ventas'])})."
            dec = "Amplía el filtro de canales para comparar."
        else:
            resp = (f"{canal.index[0]} lidera con {dinero(top['ventas'])} ({pct(top['% ventas'])}) y "
                    f"{canal.index[-1]} es el de menor venta ({pct(ult['% ventas'])}): "
                    f"{numero(brecha, 1)} puntos de diferencia. Por segmento de cliente: {texto_seg}.")
            dec = ("Los canales venden de forma parecida: no conviene concentrar la inversión en uno solo "
                   "sin comparar antes su costo de adquisición (el dataset no lo trae)."
                   if brecha < 5 else
                   f"Priorizar presupuesto en {canal.index[0]} y revisar el plan de {canal.index[-1]}.")
        mejor_seg = seg.index[0]
        dec += f" El segmento {mejor_seg} aporta {pct(seg['% ventas'].iloc[0], 0)} de las ventas: protegerlo es prioridad."
        r.append({"id": "P1", "pregunta": self.PREGUNTAS["P1"], "respuesta": resp,
                  "visual": "Barras horizontales ordenadas de mayor a menor, un color por canal.",
                  "decision": dec})

        # ---- P2 · cuándo
        dsem = A.dia_semana_resumen()["venta promedio por día"]
        diario = A.ventas_diarias_canal().sum(axis=1)
        m = A.ventas_mensuales()
        completos = m[m["completo"]]
        texto_mes = ""
        if len(completos):
            mm = completos["ventas"].idxmax()
            texto_mes = f" El mes completo con más ventas es {MESES[mm.month - 1]} {mm.year} ({dinero(completos['ventas'].max())})."
        dif = (dsem.max() - dsem.min()) / dsem.min() if len(dsem) > 1 and dsem.min() > 0 else 0
        resp = (f"El {dsem.idxmax()} es el día de la semana más fuerte ({dinero(dsem.max())} en promedio) y el "
                f"{dsem.idxmin()} el más flojo ({dinero(dsem.min())}): {pct(dif, 0)} de diferencia."
                f"{texto_mes} El día con más ventas fue el {diario.idxmax():%d/%m/%Y} ({dinero(diario.max())}). "
                "Todos los pedidos tienen la misma hora del día, así que el dataset no permite analizar horarios.")
        dec = (f"Reforzar campañas y atención el {dsem.idxmax()}; usar promociones el {dsem.idxmin()} para mover la demanda."
               if dif >= 0.10 else
               "La demanda es pareja durante la semana: no hay un día que justifique turnos o campañas especiales.")
        r.append({"id": "P2", "pregunta": self.PREGUNTAS["P2"], "respuesta": resp,
                  "visual": "Ventas diarias con promedio móvil, ventas por mes y mapa de calor día × canal.",
                  "decision": dec})

        # ---- P3 · qué
        cat, disp, rk = A.ventas_por_categoria(), A.ventas_por_dispositivo(), A.ranking_productos()
        n80 = A.productos_para_80()
        perfil = A.mix_canal("category").idxmax(axis=1)
        texto_perfil = "; ".join(f"{c} → {k}" for c, k in perfil.items()) if len(perfil) > 1 else ""
        resp = (f"{cat.index[0]} es la categoría con más ventas ({dinero(cat['ventas'].iloc[0])}, "
                f"{pct(cat['% ventas'].iloc[0])}) y {cat.index[-1]} la de menos ({pct(cat['% ventas'].iloc[-1])}). "
                f"{disp.index[0]} es el dispositivo líder ({pct(disp['% ventas'].iloc[0])}). "
                f"El producto {rk.index[0]} es el que más vende, con solo {pct(rk['% ventas'].iloc[0], 2)} del total; "
                f"{n80} de {len(rk)} productos explican el 80 % de las ventas."
                + (f" Categoría dominante por canal: {texto_perfil}." if texto_perfil else ""))
        dec = ("El catálogo está muy repartido: ningún producto concentra las ventas, así que recortar el catálogo "
               "tendría poco efecto y conviene decidir por categoría."
               if n80 / len(rk) > 0.5 else
               "Las ventas se concentran en pocos productos: asegurar su inventario y revisar los de baja rotación.")
        r.append({"id": "P3", "pregunta": self.PREGUNTAS["P3"], "respuesta": resp,
                  "visual": "Barras por categoría y dispositivo, mapa de calor canal × categoría y top 10 de productos.",
                  "decision": dec})

        # ---- P4 · clientes
        pc = A.clientes_detalle()
        seg_cli = pc["segmento"].value_counts(normalize=True).reindex(pc["segmento"].cat.categories).fillna(0)
        seg_ven = (pc.groupby("segmento", observed=False)["ventas"].sum() / pc["ventas"].sum()).fillna(0)
        mas_de_uno = (pc["pedidos"] > 1).mean()
        resp = (f"{numero(len(pc))} clientes con {numero(pc['pedidos'].mean(), 2)} pedidos en promedio; "
                f"{pct(mas_de_uno, 0)} compró más de una vez. Los muy frecuentes (6+ pedidos) son el "
                f"{pct(seg_cli['Muy frecuente (6+)'], 0)} de los clientes y generan el "
                f"{pct(seg_ven['Muy frecuente (6+)'], 0)} de las ventas; el 20 % de mejores clientes aporta el "
                f"{pct(A.pareto_20(pc), 0)}.")
        r.append({"id": "P4", "pregunta": self.PREGUNTAS["P4"], "respuesta": resp,
                  "visual": "Columnas de % de clientes frente a % de ventas por segmento de frecuencia y curva de Pareto.",
                  "decision": "Programa de fidelización para los clientes frecuentes y muy frecuentes, y campaña de "
                              f"segunda compra para el {pct(seg_cli['Ocasional (1)'], 0)} que pidió una sola vez."})

        # ---- P5 · entregas y estados
        ent = A.estado_entregas()
        tot = ent["pedidos"].sum()
        p = {s: ent["pedidos"].get(s, 0) / tot for s in ORDEN_ENTREGA}
        tardios = (V["shipping_days"] > 3).mean()
        est = A.ventas_por_estado()
        dev = V.groupby("category", observed=True)["delivery_status"].apply(lambda s: (s == "Returned").mean())
        resp = (f"{pct(p['Delivered'], 0)} de los pedidos está entregado, {pct(p['Shipped'], 0)} en camino, "
                f"{pct(p['Pending'], 0)} pendiente y {pct(p['Returned'], 0)} devuelto. El envío tarda "
                f"{numero(V['shipping_days'].mean(), 1)} días en promedio y el {pct(tardios, 0)} tarda más de 3 días. "
                f"Los pedidos vienen de {len(est)} estados de EE. UU.; el mayor es {est.index[0]} "
                f"({pct(est['% ventas'].iloc[0])} de las ventas).")
        r.append({"id": "P5", "pregunta": self.PREGUNTAS["P5"], "respuesta": resp,
                  "visual": "Barras por estado de entrega, estados de entrega por canal y mapa de ventas por estado.",
                  "decision": f"Atacar los envíos de más de 3 días ({pct(tardios, 0)} de los pedidos) y revisar las "
                              f"devoluciones, que son más altas en {dev.idxmax()} ({pct(dev.max())}). "
                              + ("Las ventas están repartidas por todo el país: ningún estado destaca lo suficiente "
                                 "como para justificar una decisión logística propia sin más datos."
                                 if est["% ventas"].iloc[0] < 0.05 else
                                 f"{est.index[0]} concentra una parte alta de las ventas: revisar su logística.")})
        return r

    def respuestas_tabla(self) -> pd.DataFrame:
        return pd.DataFrame(self.respuestas()).set_index("id")

    # ================================================================== estilo de las figuras
    def _estilo(self, fig: go.Figure, titulo: str = "", alto: int = 380, leyenda: bool = False) -> go.Figure:
        fig.update_layout(
            title={"text": titulo, "x": 0, "xanchor": "left", "font": {"size": 15, "color": self.TEXTO}},
            height=alto, margin={"l": 10, "r": 10, "t": 50 if titulo else 10, "b": 10},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter, Segoe UI, sans-serif", "size": 12, "color": self.TEXTO_2},
            separators=",.", showlegend=leyenda,
            legend={"orientation": "h", "yanchor": "top", "y": -0.12, "xanchor": "left", "x": 0, "title": None},
            hoverlabel={"bgcolor": "white", "font_size": 12},
        )
        fig.update_xaxes(showgrid=False, linecolor=self.REJILLA, ticks="", title_text=None)
        fig.update_yaxes(gridcolor=self.REJILLA, zeroline=False, linecolor=self.REJILLA, title_text=None,
                         tickformat=",.0f")
        if leyenda:
            fig.update_layout(margin={"b": 60})
        return fig

    # ================================================================== P1 · canales y segmentos
    def figura_ventas_canal(self) -> go.Figure:
        d = self.A.ventas_por_canal().sort_values("ventas")
        etiqueta = [f"{dinero(v)} · {pct(p)}" for v, p in zip(d["ventas"], d["% ventas"])]
        fig = go.Figure(go.Bar(
            x=d["ventas"], y=d.index.astype(str), orientation="h", text=etiqueta, textposition="outside",
            marker={"color": [self.color_canal[c] for c in d.index.astype(str)], "cornerradius": 4},
            customdata=np.stack([d["pedidos"], d["ticket_promedio"], d["customers"]], axis=-1),
            hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Pedidos: %{customdata[0]:,}"
                          "<br>Ticket: $%{customdata[1]:,.2f}<br>Clientes: %{customdata[2]:,}<extra></extra>",
            cliponaxis=False, width=0.6))
        fig.update_xaxes(range=[0, d["ventas"].max() * 1.3], tickprefix="$", showticklabels=False)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, "P1 · Ventas por canal de adquisición", alto=60 * len(d) + 90)

    def figura_ventas_segmento(self) -> go.Figure:
        d = self.A.ventas_por_segmento().sort_values("ventas")
        fig = go.Figure(go.Bar(x=d["ventas"], y=d.index.astype(str), orientation="h", width=0.55,
                               text=[pct(p) for p in d["% ventas"]], textposition="outside", cliponaxis=False,
                               marker={"color": self.COLOR, "cornerradius": 4},
                               customdata=np.stack([d["pedidos"], d["customers"]], axis=-1),
                               hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<br>Pedidos: %{customdata[0]:,}"
                                             "<br>Clientes: %{customdata[1]:,}<extra></extra>"))
        fig.update_xaxes(range=[0, d["ventas"].max() * 1.2], showticklabels=False)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, "Ventas por segmento de cliente", alto=60 * len(d) + 90)

    # ================================================================== P2 · cuándo
    def figura_ventas_diarias(self) -> go.Figure:
        s = self.A.ventas_diarias_canal().sum(axis=1)
        s = s.reindex(pd.date_range(s.index.min(), s.index.max()), fill_value=0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="Ventas del día",
                                 line={"color": self.CLARO, "width": 1},
                                 hovertemplate="%{x|%d/%m/%Y}<br>$%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=s.index, y=s.rolling(7, min_periods=1).mean(), mode="lines",
                                 name="Promedio de 7 días", line={"color": self.COLOR, "width": 2.5},
                                 hovertemplate="%{x|%d/%m/%Y}<br>Promedio 7 días: $%{y:,.0f}<extra></extra>"))
        fig.update_yaxes(tickprefix="$", rangemode="tozero")
        fig.update_xaxes(tickformat="%b %Y")
        return self._estilo(fig, "Ventas diarias", alto=360, leyenda=True)

    def figura_ventas_mensuales(self) -> go.Figure:
        m = self.A.ventas_mensuales()
        etiquetas = [f"{MESES[p.month - 1]} {p.year}" + ("" if ok else "*") for p, ok in zip(m.index, m["completo"])]
        fig = go.Figure(go.Bar(
            x=etiquetas, y=m["ventas"], width=0.65,
            marker={"color": [self.COLOR if ok else self.CLARO for ok in m["completo"]], "cornerradius": 4},
            customdata=np.stack([m["dias"], m["dias_del_mes"]], axis=-1),
            hovertemplate="<b>%{x}</b><br>Ventas: $%{y:,.0f}<br>Días con datos: %{customdata[0]} de "
                          "%{customdata[1]}<extra></extra>"))
        fig.update_yaxes(tickprefix="$")
        return self._estilo(fig, "Ventas por mes (* mes incompleto en los datos)", alto=360)

    def figura_dia_semana(self) -> go.Figure:
        t = self.A.dia_semana_canal()
        y = list(t.index.astype(str))
        fig = go.Figure(go.Heatmap(
            z=t.values, x=list(t.columns), y=y, colorscale=self.ESCALA, xgap=2, ygap=2,
            text=[[dinero(v) for v in fila] for fila in t.values], texttemplate="%{text}",
            hovertemplate="<b>%{y}</b> · %{x}<br>Venta promedio: $%{z:,.0f}<extra></extra>",
            colorbar={"tickprefix": "$", "tickformat": ",.0f", "thickness": 10, "len": 0.8}))
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, "P2 · Venta promedio por día de la semana y canal", alto=60 * len(y) + 110)

    # ================================================================== P3 · qué
    def figura_categorias(self) -> go.Figure:
        d = self.A.ventas_por_categoria().sort_values("ventas")
        etiqueta = [f"{dinero(v)} · {pct(p)}" for v, p in zip(d["ventas"], d["% ventas"])]
        fig = go.Figure(go.Bar(x=d["ventas"], y=d.index.astype(str), orientation="h", width=0.6,
                               text=etiqueta, textposition="outside", cliponaxis=False,
                               marker={"color": self.COLOR, "cornerradius": 4},
                               hovertemplate="<b>%{y}</b><br>Ventas: $%{x:,.0f}<extra></extra>"))
        fig.update_xaxes(range=[0, d["ventas"].max() * 1.3], showticklabels=False)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, "P3 · Ventas por categoría", alto=48 * len(d) + 90)

    def figura_mix_categoria(self) -> go.Figure:
        t = self.A.mix_canal("category")
        y = list(t.index.astype(str))
        fig = go.Figure(go.Heatmap(
            z=t.values, x=list(t.columns), y=y, colorscale=self.ESCALA, xgap=2, ygap=2,
            text=[[pct(v) for v in fila] for fila in t.values], texttemplate="%{text}",
            hovertemplate="<b>%{y}</b> · %{x}<br>%{z:.1%} de sus ventas<extra></extra>",
            colorbar={"tickformat": ".0%", "thickness": 10, "len": 0.8}))
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, "% de las ventas de cada canal por categoría", alto=60 * len(y) + 110)

    def figura_dispositivos(self) -> go.Figure:
        t = self.A.ventas_por_dispositivo()
        t.index = t.index.astype(str)
        t = t.reindex([x for x in ORDEN_DISPOSITIVOS if x in t.index])
        fig = go.Figure(go.Bar(x=t.index, y=t["ventas"], width=0.55, marker={"color": self.COLOR, "cornerradius": 4},
                               text=[pct(p) for p in t["% ventas"]], textposition="outside", cliponaxis=False,
                               customdata=np.stack([t["pedidos"], t["unidades"]], axis=-1),
                               hovertemplate="<b>%{x}</b><br>Ventas: $%{y:,.0f}<br>Pedidos: %{customdata[0]:,}"
                                             "<br>Unidades: %{customdata[1]:,}<extra></extra>"))
        fig.update_yaxes(tickprefix="$", range=[0, t["ventas"].max() * 1.18])
        return self._estilo(fig, "Ventas por dispositivo (texto: % de ventas)", alto=340)

    def figura_top_productos(self, n: int = 10) -> go.Figure:
        rk = self.A.ranking_productos().head(n).iloc[::-1]
        fig = go.Figure(go.Bar(x=rk["ventas"], y=[f"Producto {i}" for i in rk.index], orientation="h", width=0.6,
                               marker={"color": self.COLOR, "cornerradius": 4},
                               customdata=np.stack([rk["categoría"], rk["productos"], rk["% ventas"]], axis=-1),
                               hovertemplate="<b>%{y}</b> · %{customdata[0]}<br>Ventas: $%{x:,.0f}"
                                             "<br>Unidades: %{customdata[1]:,}<br>%{customdata[2]:.2%} del total"
                                             "<extra></extra>"))
        fig.update_xaxes(tickprefix="$", showgrid=True, gridcolor=self.REJILLA)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
        return self._estilo(fig, f"Top {n} productos por ventas", alto=32 * n + 90)

    # ================================================================== P4 · clientes
    def figura_segmentos(self) -> go.Figure:
        pc = self.A.clientes_detalle()
        cli = pc["segmento"].value_counts(normalize=True).reindex(pc["segmento"].cat.categories).fillna(0)
        ven = (pc.groupby("segmento", observed=False)["ventas"].sum() / pc["ventas"].sum()).reindex(cli.index).fillna(0)
        fig = go.Figure([
            go.Bar(name="% de clientes", x=cli.index.astype(str), y=cli.values, marker_color=self.CLARO,
                   marker_cornerradius=4, text=[pct(v, 0) for v in cli.values], textposition="outside",
                   hovertemplate="%{x}<br>%{y:.1%} de los clientes<extra></extra>"),
            go.Bar(name="% de ventas", x=ven.index.astype(str), y=ven.values, marker_color=self.COLOR,
                   marker_cornerradius=4, text=[pct(v, 0) for v in ven.values], textposition="outside",
                   hovertemplate="%{x}<br>%{y:.1%} de las ventas<extra></extra>"),
        ])
        fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
        fig = self._estilo(fig, "P4 · Clientes vs. ventas por segmento de frecuencia", alto=380, leyenda=True)
        fig.update_yaxes(tickformat=".0%", range=[0, max(cli.max(), ven.max()) * 1.2])
        return fig

    def figura_pareto_clientes(self) -> go.Figure:
        v = self.A.clientes_detalle()["ventas"].sort_values(ascending=False).to_numpy()
        x = np.arange(1, len(v) + 1) / len(v)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Reparto parejo",
                                 line={"color": self.REJILLA, "width": 1.5, "dash": "dash"}, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=v.cumsum() / v.sum(), mode="lines", name="Clientes",
                                 line={"color": self.COLOR, "width": 2.5},
                                 hovertemplate="%{x:.0%} de clientes → %{y:.0%} de ventas<extra></extra>"))
        fig.add_vline(x=0.2, line_dash="dot", line_color=self.TEXTO_2, line_width=1,
                      annotation_text="20 % de clientes", annotation_position="bottom right",
                      annotation_font={"size": 11, "color": self.TEXTO_2})
        fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=self.REJILLA)
        fig = self._estilo(fig, "Curva de Pareto de clientes", alto=380, leyenda=True)
        fig.update_yaxes(tickformat=".0%", range=[0, 1.02])
        return fig

    # ================================================================== P5 · entregas y estados
    def figura_entregas(self) -> go.Figure:
        t = self.A.estado_entregas()
        t = t.reindex([s for s in ORDEN_ENTREGA if s in t.index])
        total = t["pedidos"].sum()
        fig = go.Figure(go.Bar(
            x=t.index, y=t["pedidos"], width=0.55,
            marker={"color": [COLOR_ENTREGA[s] for s in t.index], "cornerradius": 4},
            text=[f"{numero(n)} · {pct(n / total)}" for n in t["pedidos"]], textposition="outside", cliponaxis=False,
            customdata=np.stack([t["ventas"], t["ticket_promedio"]], axis=-1),
            hovertemplate="<b>%{x}</b><br>Pedidos: %{y:,}<br>Ventas: $%{customdata[0]:,.0f}"
                          "<br>Ticket: $%{customdata[1]:,.2f}<extra></extra>"))
        fig.update_yaxes(range=[0, t["pedidos"].max() * 1.18])
        return self._estilo(fig, "P5 · Pedidos por estado de entrega", alto=360)

    def figura_entregas_canal(self) -> go.Figure:
        t = self.A.entregas_canal()
        y = list(t.index.astype(str))
        fig = go.Figure([
            go.Bar(name=s, y=y, x=t[s], orientation="h", marker_color=COLOR_ENTREGA[s],
                   text=[pct(v, 0) for v in t[s]], textposition="inside",
                   hovertemplate="<b>%{y}</b><br>" + s + ": %{x:.1%}<extra></extra>")
            for s in t.columns])
        fig.update_layout(barmode="stack")
        fig.update_xaxes(tickformat=".0%", range=[0, 1])
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)", autorange="reversed")
        return self._estilo(fig, "Estado de entrega dentro de cada canal", alto=60 * len(y) + 120, leyenda=True)

    def figura_mapa_estados(self) -> go.Figure:
        """Ventas por estado de EE. UU. (color = ventas). Necesita internet para cargar el contorno del mapa."""
        t = self.A.ventas_por_estado()
        t = t[t.index.isin(ABREV_ESTADOS)]
        fig = go.Figure(go.Choropleth(
            locations=[ABREV_ESTADOS[e] for e in t.index], z=t["ventas"], locationmode="USA-states",
            colorscale=self.ESCALA, text=list(t.index), marker_line_color="white",
            customdata=np.stack([t["pedidos"], t["% ventas"]], axis=-1),
            hovertemplate="<b>%{text}</b><br>Ventas: $%{z:,.0f}<br>Pedidos: %{customdata[0]:,}"
                          "<br>%{customdata[1]:.1%} del total<extra></extra>",
            colorbar={"tickprefix": "$", "tickformat": ",.0f", "thickness": 10, "len": 0.7}))
        fig.update_layout(geo={"scope": "usa", "bgcolor": "rgba(0,0,0,0)"})
        fig = self._estilo(fig, "Ventas por estado de envío (EE. UU.)", alto=470)
        fig.update_layout(margin={"l": 0, "r": 0, "t": 45, "b": 0})
        return fig

    # ================================================================== Streamlit
    def render(self) -> None:
        """Arma la app completa. Se llama desde ``src/clases_po/app.py`` con ``streamlit run``."""
        import streamlit as st

        st.set_page_config(page_title="E-commerce · Dashboard", page_icon="🛒", layout="wide")
        st.markdown(_CSS, unsafe_allow_html=True)

        # ---------------- filtros (barra lateral)
        base = self.V_total
        with st.sidebar:
            st.header("Filtros")
            sel_can = st.multiselect("Canal", self.orden_canal, default=self.orden_canal)
            sel_cat = st.multiselect("Categoría", ORDEN_CATEGORIAS, default=ORDEN_CATEGORIAS)
            disp = [t for t in ORDEN_DISPOSITIVOS if t in set(base["device_type"].astype(str))]
            sel_dis = st.multiselect("Dispositivo", disp, default=disp)
            ests = [s for s in ORDEN_ENTREGA if s in set(base["delivery_status"])]
            sel_ent = st.multiselect("Estado de entrega", ests, default=ests)
            fmin, fmax = base["order_date"].min().date(), base["order_date"].max().date()
            sel_fec = st.date_input("Rango de fechas", (fmin, fmax), min_value=fmin, max_value=fmax,
                                    format="DD/MM/YYYY")
            st.divider()
            st.caption("Datos: millat/e-commerce-orders (Hugging Face), enriquecidos en la Semana 5. "
                       "Es un dataset sintético: sirve para practicar la analítica, no describe un negocio real.")

        d = self.filtrar(sel_can, sel_cat, sel_dis, sel_ent, sel_fec if isinstance(sel_fec, tuple) else None)

        # ---------------- encabezado y pregunta de negocio
        st.title(self.titulo)
        st.markdown(f'<div class="pregunta"><span>Pregunta de negocio</span>{self.PREGUNTA_NEGOCIO}</div>',
                    unsafe_allow_html=True)
        if d.vacio:
            st.warning("No hay ventas con esos filtros. Amplía la selección en la barra lateral.")
            return
        st.caption(f"Periodo: {d.periodo()} · {numero(len(d.V))} pedidos · {len(d.A.ventas_por_canal())} canal(es)")

        # ---------------- KPIs
        k = d.kpis()
        cols = st.columns(6)
        extra = {"delta_arrow": "off"} if _acepta_delta_arrow(st) else {}
        cols[0].metric("Ventas", dinero(k["Ventas"]), f"{pct(k['% de las ventas totales'], 0)} del total",
                       delta_color="off", **extra)
        cols[1].metric("Pedidos", numero(k["Pedidos"]))
        cols[2].metric("Ticket promedio", dinero(k["Ticket promedio"], 2))
        cols[3].metric("Clientes", numero(k["Clientes"]))
        cols[4].metric("Unidades por pedido", numero(k["Unidades por pedido"], 2))
        cols[5].metric("Días de envío", numero(k["Días de envío (prom.)"], 1))

        tabs = st.tabs(["🎯 Respuesta de negocio", "📣 Canales y segmentos", "📅 Cuándo", "🛍️ Qué",
                        "👥 A quién · clientes", "📦 Entregas y mapa", "📄 Datos"])
        cfg = {"displayModeBar": False}

        with tabs[0]:
            st.subheader("Cinco preguntas, cinco respuestas")
            for r in d.respuestas():
                with st.container(border=True):
                    st.markdown(f"**{r['id']} · {r['pregunta']}**")
                    st.markdown(_esc(r["respuesta"]))
                    c1, c2 = st.columns(2)
                    c1.markdown(f"📊 **Cómo se ve:** {_esc(r['visual'])}")
                    c2.markdown(f"✅ **Decisión:** {_esc(r['decision'])}")

        with tabs[1]:
            c1, c2 = st.columns([1.6, 1])
            c1.plotly_chart(d.figura_ventas_canal(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_ventas_segmento(), width="stretch", config=cfg)
            t = d.A.ventas_por_canal().reset_index().rename(columns={"channel": "canal"})
            st.dataframe(t, hide_index=True, width="stretch", column_config={
                "ventas": st.column_config.NumberColumn("ventas", format="dollar"),
                "% ventas": st.column_config.ProgressColumn("% ventas", format="percent", min_value=0, max_value=1),
                "precio_promedio": st.column_config.NumberColumn("precio promedio", format="dollar"),
                "ticket_promedio": st.column_config.NumberColumn("ticket promedio", format="dollar")})

        with tabs[2]:
            st.plotly_chart(d.figura_ventas_diarias(), width="stretch", config=cfg)
            c1, c2 = st.columns(2)
            c1.plotly_chart(d.figura_ventas_mensuales(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_dia_semana(), width="stretch", config=cfg)

        with tabs[3]:
            c1, c2 = st.columns(2)
            c1.plotly_chart(d.figura_categorias(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_dispositivos(), width="stretch", config=cfg)
            c1, c2 = st.columns([1, 1])
            c1.plotly_chart(d.figura_mix_categoria(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_top_productos(10), width="stretch", config=cfg)

        with tabs[4]:
            c1, c2 = st.columns(2)
            c1.plotly_chart(d.figura_segmentos(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_pareto_clientes(), width="stretch", config=cfg)
            st.markdown("**Top 10 clientes**")
            st.dataframe(d.A.top_clientes(10), hide_index=True, width="stretch", column_config={
                "ventas": st.column_config.NumberColumn(format="dollar"),
                "ticket_promedio": st.column_config.NumberColumn("ticket promedio", format="dollar")})

        with tabs[5]:
            c1, c2 = st.columns(2)
            c1.plotly_chart(d.figura_entregas(), width="stretch", config=cfg)
            c2.plotly_chart(d.figura_entregas_canal(), width="stretch", config=cfg)
            st.plotly_chart(d.figura_mapa_estados(), width="stretch")

        with tabs[6]:
            cols_ver = ["order_id", "order_date", "channel", "customer_id", "customer_segment", "category",
                        "product_id", "device_type", "quantity", "price", "order_value", "delivery_status",
                        "shipping_days", "estado"]
            cols_ver = [c for c in cols_ver if c in d.V.columns]
            st.dataframe(d.V[cols_ver], hide_index=True, width="stretch", height=420)
            st.download_button("Descargar CSV filtrado", d.V.to_csv(index=False).encode("utf-8"),
                               "ecommerce_filtrado.csv", "text/csv")


def _acepta_delta_arrow(st) -> bool:
    import inspect
    try:
        return "delta_arrow" in inspect.signature(st.metric).parameters
    except (TypeError, ValueError):
        return False


def _esc(texto: str) -> str:
    """Streamlit interpreta $...$ como fórmula LaTeX: se escapa el símbolo de pesos."""
    return texto.replace("$", r"\$")


_CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1400px;}
.pregunta {border-left: 4px solid #eb6834; background: rgba(235,104,52,.07); padding: .8rem 1rem;
           border-radius: 6px; margin: .2rem 0 1rem; font-size: 1.02rem; line-height: 1.45;}
.pregunta span {display:block; font-size:.72rem; font-weight:700; letter-spacing:.06em;
                text-transform:uppercase; color:#b4491f; margin-bottom:.2rem;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); border-radius: 8px; padding: .55rem .8rem;}
</style>
"""
