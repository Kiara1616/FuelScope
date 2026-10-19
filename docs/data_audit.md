# Auditoría del conjunto de precios

Los tres archivos fueron descargados por la propietaria desde el [conjunto público de OSINERGMIN](https://www.datosabiertos.gob.pe/dataset/lista-de-precios-de-combustibles-diaria-reconstruida-partir-de-los-precios-actualizados) y entregados al proyecto el 18 de octubre de 2026. Una descarga directa posterior de las tres URLs oficiales coincidió byte por byte con ellos. El portal no ofrece en la página consultada un checksum propio. La estructura del CSV se contrastó con el diccionario y los metadatos recibidos; los hashes siguientes identifican exactamente la **primera versión** incorporada. El estado de la versión actualmente incluida se registra en [`data/source_status.json`](../data/source_status.json).

| Archivo original | SHA-256 |
| --- | --- |
| `precios_combustibles_anonimizados_20260301_part1.csv` | `a733b48f6ff24d1e0837b622c1ec472cc2bb2924dcb2a90b145a77e1d4262eaa` |
| `Diccionario de datos_Precios_Combustible.xlsx` | `dbfb913f27707595959207c1691c1e7f83c0b5de0720c18461b6ade7e07e55a2` |
| `Metadatos Lista de precios_Combustible_6_0.docx` | `f55e77766b5e88197c52528bb57a68fa2dc3f9543aa45c17fa93288bb2739303` |

El CSV original está en `data/raw` comprimido con gzip sin modificar sus bytes descomprimidos; su hash descomprimido coincide con el de la tabla. El diccionario y los metadatos también se conservan allí. El CSV pesa 29 635 336 bytes, usa UTF-8 y coma como delimitador.

## Esquema y significado

El archivo contiene **497 156 filas y 11 columnas**: `fecha_emision`, `fecha_corte`, `id`, `fe_eval`, `g_premium`, `g_regular`, `diesel`, `gnv`, `glp_g`, `glp_e` y `ANON_CO_LOCAL_VENTA`. El diccionario define `FE_EVAL` como fecha de vigencia del precio y `FECHA_CORTE` como fecha de generación; ambos usan `aaaammdd`. El campo de local aparece como `ANON_LOCAL_VENTA` en el diccionario y como `ANON_CO_LOCAL_VENTA` en el CSV recibido; se usa el nombre real y se registra la discrepancia. `fecha_emision` e `id` no tienen definición en el diccionario proporcionado.

Las fechas `fe_eval` cubren **59 días, del 1 de enero al 28 de febrero de 2026**. `fecha_emision` y `fecha_corte` valen `20260301` en todas las filas. El DOCX indica frecuencia de actualización mensual, última actualización `2026-03-11` y cobertura `Perú, 03-2026`; esta cobertura del recurso no equivale a la última fecha observada. Hay 8 825 identificadores de local distintos en el CSV y 8 613 entre observaciones con al menos un precio válido. `id` es único y no se detectaron filas completas duplicadas.

**El CSV no contiene departamento, provincia, distrito ni coordenadas.** FuelScope no muestra rankings territoriales con este snapshot. El diccionario describe los seis combustibles, pero no documenta la unidad física de sus precios. Por ello la interfaz dice «unidad no documentada» y compara cada combustible por separado. No se asignaron unidades por inferencia ni se convirtieron precios.

## Reglas y resultado del procesamiento

Cada una de las seis columnas de combustible produce una posible observación. Las celdas `nan` o vacías se excluyen; también se excluirían fechas inválidas y precios no finitos, cero o negativos. No se detectaron precios cero o negativos. No se aplicó un techo arbitrario: hay valores extremos como 2 000 y 2 500 en gasolina regular y diésel que requieren revisión de origen. El indicador principal es la mediana, resistente a esos extremos, y nunca se presenta como precio vigente.

| Combustible | Precios válidos | Mediana reportada | Máximo reportado |
| --- | ---: | ---: | ---: |
| Gasolina/gasohol premium | 221 512 | 15,09 | 24,99 |
| Gasolina/gasohol regular | 256 680 | 13,99 | 2 000,00 |
| Diésel DB5-S | 277 094 | 14,50 | 2 500,00 |
| GNV | 17 788 | 1,78 | 14,29 |
| GLP a granel | 98 799 | 5,815 | 14,29 |
| GLP envasado, balón de 10 kg | 190 026 | 48,00 | 300,00 |

De **2 982 936 posibles precios** (497 156 filas × seis combustibles), **1 061 899** son válidos y **1 921 037** se excluyen por ausencia de precio. La unidad de estas cifras es la unidad reportada por el archivo, aún no definida en el diccionario. No se suman ni comparan medianas de distintos combustibles.

El contrato reproducible está en `data/source_contract.json` y el snapshot publicado en `data/processed`. Su manifiesto guarda SHA-256 del CSV original, Parquet e informe de calidad, además de recuentos y fechas. La tarea semanal consulta la URL directa conocida y aborta si cambian los documentos de referencia, el esquema o los controles de volumen y fecha. Su ejecución en GitHub Actions todavía debe comprobarse. No hay garantía de frescura.
