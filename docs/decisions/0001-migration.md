# ADR 0001: migración de InsightFlow a FuelScope

El nombre solicitado para el producto es **FuelScope**. La especificación adjunta proponía RutaCombustible, pero la instrucción directa del propietario establece el nombre vigente. El mismo repositorio se renombró a `Kiara1616/FuelScope`, con historial conservado y etiqueta `v1-insightflow-sales` para la versión anterior. La migración se desarrolla en `feature/fuelscope-migration` desde `main`.

La aplicación objetivo será un monolito modular de Streamlit con procesamiento separado y datos oficiales versionados. La fuente oficial bloquea la descarga en el entorno actual, de modo que la construcción de métricas y la publicación quedan sujetas a obtener y auditar el CSV y diccionario originales. No se presentarán cifras sintéticas como precios reales.

Base inspeccionada: commit `4d145a3` en `main`, 15 commits visibles en GitHub; aplicación `app.py`, `data/ventas.csv`, una prueba de datos y un workflow de tests. El artículo histórico de ventas se conserva en Git y no se reescribe para atribuirle el producto nuevo.
