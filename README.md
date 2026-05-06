# Noumenon

Reconstrucción en curso hacia una **Noumenon V2** simple, manual-asistida, robusta y orientada a lectura estructural de poder para decisión ejecutiva.

## Estado actual

La vía principal del producto es ahora:

```bash
streamlit run app_v2.py
```

La V2 vive en [`noumenon_v2/`](./noumenon_v2) y concentra la nueva consola, la exportación de informe y el contrato de caso.

El sistema anterior sigue en el repo como **legado reutilizable**:

- para extraer motor y utilidades todavía valiosas
- para mantener compatibilidad mientras cerramos la transición
- pero ya no debe entenderse como la experiencia principal del producto

Mapa de transición y limpieza:

- [`docs/RECONSTRUCCION_NOUMENON_V2.md`](docs/RECONSTRUCCION_NOUMENON_V2.md)
- [`docs/TRANSICION_REPO_V2.md`](docs/TRANSICION_REPO_V2.md)
- [`docs/LEGACY_INVENTORY.md`](docs/LEGACY_INVENTORY.md)
- [`docs/V2_DEMO_PLAYBOOK.md`](docs/V2_DEMO_PLAYBOOK.md)
- [`docs/ARQUETIPOS_NOUMENON_CANON_V1.md`](docs/ARQUETIPOS_NOUMENON_CANON_V1.md)

## Producto V2

Noumenon V2 no sustituye el juicio experto. Su función es:

- ordenar evidencia
- operacionalizar la metodología
- visualizar tensiones y fugas
- apoyar diagnósticos
- producir salidas ejecutivas defendibles

## Legado

El flujo previo basado en [`app.py`](./app.py) queda como referencia y fuente de piezas reutilizables, no como shell principal recomendado.

## Estrategia de producto (Fase A)

La **promesa de producto** (ICP, entregas, límites explícitos) está congelada en:

**[`docs/FASE_A_PROMESA.md`](docs/FASE_A_PROMESA.md)**

Antes de ampliar alcance o prometer automatismo total, ese documento es la referencia.

**Lexicón AKXOM** (Leviatán, Capa Basal, Fricción, Eutaxia): [`docs/GLOSARIO_AKXOM.md`](docs/GLOSARIO_AKXOM.md) — mismo vocabulario en Consola (expander) e informes.

## Requisitos

- Python **3.10+**
- Navegador Chromium para PDF (instalado por Playwright, ver abajo)

## Instalación

```bash
cd noumenon
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Ejecutar la aplicación V2

```bash
source .venv/bin/activate
streamlit run app_v2.py
```

Abre la URL que muestra Streamlit (por defecto `http://localhost:8501`). Usa la consola V2 para el flujo principal:

- caso
- evidencia
- estructura
- diagnóstico
- informe

## Ejecutar la demo pública de jurado

Para una versión cerrada, solo lectura y centrada en Helios:

```bash
source .venv/bin/activate
streamlit run app_jury.py
```

Esta variante:

- fija `Helios AI` como caso público
- limita el recorrido a `Diagnóstico` e `Informe`
- elimina operativa de guardado y edición
- desactiva la exportación PDF para priorizar estabilidad en despliegue

## Ejecutar el legado

Solo si necesitas contrastar o rescatar piezas del sistema previo:

```bash
source .venv/bin/activate
streamlit run app.py
```

## Verificación automática (regresión motor)

Tras cambios en `doc_ingest`, `motor_*` o `simulation`:

```bash
./scripts/verify_mvp.sh
```

Salida esperada: todos los casos de `phase29_suite.py` en verde, más `tests/test_archetypes.py` y `tests/test_oracular_report_smoke.py`.

Prueba rápida solo de arquetipos + informe oracular:

```bash
python3 -m pytest tests/test_archetypes.py tests/test_oracular_report_smoke.py -q
```

Validación de ingest estructural (gold set concentrado/degradado/equilibrado):

```bash
python3 -m pytest tests/test_ingest_gold_cases.py -q
python3 scripts/eval_ingest_gold.py
```

## Verificación V2

Para comprobar el shell y contrato de la V2:

```bash
./scripts/verify_v2.sh
```

## Definition of Done — Fase 0 (comprobar manualmente en UI)

1. Indicar cliente / proyecto / analista y objetivo.
2. Pegar evidencia de texto (y opcionalmente PDF) y obtener propuestas de lectura.
3. Ejecutar el motor (mixto guiado / auto-evaluar según flujo actual).
4. Generar y descargar **PDF** sin errores.
5. Confirmar que el informe muestra **lectura** y **trazabilidad** (por qué) a un nivel al menos inicial.

Si los cinco puntos pasan, Fase 0 está cerrada para release interna.

## Notas

- Los análisis guardados en disco van a `noumenon_data/` (JSON); esa carpeta está en `.gitignore` para no versionar datos de cliente.
- Los casos y reportes V2 se guardan en `noumenon_data_v2/`.
- **CEO Demo**: mantener solo compatibilidad; foco producto = Consola + motor + informe.
- Canon arquetípico y mapeo actual:
  - `docs/ARQUETIPOS_NOUMENON_CANON_V1.md`
  - `docs/ARQUETIPOS_MAPEO_CANON_MOTOR_V1.md`
  - `docs/ARQUETIPOS_FRONTERAS_CANON_V1.md`
  - `docs/GOLD_SET_ARQUETIPOS_V1.md`
