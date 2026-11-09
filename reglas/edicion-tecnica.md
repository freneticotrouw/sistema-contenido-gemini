# Edición: reglas técnicas por defecto

Las preferencias visuales (colores, fuentes, ritmo, stickers, zooms) vienen de `cuentas/<cuenta>/marca.json` y `edicion.md`. Esto es solo lo técnico:

- Salida 1080×1920, 30 fps, H.264, SDR bt709. Si el video viene en HDR (iPhone), convertir con tonemap antes de editar.
- Audio a -14 LUFS y true peak ≤ -1 dBTP, medido en la salida.
- **Paso 1, cortes:** transcripción por palabra del mismo archivo que se corta; cada corte en silencio, ~0,15 s antes de la primera palabra y después de la última; ningún clip <0,5 s; ninguna pausa >0,4 s; sin frases repetidas (quedarse con la última toma completa). Verificar: transcribir la salida y comparar con el guion (≥95 % de palabras); si falla, rehacer.
- **Paso 2, imágenes:** no empezar sin fotos o imágenes en `assets/`. Mostrar cada persona, marca o cosa cuando se menciona.
- **Paso 3, subtítulos:** con las fuentes y colores de `marca.json`, legibles y dentro de la zona segura (sin tapar la interfaz de la red).
- Cada paso termina con `python -m cs aprobar` hecho por la persona, nunca por ti.
- Cuando la persona corrige algo de la edición, anótalo en `cuentas/<cuenta>/edicion.md` para la próxima vez.
