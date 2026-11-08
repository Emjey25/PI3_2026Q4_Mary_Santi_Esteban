"""Visualizaciones para pedidos de comercio electrónico."""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


class GraficosBase:
    """Gráficos generales basados en las tablas de ``AnalisisBase``."""

    COLOR = "#2a78d6"
    ACENTO = "#eb6834"

    def __init__(self, analisis, aplicar_estilo: bool = True):
        self.A = analisis
        self.dinero = mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
        if aplicar_estilo:
            plt.rcParams.update({
                "figure.figsize": (11, 4.5),
                "figure.dpi": 100,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.alpha": 0.25,
                "axes.axisbelow": True,
            })

    @staticmethod
    def _etiquetar_barras(ax, fmt="{:,.0f}", porcentaje=False):
        for barra in ax.patches:
            valor = barra.get_width() if barra.get_width() != 0 else barra.get_height()
            texto = f"{valor:.1%}" if porcentaje else fmt.format(valor)
            if barra.get_width() >= barra.get_height():
                ax.annotate(texto, (barra.get_width(), barra.get_y() + barra.get_height() / 2),
                            xytext=(4, 0), textcoords="offset points", va="center", fontsize=8)
            else:
                ax.annotate(texto, (barra.get_x() + barra.get_width() / 2, barra.get_height()),
                            xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)

    def ventas_por_dia(self):
        t = self.A.ventas_por_dia()
        fig, ax = plt.subplots()
        ax.plot(t.index, t["ventas"], color=self.COLOR)
        ax.yaxis.set_major_formatter(self.dinero)
        ax.set_title("Ventas diarias del comercio electrónico")
        ax.set_ylabel("Valor vendido ($)")
        ax.set_xlabel("Fecha del pedido")
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()

    def dia_semana(self):
        t = self.A.dia_semana_resumen()
        fig, ax = plt.subplots()
        ax.bar(t.index, t["venta promedio por día"], color=self.COLOR)
        ax.yaxis.set_major_formatter(self.dinero)
        ax.set_title("Valor vendido promedio por día de la semana")
        ax.set_ylabel("Venta promedio ($)")
        ax.set_xlabel("Día de la semana")
        plt.tight_layout()
        plt.show()

    def categorias(self):
        t = self.A.frecuencias("category").drop("Total").sort_values("ventas")
        fig, ax = plt.subplots()
        ax.barh(t.index.astype(str), t["ventas"], color=self.COLOR)
        ax.xaxis.set_major_formatter(self.dinero)
        ax.set_title("Categorías con mayor valor vendido")
        ax.set_xlabel("Valor vendido ($)")
        ax.set_ylabel("Categoría")
        self._etiquetar_barras(ax)
        plt.tight_layout()
        plt.show()

    def dispositivos(self):
        t = self.A.frecuencias("device_type").drop("Total")
        fig, ax = plt.subplots()
        ax.bar(t.index.astype(str), t["productos"], color=self.COLOR)
        ax.set_title("Unidades vendidas por dispositivo de compra")
        ax.set_ylabel("Unidades vendidas")
        ax.set_xlabel("Dispositivo")
        self._etiquetar_barras(ax, fmt="{:,.0f}")
        plt.tight_layout()
        plt.show()

    def tamanos(self):
        """Alias de compatibilidad para notebooks anteriores."""
        self.dispositivos()

    def dispositivo_y_categoria(self):
        self.categoria_dispositivo()

    def categoria_dispositivo(self):
        t = self.A.categoria_x_dispositivo("ventas").drop(index="Total", columns="ventas Total")
        t.columns = [str(c).replace("ventas ", "") for c in t.columns]
        ax = t.plot(kind="bar", figsize=(10, 4), color=[self.COLOR, self.ACENTO, "#55a868"])
        ax.set_title("Valor vendido por categoría y dispositivo")
        ax.set_ylabel("Valor vendido ($)")
        ax.set_xlabel("Categoría")
        ax.yaxis.set_major_formatter(self.dinero)
        ax.legend(title="Dispositivo")
        plt.tight_layout()
        plt.show()

    def tamano_y_categoria(self):
        """Alias de compatibilidad para notebooks anteriores."""
        self.categoria_dispositivo()

    def categoria_tamano(self):
        """Alias de compatibilidad para notebooks anteriores."""
        self.categoria_dispositivo()

    def ventas_hora(self):
        t = self.A.ventas_por_hora()
        fig, ax = plt.subplots()
        ax.bar(t.index, t["ventas"], color=self.COLOR)
        ax.yaxis.set_major_formatter(self.dinero)
        ax.set_title("Valor vendido según la hora del pedido")
        ax.set_ylabel("Valor vendido ($)")
        ax.set_xlabel("Hora del día")
        plt.tight_layout()
        plt.show()

    def top_productos(self, n: int = 10):
        t = self.A.ranking_productos().head(n).iloc[::-1]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(t.index.astype(str), t["ventas"], color=self.COLOR)
        ax.xaxis.set_major_formatter(self.dinero)
        ax.set_title(f"Top {n} productos por valor vendido")
        ax.set_xlabel("Valor vendido ($)")
        ax.set_ylabel("Identificador del producto")
        self._etiquetar_barras(ax)
        plt.tight_layout()
        plt.show()

    def histogramas(self):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].hist(self.A.V["price"], bins=20, color=self.COLOR)
        axes[0].set_title("Distribución del precio unitario")
        axes[0].set_xlabel("Precio unitario ($)")
        axes[0].set_ylabel("Cantidad de líneas")
        axes[1].hist(self.A.pedidos["valor_pedido"], bins=20, color=self.ACENTO)
        axes[1].xaxis.set_major_formatter(self.dinero)
        axes[1].set_title("Distribución del valor total del pedido")
        axes[1].set_xlabel("Valor del pedido ($)")
        axes[1].set_ylabel("Cantidad de pedidos")
        plt.tight_layout()
        plt.show()

    def dashboard(self, canal="Todos", categoria="Todas", dispositivo="Todos",
                  titulo="Dashboard de e-commerce"):
        d = self.A.filtrar(canal, categoria, dispositivo)
        if d.empty:
            print("No hay pedidos con esos filtros.")
            return
        kpis = self.A.kpis(canal, categoria, dispositivo)
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        fig.suptitle(f"{titulo} · {self.A.periodo()}", fontweight="bold")
        d.groupby("order_date")["order_value"].sum().plot(ax=axes[0, 0], color=self.COLOR)
        d.groupby("hora")["order_value"].sum().plot.bar(ax=axes[0, 1], color=self.COLOR)
        d.groupby("product_id")["order_value"].sum().nlargest(5).sort_values().plot.barh(
            ax=axes[1, 0], color=self.ACENTO
        )
        d.groupby("category", observed=True)["order_value"].sum().plot.bar(
            ax=axes[1, 1], color=self.COLOR
        )
        axes[0, 0].set_title("Ventas por fecha")
        axes[0, 1].set_title("Ventas por hora")
        axes[1, 0].set_title("Top 5 productos por valor")
        axes[1, 1].set_title("Ventas por categoría")
        axes[0, 0].set_ylabel("Valor vendido ($)")
        axes[0, 1].set_ylabel("Valor vendido ($)")
        axes[1, 0].set_xlabel("Valor vendido ($)")
        axes[1, 1].set_ylabel("Valor vendido ($)")
        for ax in axes.flat:
            ax.yaxis.set_major_formatter(self.dinero)
        plt.tight_layout()
        plt.show()
        return kpis


