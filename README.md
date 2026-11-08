# Proyecto Integrado 2026Q4 - Análisis de pedidos de e-commerce

Este repositorio contiene un proyecto de análisis de datos para comercio electrónico basado en un dataset de pedidos reales en formato tabular. El objetivo es preparar los datos, enriquecerlos con métricas de negocio, analizar tendencias de compra y entrega, y dejar una base reutilizable para dashboards, modelos predictivos y automatización.

## Objetivo del proyecto

- Cargar y validar un dataset de e-commerce desde Hugging Face.
- Preprocesar columnas, fechas y métricas de negocio.
- Realizar análisis descriptivo por categoría, canal, cliente, producto y entrega.
- Generar visualizaciones y reportes automáticos.
- Probar flujos de modelado con regresión lineal y clasificación de texto.
- Integrar un cliente con LLM de NVIDIA para apoyo analítico.

## Estado actual del repositorio

El proyecto ya incluye:

- carga del dataset desde Hugging Face con `datasets`
- validación y preprocesamiento con pandas
- análisis estadístico y segmentado por canal/segmento
- enriquecimiento con columnas derivadas (valor del pedido, días de envío, recurrencia, shares, etc.)
- generación de reportes y gráficos
- modelos de regresión lineal y clasificación de texto con scikit-learn
- cliente con API NVIDIA para consultas JSON o texto
- notebooks de trabajo y automación con GitHub Actions

## Dataset principal

El proyecto trabaja con el dataset de Hugging Face:

- `millat/e-commerce-orders`
- partición: `train`

El dataset se guarda y se usa en varias ubicaciones del repositorio:

- `datos/e-commerce-orders.csv`
- `src/sincronicas/datos/e-commerce-orders.csv`
- `reportes/E-commerce Orders & Customer Behavior.txt`
- `src/sincronicas/reportes/E-commerce Orders & Customer Behavior.txt`

Resumen del dataset cargado:

- 10.000 filas
- 15 columnas originales
- 0 duplicados
- 0 valores nulos
- precio medio: 252.55
- cantidad promedio por pedido: 2.12

Columnas principales:

- `order_id`
- `customer_id`
- `product_id`
- `category`
- `price`
- `quantity`
- `order_date`
- `shipping_date`
- `delivery_status`
- `payment_method`
- `device_type`
- `channel`
- `shipping_address`
- `billing_address`
- `customer_segment`

## Estructura actual del repositorio

```text
PI3_2026Q4_Mary_Santi_Esteban/
├── .github/
│   └── workflows/
│       └── ejecutar-semana-1.yml
├── Entregas_Documentos/
│   └── Actividad 2 Proyecto integrado Update.pdf
├── datos/
│   └── e-commerce-orders.csv
├── reportes/
│   └── E-commerce Orders & Customer Behavior.txt
├── src/
│   ├── clases_po/
│   │   ├── __init__.py
│   │   ├── analisis.py
│   │   ├── clasificador_text.py
│   │   ├── enriquecimiento.py
│   │   ├── graficos.py
│   │   ├── hf_loader.py
│   │   ├── llm_nvidia.py
│   │   ├── preprocesamiento.py
│   │   ├── regresion_lineal.py
│   │   └── reportes.py
│   └── sincronicas/
│       ├── Semana_1SINC.ipynb
│       ├── Semana_4SINC.ipynb
│       ├── datos/
│       │   ├── e-commerce-orders.csv
│       │   └── resultados_punto_4/
│       │       ├── dataset_ecommerce_preparado.csv
│       │       ├── pregunta_1_categorias.csv
│       │       ├── pregunta_2_productos.csv
│       │       ├── pregunta_3_canales_segmentos.csv
│       │       ├── pregunta_4_entregas.csv
│       │       └── resumen_dataset_ecommerce.txt
│       └── reportes/
│           └── E-commerce Orders & Customer Behavior.txt
├── .gitignore
├── README.md
├── requirements.txt
└── .venv/ (si se crea localmente)
```

## Módulos principales del código

### 1) `src/clases_po/hf_loader.py`

`HFDatasetLoader`

- Carga datasets desde Hugging Face.
- Convierte la salida a `pandas.DataFrame`.
- Soporta limitar filas (`max_rows`).
- Permite guardar el resultado en CSV, JSON, Parquet o Excel.

### 2) `src/clases_po/preprocesamiento.py`

`PreprocesadorEcommerce`

- Diagnostica tipos de columna.
- Convierte `quantity`, `price`, fechas y columnas categóricas.
- Genera columnas calculadas como:
  - `order_value`
  - `shipping_days`
  - `total_calculado`
  - `verificacion`
  - `dia_semana`
  - `hora`
  - `nuevo_pedido`
- Valida integridad del dataset y compara métricas esperadas.

### 3) `src/clases_po/enriquecimiento.py`

`EnriquecedorEcommerce`

- Añade métricas de negocio y comportamiento del cliente.
- Crea indicadores como:
  - `customer_order_count`
  - `customer_recurrente`
  - `channel_sales_share`
  - `segment_sales_share`
  - `delivery_delay`
- Genera resúmenes por:
  - cliente
  - canal
  - entregas

