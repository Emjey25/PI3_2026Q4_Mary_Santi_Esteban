# PI3 - Análisis de pedidos de e-commerce

Proyecto en Python para cargar y describir pedidos de comercio electrónico. El
flujo obtiene los datos desde Hugging Face, los convierte en un
`pandas.DataFrame`, verifica su calidad y genera un reporte reproducible.

## Necesidad y diseño inicial

**Necesidad:** contar con una descripción confiable de los pedidos para
identificar qué información está disponible sobre productos, clientes, pagos,
canales y entregas antes de realizar análisis comerciales.

**Pregunta:** ¿qué características tienen los pedidos del dataset y qué
variables permiten estudiar el comportamiento de compra y la operación de
entrega?

**Objetivo:** cargar el dataset, describir su estructura y calidad, y dejar
disponible un resumen automático para futuros análisis.

**Alcance:** esta primera entrega cubre obtención, exploración básica,
validación de duplicados y valores nulos, exportación a CSV y generación del
reporte `.txt`. No incluye modelos predictivos ni conclusiones causales.

## ¿Qué hace este proyecto?

- Descarga un dataset desde Hugging Face con `HFDatasetLoader`.
- Convierte los registros a un `DataFrame` de pandas.
- Permite guardar los datos en CSV, JSON, Parquet o Excel.
- Genera un resumen con filas, columnas, duplicados, tipos, nulos y estadísticas numéricas.
- Puede ejecutarse automáticamente con GitHub Actions.

## Dataset actual

El proyecto usa el dataset
[`millat/e-commerce-orders`](https://huggingface.co/datasets/millat/e-commerce-orders),
en la partición `train`. La ficha del dataset contiene su descripción, autoría,
licencia y condiciones de uso; debe consultarse antes de reutilizar los datos
fuera de este proyecto.

Resumen del dataset cargado:

- 10.000 filas
- 15 columnas
- 0 registros duplicados
- 0 valores nulos
- Precio promedio: 252.55
- Cantidad promedio por pedido: 2.12

Archivo principal de datos:

- `src/sincronicas/datos/e-commerce-orders.csv`
- `src/sincronicas/reportes/E-commerce Orders & Customer Behavior.txt`

### Columnas principales

`order_id`, `customer_id`, `product_id`, `category`, `price`, `quantity`, `order_date`, `shipping_date`, `delivery_status`, `payment_method`, `device_type`, `channel`, `shipping_address`, `billing_address`, `customer_segment`.

Cada fila representa un pedido. Las variables de categoría, precio y cantidad
permiten describir la compra; las fechas y el estado permiten revisar la
entrega; y el método de pago, dispositivo, canal y segmento permiten explorar
el comportamiento del cliente.

## Estructura del repositorio

```text
.
├── .github/
│   └── workflows/
│       └── ejecutar-semana-1.yml
├── requirements.txt
├── src/
│   ├── clases_po/
│   │   ├── __init__.py
│   │   ├── hf_loader.py
│   │   └── reportes.py
│   └── sincronicas/
│       ├── Semana_1SINC.ipynb
│       ├── datos/
│       └── reportes/
└── README.md
```

## Uso rápido

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Luego se puede ejecutar el notebook desde la carpeta `src/sincronicas`.

```bash
cd src/sincronicas
jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  --ExecutePreprocessor.timeout=1800 \
  Semana_1SINC.ipynb
```

La ejecución actualiza el CSV y el reporte publicado en
`src/sincronicas/reportes/E-commerce Orders & Customer Behavior.txt`.

## Requisitos

- Python 3.12
- `pip`
- Conexión a internet para descargar el dataset inicial

## Descripción corta del proyecto

Este repositorio muestra un flujo básico de análisis de datos para e-commerce: descarga del dataset, transformación a formato tabular, validación de calidad y generación de reportes. Está pensado como base para explorar ventas, comportamiento del cliente, canales de adquisición y métricas de pedidos.