class GraficosEcommerce(GraficosBase):
    """Gráficos específicos de clientes, canales y entregas."""

    def canales(self):
        t = self.A.ventas_por_canal().sort_values("ventas")
        fig, ax = plt.subplots()
        ax.barh(t.index.astype(str), t["ventas"], color=self.COLOR)
        ax.xaxis.set_major_formatter(self.dinero)
        ax.set_title("Valor vendido por canal de adquisición")
        ax.set_xlabel("Valor vendido ($)")
        ax.set_ylabel("Canal")
        self._etiquetar_barras(ax)
        plt.tight_layout()
        plt.show()

    def segmentos(self):
        t = self.A.ventas_por_segmento().sort_values("ventas")
        fig, ax = plt.subplots()
        ax.barh(t.index.astype(str), t["ventas"], color=self.COLOR)
        ax.xaxis.set_major_formatter(self.dinero)
        ax.set_title("Valor vendido por segmento de cliente")
        ax.set_xlabel("Valor vendido ($)")
        ax.set_ylabel("Segmento")
        self._etiquetar_barras(ax)
        plt.tight_layout()
        plt.show()

    def entregas(self):
        t = self.A.estado_entregas().sort_values("pedidos")
        fig, ax = plt.subplots()
        ax.bar(t.index.astype(str), t["pedidos"], color=self.ACENTO)
        ax.set_title("Pedidos según estado de entrega")
        ax.set_ylabel("Cantidad de pedidos")
        ax.set_xlabel("Estado de entrega")
        self._etiquetar_barras(ax, fmt="{:,.0f}")
        plt.tight_layout()
        plt.show()