### 4) `src/clases_po/analisis.py`

`AnalisisBase` y `AnalisisEcommerce`

- Realiza análisis descriptivo sobre pedidos y ventas.
- Calcula fórmulas equivalentes a un flujo tipo Excel.
- Genera tablas de totales, frecuencia, ventas por día, categoría, canal, segmento, etc.
- Permite filtrar por canal, categoría, dispositivo y día de la semana.
- Define KPI y resúmenes de negocio para dashboards.

### 5) `src/clases_po/graficos.py`

`GraficosBase` y `GraficosEcommerce`

- Muestra visualizaciones como:
  - ventas por día
  - ventas por hora
  - ventas por categoría
  - ventas por canal
  - ventas por segmento
  - estados de entrega
  - top productos
  - dashboard global

### 6) `src/clases_po/reportes.py`

`Reportes`

- Genera un resumen textual de cualquier DataFrame.
- Incluye:
  - número de filas y columnas
  - duplicados
  - tipos de columnas
  - valores nulos
  - estadísticas descriptivas numéricas
- Puede exportarse directamente a `.txt`.

### 7) `src/clases_po/clasificador_text.py`

`ClasificadorTexto`

- Implementa un flujo reutilizable de clasificación de texto con scikit-learn.
- Usa `TfidfVectorizer` + `MultinomialNB` por defecto.
- Permite:
  - cargar datos desde DataFrame, CSV o dataset de Hugging Face
  - validar columnas de texto y etiquetas
  - dividir entrenamiento/prueba con estratificación
  - entrenar, evaluar y guardar el modelo
  - ejecutar el flujo completo de forma reproducible

### 8) `src/clases_po/regresion_lineal.py`

`RegresionLineal`

- Encapsula un flujo de regresión lineal.
- Valida entradas numéricas y gestiona limpieza de datos.
- Divide los datos en train/test.
- Entrena `LinearRegression` y calcula métricas como:
  - MAE
  - MSE
  - RMSE
  - R²
- Guarda el modelo entrenado y permite reentrenamiento.

### 9) `src/clases_po/llm_nvidia.py`

`LLMNvidia`

- Cliente para la API de NVIDIA compatible con OpenAI.
- Soporta streaming y extracción de JSON.
- Permite:
  - caché local en disco
  - reintentos automáticos
  - uso de prompt por texto o JSON
  - fallback cuando la API no está disponible

## Notebooks y entregas

El proyecto incluye dos notebooks principales:

- `src/sincronicas/Semana_1SINC.ipynb`
- `src/sincronicas/Semana_4SINC.ipynb`

Estos notebooks trabajan sobre el dataset de pedidos para:

- explorar la estructura del dataset
- preparar y limpiar los datos
- responder preguntas de negocio
- generar resultados intermedios en CSV
- publicar reportes resumen en `src/sincronicas/datos/resultados_punto_4/`

Dentro de esa carpeta ya aparecen resultados como:

- `dataset_ecommerce_preparado.csv`
- `pregunta_1_categorias.csv`
- `pregunta_2_productos.csv`
- `pregunta_3_canales_segmentos.csv`
- `pregunta_4_entregas.csv`
- `resumen_dataset_ecommerce.txt`

## Flujo de trabajo del proyecto

1. Cargar datos desde Hugging Face o desde CSV local.
2. Diagnosticar tipos y columnas.
3. Preprocesar fechas, categorías y métricas.
4. Enriquecer el dataset con indicadores derivados.
5. Analizar KPIs por producto, canal, cliente y entrega.
6. Generar gráficos y reportes.
7. Entrenar modelos de clasificación y regresión cuando sea necesario.
8. Exportar resultados para documentación o análisis posterior.

## Requisitos

- Python 3.12
- pip
- internet para acceder al dataset inicial desde Hugging Face
- dependencias listadas en `requirements.txt`

## Instalación rápida

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si quieres exportar formatos adicionales como Parquet o Excel, también puede instalarse soporte adicional:

```bash
python -m pip install pyarrow openpyxl
```

## Ejecutar el notebook

Desde la carpeta del proyecto:

```bash
cd src/sincronicas
jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  --ExecutePreprocessor.timeout=1800 \
  Semana_4SINC.ipynb
```

Esto re-ejecuta el análisis y actualiza los archivos generados en:

- `src/sincronicas/datos/`
- `src/sincronicas/reportes/`

## Automatización

El repositorio incluye una GitHub Action en:

- `.github/workflows/ejecutar-semana-1.yml`

La acción:

- configura Python 3.12
- instala dependencias
- ejecuta el notebook `Semana_4SINC.ipynb`
- confirma y publica los datos y reportes generados

## Tecnologías principales

- Python 3.12
- pandas
- numpy
- matplotlib
- scikit-learn
- datasets
- Jupyter Notebook
- Hugging Face Datasets

## Resumen corto

Este proyecto es una base sólida para análisis de e-commerce con enfoque de negocio, automatización y experimentación. Combina preparación de datos, feature engineering, análisis descriptivo, visualización, modelado y soporte con IA generativa, todo dentro de un mismo repositorio reproducible.
