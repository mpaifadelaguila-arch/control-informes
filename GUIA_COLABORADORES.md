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

### Cómo reconocer cada archivo adjunto

No hace falta usar el nombre exacto de archivo de los ejemplos: basta con
que el nombre incluya la palabra clave correspondiente para que se
identifique correctamente, sin importar el resto del nombre:

- **Plantilla Word**: `plantilla_base.docx` / `plantilla_complementario.docx`.
- **PSAIM**: cualquier archivo Excel cuyo nombre incluya la palabra
  **"PSAIM"** (p.ej. `Informe PSAIM ITEM 120 Comp. Temp.xlsx`) se asume
  como archivo PSAIM del informe. Puedes adjuntar **más de uno** — lo
  normal es que solo la(s) línea(s) con medición de espesores traiga(n)
  su propio archivo PSAIM por separado; cada archivo se asigna
  automáticamente a su línea (por el TAG dentro del archivo o en su
  nombre), sin que tengas que combinarlos tú a mano en un solo Excel.
- **VT-CHECK LIST**: cualquier archivo Excel cuyo nombre incluya
  "CHECK LIST" o "CHECKLIST".
- **Detalle de grupo / Detalle de líneas**: el Excel que trae las columnas
  ITEM, SAP, LINEAS, ALCANCE DEL SERVICIO, etc. (identifícalo por su
  contenido si el nombre no es claro).

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
4. Archivo(s) PSAIM (Excel) — uno solo, o varios (uno por línea con
   medición de espesores, que es lo normal).
5. P&ID del grupo (PDF).
6. Isométricos por línea (PDF, uno por archivo — el **nombre del archivo**
   debe incluir el TAG de la línea, p.ej. `iso_4-22-71-11.pdf`, para que se
   asigne automáticamente a esa línea).

### 3. Cómo pedirle a Claude que genere el informe

Copia tus archivos dentro de esta carpeta (o en una subcarpeta), abre Claude
Code aquí, y pídele algo así:

> Genera el informe del grupo usando generar_informe_cli.py. El detalle de
> grupo es `Detalle_GT-023.xlsx`, las fotos están en la carpeta `fotos/`, el
> checklist es `VT-CHECK_LIST_GT-023.xlsx` y el PSAIM es `PSAIM_GT-023.xlsx`
> (si tienes más de un archivo PSAIM, uno por línea, menciónalos todos).
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
  --psaim "PSAIM_linea1.xlsx" "PSAIM_linea2.xlsx" \
  --pid "PID_GT-023.pdf" \
  --isometricos iso_1.pdf iso_2.pdf \
  --salida salida/
```

Solo `--detalle` y `--fotos` son obligatorios. Ejecuta
`python3 generar_informe_cli.py --help` para ver todas las opciones.

---

## INFORME COMPLEMENTARIO / ANEXO ADICIONAL

Para cuando, de un grupo de tuberías ya entregado, quedaron líneas sin
inspeccionar en su momento y ahora se inspeccionan e informan como anexo al
informe principal (solo inspección visual VT, nunca lleva PSAIM/Anexo C).
Es un módulo **independiente** del informe normal: usa su propia plantilla
(`plantilla_complementario.docx`) y su propio script
(`generar_informe_complementario_cli.py`), sin afectar en nada al flujo
anterior.

**Archivos:**
- Obligatorios: Detalle de líneas (Excel, **debe traer la columna
  "N° ORIGINAL"** para conservar la numeración del informe principal) y el
  texto del Sumario de Inspección (se redacta a mano, es muy específico
  para generarlo automáticamente).
- Opcionales: VT-CHECK LIST, Fotos, P&ID, Isométricos. **Nunca PSAIM.**
- El código de este informe (p.ej. `ADEMINSAC-FIAB-RLP-634-1-2026`, con el
  número de anexo antes del año) se toma de la columna "CODIGO DE INFORME"
  del propio Detalle de líneas — no hay que calcularlo aparte.

**Proyecto de claude.ai:** igual que el informe principal, pero adjuntando
`plantilla_complementario.docx` (nunca la dejes solo en Contexto, por la
misma razón que `plantilla_base.docx`) y usando este mensaje:

> Adjunto `plantilla_complementario.docx`, el Detalle de líneas
> `Detalle_GT-023_complementario.xlsx` y [demás archivos que tengas]. El
> código del informe principal es `ADEMINSAC-FIAB-RLP-634-2026`. El
> Sumario de Inspección es: "[tu texto]". Usando
> generar_informe_complementario_cli.py, genera el Informe Complementario,
> el VT-CHECK LIST parchado, los Anexos y el Informe Compilado en PDF.

**Claude Code / línea de comandos:**

```
python3 generar_informe_complementario_cli.py \
  --detalle "Detalle_GT-023_complementario.xlsx" \
  --sumario "Como resultado de la aplicación de las técnicas de inspección..." \
  --codigo-principal "ADEMINSAC-FIAB-RLP-634-2026" \
  --checklist "VT-CHECK_LIST.xlsx" \
  --fotos fotos/ \
  --salida salida_complementario/
```

Solo `--detalle` y `--sumario` son obligatorios. Ejecuta
`python3 generar_informe_complementario_cli.py --help` para ver todas las
opciones.

---

## Importante (aplica a todo lo anterior)

- Los archivos `BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx` (base técnica de líneas)
  y `Catalogo_Hallazgos_Recomendaciones.xlsx` (catálogo de hallazgos y
  recomendaciones) que vienen en este paquete son una **copia congelada** al
  momento de la entrega. Si el administrador del sistema los actualiza más
  adelante (nuevas líneas, nuevos casos), vas a necesitar una copia nueva de
  este paquete para tenerlos al día.
- No compartas este paquete fuera del equipo: incluye la base de datos
  técnica completa de las líneas de la refinería.
