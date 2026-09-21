# Generación de Informes — Guía para colaboradores sin acceso al sistema

Este paquete te permite generar el Informe técnico completo (Word, VT-CHECK
LIST parchado, Anexos y el Informe Compilado al 100% en PDF), sin necesitar
acceso a la app web ni al repositorio de GitHub. Es exactamente el mismo
motor de generación que usa la app — mismas reglas, mismo catálogo de
hallazgos/recomendaciones, misma plantilla Word.

Hay dos formas de usarlo: con **Claude Code** instalado en tu computador
(Opción A), o directamente en un **Proyecto de claude.ai** en el navegador,
sin instalar nada (Opción B). Elige la que tengas disponible.

---

## OPCIÓN B — Proyecto de claude.ai, sin instalar nada

1. Crea (o usa) un Proyecto de claude.ai y sube **todos** los archivos de
   este paquete a su panel de **Contexto**.
2. Abre un chat nuevo dentro de ese Proyecto.

### ⚠️ Regla crítica: la plantilla Word NO va en Contexto

El panel de Contexto de los Proyectos **extrae el contenido como texto** de
cada archivo para poder buscar en él — con `.py`, `.md`, `.txt` y los
`.xlsx` de datos (base maestra, catálogo) esto no es un problema, porque son
texto o tablas planas y sobreviven intactos. Pero `plantilla_base.docx` es
un Word real con tablas, cuadros de texto y logo: si lo dejas en Contexto,
se vuelve un volcado de texto plano de unos 9 KB, ya no un `.docx` real, y
el motor no puede abrirlo (falla al generar el Word, los Anexos y el PDF
compilado — **solo** alcanza a generar el VT-CHECK LIST parchado, que no
depende de la plantilla).

**Por eso `plantilla_base.docx` se adjunta directamente en el mensaje del
chat cada vez que pides generar un informe** (no se deja solo en Contexto).
Usa este mensaje como plantilla, adjuntando los archivos que corresponda:

> Adjunto `plantilla_base.docx` (la plantilla Word real), el detalle de
> grupo `Detalle_GT-023.xlsx`, las fotos de la unidad y el VT-CHECK LIST
> `VT-CHECK_LIST_GT-023.xlsx`. Usando generar_informe_cli.py (ya está en el
> Contexto del proyecto, junto con la base maestra y el catálogo),
> genera el Informe Word, el VT-CHECK LIST parchado, los Anexos y el
> Informe Compilado al 100% en PDF.

Claude te va a entregar los archivos generados directamente en el chat,
listos para descargar.

---

## OPCIÓN A — Claude Code, instalado en tu computador

### 1. Qué necesitas antes de empezar

1. Tener [Claude Code](https://claude.ai/code) instalado en tu computador.
2. Tener Python 3.10 o superior instalado.
3. Descomprimir este paquete en una carpeta.
4. Abrir una terminal en esa carpeta e instalar las dependencias:
   ```
   pip install -r requirements_cli.txt
   ```
5. **(Opcional)** Si además quieres el "Informe Compilado al 100%" en PDF
   (Word + todos los anexos fusionados en un solo PDF), instala LibreOffice
   (gratuito). Sin esto, igual se generan todos los demás entregables
   (Word, checklist, anexos), solo falta ese PDF final:
   - Windows / Mac: instala LibreOffice desde su sitio oficial.
   - Linux (Ubuntu/Debian):
     ```
     sudo apt install libreoffice fonts-crosextra-caladea fonts-crosextra-carlito
     ```
6. Abre Claude Code en esta carpeta.

### 2. Qué archivos debes preparar

**Obligatorios:**
1. Detalle de grupo / líneas (Excel) — el mismo archivo que se usa hoy para
   cargar el grupo en la app.
2. Fotos de la Unidad (una carpeta con las fotos `.jpg`/`.png`).

**Opcionales** (si los tienes, mejor — sin ellos el informe igual se genera,
con las secciones correspondientes marcadas "PENDIENTE"):

3. VT-CHECK LIST (Excel) ya diligenciado en campo.
4. Archivo PSAIM (Excel).
5. P&ID del grupo (PDF).
6. Isométricos por línea (PDF, uno por archivo — el **nombre del archivo**
   debe incluir el TAG de la línea, p.ej. `iso_4-22-71-11.pdf`, para que se
   asigne automáticamente a esa línea).

### 3. Cómo pedirle a Claude que genere el informe

Copia tus archivos dentro de esta carpeta (o en una subcarpeta), abre Claude
Code aquí, y pídele algo así:

> Genera el informe del grupo usando generar_informe_cli.py. El detalle de
> grupo es `Detalle_GT-023.xlsx`, las fotos están en la carpeta `fotos/`, el
> checklist es `VT-CHECK_LIST_GT-023.xlsx` y el PSAIM es `PSAIM_GT-023.xlsx`.
> Guarda todo en la carpeta `salida/`.

Claude va a correr el motor y entregarte:
- El **Informe Word** (`.docx`)
- El **VT-CHECK LIST parchado** con hallazgos/recomendaciones (`.xlsx`), si
  subiste el checklist
- Los **Anexos comprimidos** (`.zip`)
- El **Informe Compilado al 100%** en PDF (si tienes LibreOffice instalado)

### 4. También puedes correrlo tú mismo, sin pedírselo a Claude

```
python3 generar_informe_cli.py \
  --detalle "Detalle_GT-023.xlsx" \
  --fotos fotos/ \
  --checklist "VT-CHECK_LIST_GT-023.xlsx" \
  --psaim "PSAIM_GT-023.xlsx" \
  --pid "PID_GT-023.pdf" \
  --isometricos iso_1.pdf iso_2.pdf \
  --salida salida/
```

Solo `--detalle` y `--fotos` son obligatorios. Ejecuta
`python3 generar_informe_cli.py --help` para ver todas las opciones.

---

## Importante (aplica a ambas opciones)

- Los archivos `BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx` (base técnica de líneas)
  y `Catalogo_Hallazgos_Recomendaciones.xlsx` (catálogo de hallazgos y
  recomendaciones) que vienen en este paquete son una **copia congelada** al
  momento de la entrega. Si el administrador del sistema los actualiza más
  adelante (nuevas líneas, nuevos casos), vas a necesitar una copia nueva de
  este paquete para tenerlos al día.
- No compartas este paquete fuera del equipo: incluye la base de datos
  técnica completa de las líneas de la refinería.
