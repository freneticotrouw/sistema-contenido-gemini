# Sistema de contenido para Gemini

Un equipo de contenido que vive en tu computador: investiga ideas, escribe guiones con **tu** voz, edita tus videos en 3 pasos y aprende de tus métricas. Funciona con tu suscripción de Google AI Pro o Ultra, sin pagos extra.

## Instalar (un solo comando)

**Windows** (PowerShell):
```
irm https://raw.githubusercontent.com/freneticotrouw/sistema-contenido-gemini/main/instalar.ps1 | iex
```
**Mac** (Terminal):
```
curl -fsSL https://raw.githubusercontent.com/freneticotrouw/sistema-contenido-gemini/main/instalar.sh | bash
```
Instala lo que falte (Python, ffmpeg, yt-dlp, Whisper y Antigravity CLI, el asistente de Gemini en la terminal que reemplazó a Gemini CLI), crea la carpeta `mi-contenido` y lo abre. Cuando te pida iniciar sesión, entra con la cuenta de Google de tu suscripción. **No uses una API key**: esa se cobra aparte.

## Primer uso
Escribe en Gemini:
```
/empezar
```
Te pide tus cuentas de Instagram y TikTok (y, si quieres, referentes), baja tus videos públicos, los escucha y los mira, y arma tu estilo, tus temas, tus estructuras y tu paleta. Tú los apruebas.

## Día a día
| Comando | Para qué |
|---|---|
| `/ideas` | Ideas nuevas investigadas en la web, según lo que te funciona |
| `/guion <id>` | Guion con tu voz |
| `/editar <id>` | Edición en 3 pasos (cortes, imágenes, subtítulos), cada uno con tu aprobación |
| `/metricas` | Vuelve a leer tus cuentas y actualiza qué funciona |
| `/que-sigue` | El siguiente paso, en una frase |
| `/centro` | Abre el Centro de contenido en el navegador (también desde el celular, en la misma wifi) |

## Actualizar
`python -m cs actualizar` trae la versión nueva sin tocar tus cuentas ni tus contenidos.

## Qué se queda en tu computador
Todo. Los videos descargados y los tuyos nunca se suben a ningún lado. Solo analiza cuentas públicas o la tuya.
