---
name: metricas
description: Vuelve a leer las cuentas y actualiza qué funciona
---

Cuenta: lo que la persona escribió después del comando
`python -m cs descargar <cuenta> --solo-datos` (trae vistas y copys sin bajar videos) y `python -m cs muestras <cuenta>`. Usa la skill `analista` para comparar con la vez anterior y actualizar `que-funciona.md` (qué subir, qué dejar). Guarda un informe corto en `cuentas/<cuenta>/informes/<fecha>.md` y resume en 5 líneas. Luego `python -m cs sync -m "metricas <cuenta>"`.
