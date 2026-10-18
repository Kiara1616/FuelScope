---
title: "Del dato al indicador: diseño y evaluación de un dashboard de ventas con Streamlit"
description: "Un caso reproducible sobre indicadores, decisiones de visualización, automatización y límites de un dashboard publicado en la nube."
tags: python, streamlit, dataviz, github
cover_image: https://raw.githubusercontent.com/Kiara1616/insightflow-sales-dashboard/main/docs/assets/banner-articulo.png
---

¿Qué debe mostrar un dashboard para que una persona pueda pasar de «¿cuánto vendimos?» a «¿dónde conviene investigar?»? Esa pregunta orientó la construcción de un panel de análisis comercial con Python. Partí de un archivo de ventas, definí indicadores, construí vistas interactivas, añadí pruebas y publiqué la aplicación en la nube. Comparto aquí tanto las decisiones de diseño como los límites de lo que el resultado permite afirmar.

> **Explora el proyecto:** [aplicación interactiva](https://insightflow-sales-dashboard-he3kljwft48fj5lkjgtyu.streamlit.app) · [repositorio público y código fuente](https://github.com/Kiara1616/insightflow-sales-dashboard) · [pruebas automatizadas](https://github.com/Kiara1616/insightflow-sales-dashboard/actions)

**Resumen.** Se desarrolló un dashboard descriptivo a partir de 18 registros sintéticos de ventas. El proceso comprende validación básica del esquema, transformación temporal, cálculo de indicadores sobre datos filtrados, visualización interactiva, pruebas automatizadas y publicación desde un repositorio abierto. El caso muestra una ruta reproducible para construir un panel; no constituye una evaluación de desempeño comercial real.

**Palabras clave:** visualización de datos, dashboards, indicadores, Streamlit, reproducibilidad.

## 1. Del problema a las preguntas de análisis

El punto de partida fue una necesidad frecuente: una tabla de operaciones permite buscar registros individuales, pero dificulta comparar períodos, regiones y líneas de producto de manera inmediata. El panel se diseñó para responder cuatro preguntas:

1. ¿Cuál es el volumen de ventas y de unidades en el período seleccionado?
2. ¿Cómo cambian las ventas de un mes a otro?
3. ¿Qué regiones y categorías concentran la facturación?
4. ¿Qué producto registra la mayor venta acumulada bajo los filtros actuales?

La elección de los gráficos vino después de estas preguntas. Esta secuencia se inspira en el [modelo de diseño y validación de visualizaciones de Munzner](https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/): primero se caracteriza el problema y los datos, luego se definen tareas y representaciones. No afirmo haber validado formalmente cada nivel de ese modelo; lo uso como marco para justificar por qué las vistas responden a tareas concretas.

El alcance es **descriptivo y exploratorio**. El panel ayuda a localizar diferencias en el conjunto de datos, pero no predice demanda, demuestra causalidad ni recomienda una acción empresarial por sí mismo. Una observación visual plantea una pregunta; responderla exige más contexto.

## 2. Unidad de análisis, preparación y calidad de los datos

El archivo [`data/ventas.csv`](https://github.com/Kiara1616/insightflow-sales-dashboard/blob/main/data/ventas.csv) contiene **18 registros sintéticos** fechados entre enero y junio de 2025. Cada fila representa un registro de ventas de un producto en una fecha y región; no equivale necesariamente a una factura o pedido individual. Las variables son `fecha`, `region`, `categoria`, `producto`, `ventas` y `unidades`. El sol peruano (`S/`) es la unidad monetaria usada para mostrar los importes del ejemplo.

Esta granularidad importa: si una fila no es un pedido, dividir ingresos entre el número de filas no da un «ticket promedio». Tampoco hay identificadores de clientes, costos ni márgenes. Definir la unidad de análisis antes de crear indicadores evita que una cifra técnicamente correcta responda a la pregunta equivocada.

Antes de visualizar, la aplicación convierte `fecha` a tipo fecha, comprueba que estén presentes las columnas requeridas y deriva un campo `mes`. Estas operaciones están implementadas en [`app.py`](https://github.com/Kiara1616/insightflow-sales-dashboard/blob/main/app.py). Las pruebas verifican, además, que el archivo no esté vacío y que ventas y unidades sean positivas.

La revisión de calidad es **básica**: el proyecto todavía no comprueba duplicados, fechas fuera de rango, monedas mezcladas ni coherencia entre producto y categoría. Tampoco implementa un proceso de carga desde una fuente transaccional. Conviene distinguir estas ausencias de lo que sí está probado.

## 3. Indicadores y reglas de cálculo

Sea **F** el conjunto de registros que queda después de aplicar los filtros de región, categoría y período. Todos los indicadores y gráficos se calculan sobre **F**, no sobre el archivo completo:

| Indicador | Definición | Unidad |
| --- | --- | --- |
| Ventas totales | Suma de `ventas` para cada registro de **F**. | Soles (S/). |
| Unidades vendidas | Suma de `unidades` para cada registro de **F**. | Unidades. |
| Venta promedio por unidad | Ventas totales ÷ unidades vendidas, cuando el denominador es mayor que cero. | S/ por unidad. |
| Producto líder | Producto cuya suma de `ventas` en **F** es máxima. | Nombre de producto. |

La venta promedio por unidad **no es el ticket promedio por transacción**: el conjunto de datos no incluye un identificador de pedido. Precisar esta diferencia evita interpretar un indicador con una unidad de análisis equivocada. Si los filtros no devuelven registros, el panel comunica que no hay datos y no muestra métricas vacías como si fueran resultados.

## 4. Del indicador a la representación visual

La interfaz se construyó con [Streamlit](https://docs.streamlit.io/) y el tratamiento de datos con Pandas. Los filtros están en una barra lateral y las métricas principales se sitúan antes de los gráficos. El recorrido de lectura propuesto va de la síntesis al detalle: indicadores, evolución temporal, comparación regional y registros originales.

La evolución temporal se representa con una línea de ventas mensuales; la comparación territorial, con barras por región. Ambas figuras se generan con [Plotly Express](https://plotly.com/python/plotly-express/). La tabla por categoría y la vista desplegable de registros conservan el detalle necesario para revisar las agregaciones.

| Pregunta | Vista | Motivo de elección |
| --- | --- | --- |
| ¿Cuál es la magnitud actual? | Tarjetas de indicadores | Lectura inmediata del subconjunto seleccionado. |
| ¿Cómo varía a lo largo del tiempo? | Línea mensual | El orden temporal hace visible la secuencia de valores. |
| ¿Cómo se comparan regiones? | Barras | Las longitudes facilitan la comparación de categorías discretas. |
| ¿Qué registros explican una cifra? | Tabla filtrada | Permite inspeccionar los datos detrás del resumen. |

Este diseño no ha pasado por una evaluación formal con usuarios. La literatura sobre [dashboards cooperativos](https://vis.mit.edu/pubs/cooperative-dashboards/) destaca la relación entre tareas, interacción y comunicación analítica; aquí la tomé como orientación de diseño, no como evidencia de que esta interfaz ya mejore decisiones reales.

Una decisión de implementación importante fue calcular todas las vistas a partir del mismo subconjunto filtrado. Por ejemplo:

```python
filtered = data[
    data["region"].isin(regions)
    & data["categoria"].isin(categories)
    & data["fecha"].dt.date.between(start_date, end_date)
].copy()

total_sales = filtered["ventas"].sum()
total_units = filtered["unidades"].sum()
```

Así, el valor de las tarjetas, las series y las tablas responde a la misma selección del usuario. Para el gráfico mensual se agrupan los registros por `mes`; para las barras, por `region`. La tabla final permite volver de la agregación a las filas que la originaron. El diseño también se revisó en temas claro y oscuro para conservar el contraste de las cifras.

La interacción tiene un límite deliberado: filtrar no modifica el archivo fuente ni crea nuevas observaciones. Si se desmarcan todas las categorías o regiones, el panel muestra un estado sin resultados. Esa respuesta es preferible a representar ceros que podrían confundirse con ventas observadas de valor cero.

## 5. Resultados reproducibles y lectura responsable

Con todos los filtros incluidos, los cálculos sobre el archivo de ejemplo producen **S/ 331,800** en ventas, **605 unidades** y **S/ 548.43 por unidad**. La mayor suma por producto corresponde a **Laptop** (S/ 73,500). Estos valores se obtienen directamente del CSV; no proceden de estimaciones estadísticas.

En la agregación mensual, mayo registra **S/ 64,700** y junio **S/ 39,900**. Entre las regiones, Lima suma **S/ 138,900**, Norte **S/ 100,600** y Sur **S/ 92,300**. Estos números demuestran que las vistas cambian de escala y permiten formular preguntas de seguimiento. **No demuestran** crecimiento, estacionalidad o superioridad comercial de una región: el conjunto es sintético, pequeño y no está acompañado por información sobre cobertura, objetivos o exposición al mercado.

Quien quiera comprobarlos puede descargar [`ventas.csv`](https://github.com/Kiara1616/insightflow-sales-dashboard/blob/main/data/ventas.csv), ejecutar la aplicación o inspeccionar las operaciones de agrupación en [`app.py`](https://github.com/Kiara1616/insightflow-sales-dashboard/blob/main/app.py). La posibilidad de replicar una cifra es una propiedad más sólida que una captura aislada del panel.

## 6. Reproducibilidad, pruebas y publicación automatizada

El [repositorio de InsightFlow Sales Dashboard](https://github.com/Kiara1616/insightflow-sales-dashboard) reúne el código de la aplicación, los datos de ejemplo, las dependencias, las pruebas y la configuración de integración continua. Se puede ejecutar localmente con:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Las pruebas comprueban que el archivo de datos exista, que tenga las columnas previstas, que la fecha se procese correctamente y que ventas y unidades sean positivas. El [workflow de GitHub Actions](https://github.com/Kiara1616/insightflow-sales-dashboard/blob/main/.github/workflows/tests.yml) instala las dependencias y ejecuta `python -m pytest -q` en cada `push` y `pull request`. Puede consultarse [una ejecución satisfactoria](https://github.com/Kiara1616/insightflow-sales-dashboard/actions/runs/36220497285). Estas pruebas no verifican que las cifras mostradas en la interfaz coincidan con valores esperados para cada combinación de filtros; ese sería un paso posterior.

El despliegue sigue otro mecanismo: [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) toma el proyecto desde la rama `main` y publica la aplicación. La plataforma detecta cambios en el repositorio y actualiza la aplicación. Por tanto, GitHub Actions automatiza la **verificación**, mientras Streamlit Community Cloud automatiza la **actualización del despliegue**. Son procesos relacionados, pero cumplen funciones diferentes.

Hay una limitación operativa importante: **la publicación no está condicionada a que las pruebas terminen satisfactoriamente**. Un cambio en `main` puede llegar a la aplicación aunque el workflow falle. Para un sistema de producción convendría proteger la rama, exigir revisión y usar el resultado de las pruebas como requisito antes de incorporar cambios. La automatización actual cumple una función de detección y trazabilidad, no de bloqueo preventivo del despliegue.

## 7. Evaluación del alcance y amenazas a la validez

El resultado es un [dashboard público](https://insightflow-sales-dashboard-he3kljwft48fj5lkjgtyu.streamlit.app) que permite explorar los mismos datos desde distintas selecciones sin modificar el código. El repositorio abierto facilita revisar los cálculos y repetir la ejecución. La automatización hace visibles los fallos de las comprobaciones básicas de los datos.

El caso tiene límites claros. El conjunto de datos es pequeño y sintético; no hay información sobre costos, márgenes, clientes ni pedidos. Por ello, el panel sirve como demostración metodológica y no como diagnóstico de un negocio. Además, las pruebas actuales validan el esquema y valores básicos, pero no cubren todas las interacciones de la interfaz ni sustituyen una revisión visual posterior al despliegue.

Distingo tres niveles que suelen confundirse: **exactitud de cálculo** (que el código agregue según la definición), **validez del indicador** (que la definición responda a la pregunta) y **utilidad para la decisión** (que una persona pueda actuar mejor con la información). Este proyecto aporta evidencia directa sobre parte del primer nivel y documenta las decisiones del segundo. No mide el tercero. Un estudio posterior podría plantear tareas concretas a usuarios, registrar errores y tiempos de respuesta, y recoger la interpretación que hacen de los gráficos.

## Conclusión

Construir un dashboard requiere algo más que elegir gráficos. La utilidad del resultado depende de definir bien los indicadores, mantener coherencia entre filtros y visualizaciones, documentar el origen de los datos y asegurar que el proceso de publicación sea repetible. Este proyecto presenta una implementación pequeña y verificable de ese flujo. Un paso siguiente sería incorporar un conjunto de datos real, ampliar las pruebas y evaluar el panel con usuarios que realicen tareas de análisis concretas.

Si trabajas con dashboards similares, me interesa conocer cómo compruebas que un indicador conserva su significado cuando cambian los filtros y cómo haces visible la calidad de los datos a quienes usan el panel.

## Referencias y documentación

- Munzner, T. (2009). [*A Nested Model for Visualization Design and Validation*](https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/). *IEEE Transactions on Visualization and Computer Graphics, 15*(6), 921–928.
- Setlur, V., Correll, M., Satyanarayan, A. y Tory, M. (2024). [*Heuristics for Supporting Cooperative Dashboard Design*](https://vis.mit.edu/pubs/cooperative-dashboards/). *IEEE Transactions on Visualization and Computer Graphics*.
- [Documentación de Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) y [documentación de eventos de GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), consultadas para describir los mecanismos de publicación y ejecución automática.

**Recursos del proyecto:** [código y documentación](https://github.com/Kiara1616/insightflow-sales-dashboard) · [aplicación en la nube](https://insightflow-sales-dashboard-he3kljwft48fj5lkjgtyu.streamlit.app) · [historial de automatización](https://github.com/Kiara1616/insightflow-sales-dashboard/actions).
