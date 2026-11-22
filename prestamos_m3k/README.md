# M3K Préstamos Personales

App independiente (carpeta propia, no toca la app de informes) para controlar préstamos
personales: clientes, créditos con simulador, cobros, caja, reportes y recibos.

## Cómo ejecutarla

```bash
cd prestamos_m3k
pip install -r requirements.txt
# Para probar sin clave en tu equipo (nunca en la nube):
PRESTAMOS_SIN_CLAVE=1 streamlit run app.py
```

Con clave: copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y cambia `app_password`.
En **Configuración → Datos de ejemplo** puedes cargar una cartera ficticia para recorrer la app.

## Publicarla en Streamlit Community Cloud (segunda app del mismo repositorio)

1. Nueva app → repositorio `control-informes` → archivo principal `prestamos_m3k/app.py`.
2. En *Settings → Secrets* pega el contenido de `secrets.toml.example` ya completado.
3. **Respaldo obligatorio en la nube:** el disco de Streamlit Cloud se borra al reiniciar. Crea una carpeta
   de Drive solo para préstamos, compártela con la cuenta de servicio y pon su ID en `prestamos_drive_folder_id`.
   Sin eso, descarga un respaldo desde *Configuración* con frecuencia.

## Reglas de negocio (`calculos.py`)

- Interés total plano sobre el periodo: `total = capital × (1 + tasa)`. Por defecto 20 %.
- Los **domingos no se trabaja ni se cobra**: el plazo son 24 días de trabajo (lunes a sábado).
  **Diario**: 24 cuotas, una por día de trabajo. **Semanal**: siempre 4 cuotas iguales, una cada 7 días
  (si cae en domingo pasa al lunes). **Mensual**: de 1 a 3 meses, con 20 % de interés por mes; los primeros meses se paga solo
  el interés y en el último el interés más todo el capital. Cada cuota vence el mismo día de cada mes, o **a fin de mes**: entonces la primera cuota vence el último día del mes de la entrega y cobra solo
  el interés de esos días (20 % ÷ 30 por día), y luego vienen los meses completos (si una fecha cae domingo, pasa al lunes).
- La última cuota absorbe los céntimos de redondeo.
- Cada cobro cubre primero la **mora** (si está activada) y luego las cuotas más antiguas; se admiten abonos parciales.
- **Capital en calle** = capital entregado − capital ya recuperado (la parte de capital de cada cuota cobrada).
- **Cartera vencida** = saldo vencido ÷ saldo por cobrar. También se muestran las cuotas vencidas.
- La **mora** está en 0 % (no se cobra hoy) pero se puede activar en *Configuración*.
- Los recibos y folios no se borran: se anulan con motivo y quedan en la auditoría.

## Contabilidad (`contabilidad.py`)

Todo se deriva de créditos, cobros y movimientos (sin segunda base de datos): libro diario con partida doble, libro mayor,
balance de comprobación, estado de resultados (intereses devengados en forma lineal), balance general, flujo de caja mensual,
cuentas por cobrar con antigüedad conciliadas con el mayor, y **cierre mensual** que bloquea operaciones con fecha en meses
cerrados. Las anulaciones generan asientos de reversión. No incluye provisiones por incobrabilidad ni impuestos.
Cuentas: 101 Caja, 121 Cartera, 129 Intereses no devengados, 301 Capital, 302 Retiros, 601 Gastos, 701 Intereses, 702 Mora.

## Pruebas

```bash
cd prestamos_m3k && python -m pytest -q
```

Las pruebas usan los números de la app anterior (caja 4,380, por cobrar 840, ganancia proyectada 220) y los cuatro
créditos semanales del Excel de ejemplo.

## Criterios de interfaz

Basados en las Web Interface Guidelines de Vercel: foco visible, objetivos táctiles de 44 px, importes con números
tabulares, estados siempre con texto (no solo color), estados vacíos con una acción siguiente, formato regional
(`S/ 1,234.50`, `15/11/2026`) y respeto a `prefers-reduced-motion`. Tema claro y denso tipo software contable. En computadora usa pantalla ancha con el menú siempre
visible; el diseño compacto aparece solo en el teléfono.
