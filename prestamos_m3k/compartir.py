"""Enviar recibos por WhatsApp: botón «Compartir» del celular (con la imagen) y enlace al chat del cliente."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib.parse import quote


def telefono_wa(telefono: str | None) -> str | None:
    """Número en formato internacional sin signos (Perú: 9 dígitos → 51 + número). None si no sirve."""
    dig = re.sub(r"\D", "", telefono or "")
    if dig.startswith("00"):
        dig = dig[2:]
    if len(dig) == 9 and dig.startswith("9"):
        return "51" + dig
    if 10 <= len(dig) <= 15:
        return dig
    return None


def _valor(d: dict, etiqueta: str) -> str:
    for e, v, *_ in d["bloque2"]:
        if e == etiqueta:
            return str(v)
    return ""


def mensaje(d: dict, nombre_cliente: str) -> str:
    """Texto corto que acompaña a la imagen."""
    primero = (nombre_cliente or "").split()[0].capitalize() if nombre_cliente else ""
    saludo = f"Hola {primero}, " if primero else "Hola, "
    if d["titulo"] == "Recibo de cobro" and d.get("cancelado"):
        return (f"{saludo}recibimos tu pago de {_valor(d, 'TOTAL COBRADO')}. Recibo {d['folio']}. "
                "¡Tu préstamo quedó CANCELADO! Gracias.")
    if d["titulo"] == "Recibo de cobro":
        return (f"{saludo}recibimos tu pago de {_valor(d, 'TOTAL COBRADO')}. Recibo {d['folio']}. "
                f"Saldo del crédito: {_valor(d, 'Saldo del crédito tras este cobro')}. ¡Gracias!")
    return (f"{saludo}te envío tu recibo de desembolso {d['folio']}: capital {_valor(d, 'Capital entregado')}, "
            f"total a pagar {_valor(d, 'Total a pagar')}.")


def enlace_chat(telefono: str | None, texto: str) -> str | None:
    num = telefono_wa(telefono)
    return f"https://wa.me/{num}?text={quote(texto)}" if num else None


def html_compartir(png: bytes, nombre_archivo: str, texto: str) -> str:
    """Botón que abre el menú de compartir del teléfono con la imagen adjunta (Web Share API)."""
    b64 = base64.b64encode(png).decode()
    try:
        logo = base64.b64encode((Path(__file__).parent / "assets" / "logos" / "whatsapp.png").read_bytes()).decode()
    except OSError:
        logo = ""
    img = f'<img src="data:image/png;base64,{logo}" width="20" height="20" alt="">' if logo else ""
    return f"""
<button id="b" type="button">{img}Compartir imagen</button><div id="m"></div>
<style>
 body{{margin:0;font-family:Inter,system-ui,sans-serif}}
 button{{width:100%;box-sizing:border-box;height:44px;border-radius:999px;border:1px solid rgba(184,245,58,.5);
   background:rgba(184,245,58,.14);color:#D6F58C;font:600 15px Inter,system-ui,sans-serif;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px}}
 button:hover{{background:rgba(184,245,58,.24);border-color:rgba(184,245,58,.8)}}
 #m{{color:#9A9AA0;font-size:12px;margin-top:6px}}
</style>
<script>
const b64={json.dumps(b64)}, nombre={json.dumps(nombre_archivo)}, texto={json.dumps(texto)};
const msg=document.getElementById("m");
document.getElementById("b").onclick=async()=>{{
  try{{
    const bin=atob(b64), u=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
    const f=new File([u],nombre,{{type:"image/png"}});
    if(navigator.canShare&&navigator.canShare({{files:[f]}})){{await navigator.share({{files:[f],text:texto}});}}
    else{{msg.textContent="Este navegador no permite compartir. Usa «Descargar imagen».";}}
  }}catch(e){{if(e.name!=="AbortError")msg.textContent="No se pudo compartir. Usa «Descargar imagen».";}}
}};
</script>"""


def recordatorio(nombre_cliente: str, monto: str, vencido: bool, numero_prestamo: int | None = None) -> str:
    """Mensaje corto de recordatorio de pago para mandar por WhatsApp (el monto ya viene con formato, p. ej. «S/ 180.00»)."""
    primero = (nombre_cliente or "").split()[0].capitalize() if nombre_cliente else ""
    saludo = f"Hola {primero}, " if primero else "Hola, "
    credito = f" de tu préstamo {numero_prestamo:04d}" if numero_prestamo else ""
    cuando = "tienes vencido" if vencido else "te toca pagar hoy"
    return f"{saludo}te escribo de M3K Préstamos: {cuando} {monto}{credito}. ¿A qué hora puedes pagarlo? Gracias."
