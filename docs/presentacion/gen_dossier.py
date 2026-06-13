# -*- coding: utf-8 -*-
"""
Genera DOSSIER_GENESIS.pdf a partir del contenido institucional de GENESIS.
Tema: tecnologico tipo "JARVIS" claro/elegante con acentos cian/aguamarina.
Contenido FIEL al markdown fuente: no se inventan datos ni cifras.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, NextPageTemplate, ListFlowable, ListItem, HRFlowable
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "DOSSIER_GENESIS.pdf")

# ---- Paleta JARVIS ----
ACCENT   = colors.HexColor("#2dffae")   # aguamarina / cian-verde
ACCENT_D = colors.HexColor("#11a679")   # version oscura para texto
INK      = colors.HexColor("#0d2230")   # azul petroleo casi negro
INK_SOFT = colors.HexColor("#33505f")   # gris-azulado para cuerpo
PANEL    = colors.HexColor("#f0f7f4")   # fondo de tablas claro
PANEL_HD = colors.HexColor("#0d2230")   # cabecera de tabla oscura
LINE     = colors.HexColor("#cfe8df")
DARK_BG  = colors.HexColor("#0a1a25")   # fondo portada
QUOTE_BG = colors.HexColor("#e7faf2")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm

# ---------------- Estilos ----------------
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

title_cover = S("titleCover", fontName="Helvetica-Bold", fontSize=58,
                textColor=colors.white, alignment=TA_CENTER, leading=60, spaceAfter=6)
sub_cover = S("subCover", fontName="Helvetica", fontSize=15,
              textColor=ACCENT, alignment=TA_CENTER, leading=22, spaceAfter=4)
small_cover = S("smallCover", fontName="Helvetica", fontSize=10.5,
                textColor=colors.HexColor("#9fc7bb"), alignment=TA_CENTER, leading=16)
tag_cover = S("tagCover", fontName="Helvetica-Oblique", fontSize=12,
              textColor=colors.white, alignment=TA_CENTER, leading=18)

h1 = S("h1", fontName="Helvetica-Bold", fontSize=18, textColor=INK,
       spaceBefore=10, spaceAfter=8, leading=22)
h2 = S("h2", fontName="Helvetica-Bold", fontSize=12.5, textColor=ACCENT_D,
       spaceBefore=10, spaceAfter=4, leading=16)
body = S("body", fontName="Helvetica", fontSize=10.5, textColor=INK_SOFT,
         alignment=TA_JUSTIFY, leading=15.5, spaceAfter=6)
bullet = S("bullet", fontName="Helvetica", fontSize=10.5, textColor=INK_SOFT,
           leading=15, spaceAfter=2)
quote = S("quote", fontName="Helvetica-Oblique", fontSize=11.5, textColor=INK,
          leading=17, leftIndent=8, rightIndent=8)
cell = S("cell", fontName="Helvetica", fontSize=9.5, textColor=INK_SOFT, leading=13)
cellb = S("cellb", fontName="Helvetica-Bold", fontSize=9.5, textColor=INK, leading=13)
cellh = S("cellh", fontName="Helvetica-Bold", fontSize=9.8, textColor=colors.white, leading=13)
toc_note = S("tocNote", fontName="Helvetica-Oblique", fontSize=9.5,
             textColor=INK_SOFT, leading=13)
foot = S("foot", fontName="Helvetica", fontSize=8, textColor=INK_SOFT)


class GenesisDoc(BaseDocTemplate):
    """Doc con TOC clickable y numeracion de secciones registrada."""
    def beforeDocument(self):
        # reiniciar contador de bookmarks en cada pasada de multiBuild
        self._tockey = 0

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            st = flowable.style.name
            if st == 'h1':
                txt = flowable.getPlainText()
                self._tockey = getattr(self, '_tockey', 0) + 1
                key = 'h1-%d' % self._tockey
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (0, txt, self.page, key))


# ---------------- Decoradores de pagina ----------------
def _tech_corner(c, x, y, size, flip_x=1, flip_y=1):
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.line(x, y, x + flip_x * size, y)
    c.line(x, y, x, y + flip_y * size)


def cover_bg(c, doc):
    c.saveState()
    c.setFillColor(DARK_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # rejilla tenue
    c.setStrokeColor(colors.HexColor("#12313f"))
    c.setLineWidth(0.4)
    step = 18 * mm
    x = 0
    while x < PAGE_W:
        c.line(x, 0, x, PAGE_H); x += step
    y = 0
    while y < PAGE_H:
        c.line(0, y, PAGE_W, y); y += step
    # arco/anillo decorativo
    c.setStrokeColor(colors.HexColor("#1f6e57"))
    c.setLineWidth(1.0)
    cx, cy = PAGE_W/2, PAGE_H*0.66
    for r in (52*mm, 60*mm):
        c.circle(cx, cy, r, stroke=1, fill=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2.2)
    c.arc(cx-46*mm, cy-46*mm, cx+46*mm, cy+46*mm, 25, 110)
    c.arc(cx-46*mm, cy-46*mm, cx+46*mm, cy+46*mm, 200, 95)
    # esquinas tech
    m = 12 * mm
    _tech_corner(c, m, m, 14*mm, 1, 1)
    _tech_corner(c, PAGE_W-m, m, 14*mm, -1, 1)
    _tech_corner(c, m, PAGE_H-m, 14*mm, 1, -1)
    _tech_corner(c, PAGE_W-m, PAGE_H-m, 14*mm, -1, -1)
    c.restoreState()


def content_bg(c, doc):
    c.saveState()
    # encabezado
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, PAGE_H - 13*mm, "GENESIS")
    c.setFillColor(INK_SOFT)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 13*mm,
                      "Asistente de IA personal, 100% local")
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.0)
    c.line(MARGIN, PAGE_H - 15*mm, PAGE_W - MARGIN, PAGE_H - 15*mm)
    # acento corto cian extra
    c.setLineWidth(2.4)
    c.line(MARGIN, PAGE_H - 15*mm, MARGIN + 22*mm, PAGE_H - 15*mm)
    # pie
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.line(MARGIN, 14*mm, PAGE_W - MARGIN, 14*mm)
    c.setFillColor(INK_SOFT)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, 9.5*mm, "GENESIS — Dossier de presentacion")
    c.drawRightString(PAGE_W - MARGIN, 9.5*mm, "Pagina %d" % doc.page)
    c.setFillColor(ACCENT_D)
    c.drawCentredString(PAGE_W/2, 9.5*mm, "Inteligencia artificial personal, local y soberana")
    c.restoreState()


# ---------------- Helpers de contenido ----------------
def bullets(items, style=bullet):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=10,
                  value='•', bulletColor=ACCENT_D) for t in items],
        bulletType='bullet', start='•', leftIndent=14,
        bulletColor=ACCENT_D, spaceBefore=2, spaceAfter=6,
    )


def num_list(items):
    return ListFlowable(
        [ListItem(Paragraph(t, bullet), leftIndent=12) for t in items],
        bulletType='1', leftIndent=16, bulletColor=ACCENT_D,
        bulletFontName="Helvetica-Bold", spaceBefore=2, spaceAfter=6,
    )


def make_table(data, col_widths, header=True, first_bold=False):
    rows = []
    for r, row in enumerate(data):
        cells = []
        for ci, val in enumerate(row):
            if header and r == 0:
                cells.append(Paragraph(val, cellh))
            elif first_bold and ci == 0:
                cells.append(Paragraph(val, cellb))
            else:
                cells.append(Paragraph(val, cell))
        rows.append(cells)
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    ts = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, LINE),
        ('LINEAFTER', (0, 0), (-2, -1), 0.5, LINE),
        ('BOX', (0, 0), (-1, -1), 0.8, ACCENT),
    ]
    if header:
        ts += [('BACKGROUND', (0, 0), (-1, 0), PANEL_HD),
               ('LINEBELOW', (0, 0), (-1, 0), 1.2, ACCENT)]
    # zebra
    for r in range(1 if header else 0, len(data)):
        if (r % 2) == (1 if header else 0):
            ts.append(('BACKGROUND', (0, r), (-1, r), PANEL))
    t.setStyle(TableStyle(ts))
    return t


def quote_box(text):
    p = Paragraph(text, quote)
    t = Table([[p]], colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), QUOTE_BG),
        ('LINEBEFORE', (0, 0), (0, -1), 3, ACCENT),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


def sec(n, title):
    """Encabezado de seccion numerada (registrado en TOC via h1)."""
    return Paragraph("%d. %s" % (n, title), h1)


# ---------------- Construccion del documento ----------------
def build():
    doc = GenesisDoc(OUT, pagesize=A4,
                     leftMargin=MARGIN, rightMargin=MARGIN,
                     topMargin=22*mm, bottomMargin=20*mm,
                     title="GENESIS — Dossier de presentacion",
                     author="Alex Quinones")

    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id='cover',
                        leftPadding=MARGIN, rightPadding=MARGIN,
                        topPadding=0, bottomPadding=0)
    content_frame = Frame(MARGIN, 18*mm, PAGE_W - 2*MARGIN, PAGE_H - 40*mm,
                          id='content')
    doc.addPageTemplates([
        PageTemplate(id='Cover', frames=[cover_frame], onPage=cover_bg),
        PageTemplate(id='Content', frames=[content_frame], onPage=content_bg),
    ])

    E = []  # story

    # ---- PORTADA ----
    E.append(Spacer(1, 92*mm))
    E.append(Paragraph("GENESIS", title_cover))
    E.append(Spacer(1, 4*mm))
    E.append(Paragraph("Asistente de Inteligencia Artificial Personal, 100% Local", sub_cover))
    E.append(Spacer(1, 6*mm))
    E.append(Paragraph("Privado &nbsp;&middot;&nbsp; Sin nube &nbsp;&middot;&nbsp; Soberano", tag_cover))
    E.append(Spacer(1, 40*mm))
    E.append(Paragraph("Dossier de presentacion del proyecto", small_cover))
    E.append(Paragraph("Version del documento: 1.0 &mdash; Junio 2026", small_cover))
    E.append(Paragraph("Autor: Alex Qui&ntilde;ones", small_cover))

    # ---- TOC ----
    E.append(NextPageTemplate('Content'))
    E.append(PageBreak())
    E.append(Paragraph("Tabla de contenidos",
                       ParagraphStyle('h1toc', parent=h1)))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle('toc1', fontName="Helvetica", fontSize=11,
                       textColor=INK, leading=20, leftIndent=4,
                       firstLineIndent=0)
    ]
    toc.dotsMinLevel = 0
    E.append(toc)

    # ---- 1. Resumen ejecutivo ----
    E.append(PageBreak())
    E.append(sec(1, "Resumen ejecutivo"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph(
        "<b>GENESIS</b> es un asistente de inteligencia artificial de uso personal que "
        "funciona <b>integramente en la computadora del usuario</b>, sin depender de "
        "servicios en la nube ni de APIs externas de pago. A diferencia de los asistentes "
        "comerciales (que envian cada conversacion a servidores de terceros), GENESIS "
        "procesa el lenguaje, genera imagenes, sintetiza voz y controla el sistema operativo "
        "<b>de forma local y privada</b>.", body))
    E.append(Paragraph(
        "El proyecto materializa una idea concreta: <b>soberania digital personal</b> &mdash; "
        "que una persona pueda tener un asistente potente sin entregar sus datos, sin pagar "
        "suscripciones y sin conexion obligatoria a internet.", body))
    E.append(Paragraph(
        "GENESIS esta desarrollado en Python (~146 modulos, ~96.000 lineas de codigo), corre "
        "sobre modelos de lenguaje locales (Ollama) y ofrece una aplicacion de escritorio con "
        "una interfaz tipo &quot;JARVIS&quot;. Es un proyecto en evolucion continua, documentado "
        "version por version, con una suite de pruebas amplia y una arquitectura pensada para "
        "escalar.", body))
    E.append(Spacer(1, 4))
    E.append(quote_box(
        "<b>En una frase:</b> un &quot;JARVIS&quot; personal que piensa, ve, habla, crea y "
        "actua sobre tu computadora &mdash; todo local, privado y bajo tu control."))

    # ---- 2. El problema ----
    E.append(PageBreak())
    E.append(sec(2, "El problema"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph("Los asistentes de IA actuales presentan limitaciones estructurales "
                       "para el usuario:", body))
    E.append(make_table([
        ["Problema", "Impacto"],
        ["Dependencia de la nube", "Cada interaccion viaja a servidores de terceros; sin internet no funcionan."],
        ["Privacidad comprometida", "Conversaciones, archivos y habitos quedan en manos de las empresas."],
        ["Costos recurrentes", "Suscripciones mensuales y cobros por uso de API."],
        ["Caja negra", "El usuario no controla el modelo, sus limites ni sus datos."],
        ["Capacidad de accion limitada", "La mayoria solo conversa; no controlan realmente el equipo."],
    ], [55*mm, PAGE_W - 2*MARGIN - 55*mm], first_bold=True))
    E.append(Spacer(1, 8))
    E.append(Paragraph(
        "En un contexto de creciente preocupacion por la privacidad y la <b>soberania "
        "tecnologica</b>, existe una necesidad real de alternativas que devuelvan el control "
        "al usuario.", body))

    # ---- 3. La solucion ----
    E.append(PageBreak())
    E.append(sec(3, "La solucion: GENESIS"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph("GENESIS responde a cada uno de esos problemas:", body))
    E.append(bullets([
        "<b>100% local</b> &rarr; funciona sin internet; los datos nunca salen del equipo.",
        "<b>Privado por diseno</b> &rarr; secretos y datos personales nunca se transmiten ni se versionan.",
        "<b>Sin costos recurrentes</b> &rarr; no requiere API keys ni suscripciones.",
        "<b>Abierto y controlable</b> &rarr; el usuario elige y administra los modelos.",
        "<b>Capacidad de accion real</b> &rarr; controla apps, hardware, archivos y dispositivos.",
    ]))
    E.append(Paragraph("Capacidades actuales (operativas)", h2))

    E.append(Paragraph("&#129504; &nbsp;Inteligencia", h2))
    E.append(bullets([
        "Modelos de lenguaje locales via Ollama (Llama 3.1 8B personalizado + Qwen 2.5 Coder 7B).",
        "Router multi-proveedor con <i>failover</i> automatico y clasificacion de tareas.",
        "Memoria persistente con recuperacion semantica (RAG), aprendizaje y proactividad.",
        "Auto-mejora de codigo <b>segura</b> (con barreras de seguridad) y evolucion asistida.",
    ]))
    E.append(Paragraph("&#128065; &nbsp;Sentidos y creacion", h2))
    E.append(bullets([
        "<b>Voz</b>: sintesis de voz (22 voces) y <b>clonacion de voz local</b> (modelo XTTS).",
        "<b>Imagenes</b>: generacion local con Stable Diffusion (en GPU, sin servicios externos).",
        "<b>Vision</b>: analisis de imagenes y pantalla.",
    ]))
    E.append(Paragraph("&#127899; &nbsp;Accion sobre el sistema", h2))
    E.append(bullets([
        "Control de volumen, brillo, energia, impresion y multiples monitores.",
        "Gestion de conexiones: WiFi, Bluetooth, USB.",
        "Apertura de aplicaciones y carpetas por nombre; gestion de archivos con papelera segura.",
        "Reproduccion de musica y <i>casting</i> a TV (Chromecast); integracion con apps de streaming.",
        "Envio y lectura de correo electronico; despertador con voz y musica.",
    ]))
    E.append(Paragraph("&#128421; &nbsp;Interfaz", h2))
    E.append(bullets([
        "Aplicacion de escritorio (cabina tipo &quot;JARVIS&quot;) con nucleo visual reactivo a la voz.",
        "Interfaz web local; panel de control con telemetria del sistema.",
    ]))

    # ---- 4. Diferencial ----
    E.append(PageBreak())
    E.append(sec(4, "Diferencial / innovacion"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(make_table([
        ["Eje", "GENESIS", "Asistentes comerciales"],
        ["Procesamiento", "Local (tu GPU)", "Nube de terceros"],
        ["Privacidad", "Total", "Datos en servidores externos"],
        ["Conexion", "Funciona offline", "Requiere internet"],
        ["Costo", "Sin suscripcion", "Pago mensual / por uso"],
        ["Control del modelo", "Del usuario", "De la empresa"],
        ["Accion en el equipo", "Amplia (sistema, hardware)", "Limitada"],
        ["Evolucion", "Auto-mejora documentada", "Cerrada"],
    ], [42*mm, 55*mm, PAGE_W - 2*MARGIN - 97*mm], first_bold=True))
    E.append(Spacer(1, 8))
    E.append(Paragraph(
        "El valor diferencial no es un modelo nuevo, sino la <b>integracion local y soberana</b> "
        "de capacidades de IA de ultima generacion en un unico asistente que <b>actua</b> sobre "
        "el equipo.", body))

    # ---- 5. Arquitectura ----
    E.append(PageBreak())
    E.append(sec(5, "Arquitectura (vision general)"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph("GENESIS esta organizado en modulos independientes coordinados por un nucleo:", body))
    E.append(bullets([
        "<b>Nucleo / orquestacion</b>: procesa la entrada del usuario, clasifica la intencion y despacha a la capacidad correspondiente.",
        "<b>Motor LLM</b>: Ollama local con router multi-proveedor (y <i>fallback</i> opcional a APIs externas si el usuario las habilita).",
        "<b>Capacidades</b> (modulos <font face='Courier'>core/*.py</font>): voz, imagenes, control de sistema, conexiones, archivos, comunicacion, memoria, etc. &mdash; cada una aislada y combinable.",
        "<b>Interfaz</b>: app de escritorio (PyWebView) + interfaz web (Flask).",
        "<b>Memoria</b>: corto y largo plazo, con recuperacion semantica.",
    ]))
    E.append(Paragraph("Principios de diseno:", h2))
    E.append(num_list([
        "<i>Local-first</i> y privacidad (nada sale del equipo sin pedirlo).",
        "Aislamiento por modulo (crecer sin romper lo existente).",
        "Barreras de seguridad en la auto-modificacion.",
        "Degradacion gracil (si algo falla, hay <i>fallback</i>; nunca se rompe del todo).",
        "Verificacion empirica antes de declarar &quot;funciona&quot;.",
    ]))
    E.append(Spacer(1, 4))
    E.append(quote_box(
        "<b>Hardware de referencia:</b> RTX 3060 Ti (8GB VRAM), Intel i7-13700KF, 16 GB RAM, Windows 11."))

    # ---- 6. Estado del proyecto ----
    E.append(PageBreak())
    E.append(sec(6, "Estado del proyecto"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(make_table([
        ["Dimension", "Estado"],
        ["Madurez", "Producto funcional en uso real, en evolucion continua."],
        ["Escala de codigo", "~146 modulos, ~96.000 lineas de Python."],
        ["Calidad", "Suite de pruebas amplia (decenas de suites de tests)."],
        ["Trazabilidad", "Evolucion documentada version por version (v1.0 &rarr; v6.1)."],
        ["Modelos en produccion", "2 modelos Ollama locales (general + especializado en codigo)."],
    ], [48*mm, PAGE_W - 2*MARGIN - 48*mm], first_bold=True))
    E.append(Spacer(1, 8))
    E.append(Paragraph(
        "<i>(Las cifras provienen de la documentacion interna del proyecto, "
        "<font face='Courier'>PROJECT_EVOLUTION.md</font>.)</i>", toc_note))

    # ---- 7. Roadmap ----
    E.append(PageBreak())
    E.append(sec(7, "Hoja de ruta (Roadmap)"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph(
        "El proyecto avanza por versiones tematicas. Proxima evolucion mayor: "
        "<b>v7.0 &quot;Unbound&quot;</b>, organizada en 4 lineas de trabajo:", body))
    E.append(num_list([
        "<b>Conductor</b> &mdash; orquestacion inteligente de recursos (GPU) y plataforma de herramientas: permite usar voz + imagen + lenguaje simultaneamente sin saturar la memoria de la GPU.",
        "<b>Sentidos en tiempo real</b> &mdash; vision continua (camara/pantalla) y medios integrados.",
        "<b>Autonomia</b> &mdash; agente que ejecuta tareas de varios pasos por su cuenta.",
        "<b>Alcance</b> &mdash; control remoto y acceso desde el movil.",
    ]))
    E.append(Paragraph(
        "El roadmap es un <b>documento vivo</b>, pensado para escalar de forma ordenada.", body))

    # ---- 8. Impacto ----
    E.append(PageBreak())
    E.append(sec(8, "Impacto y aplicaciones"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(bullets([
        "<b>Privacidad y soberania</b>: alternativa real a los asistentes que dependen de la nube.",
        "<b>Accesibilidad</b>: asistente por voz que controla el equipo (potencial uso en accesibilidad).",
        "<b>Educacion</b>: plataforma para aprender IA aplicada, integracion de modelos y arquitectura.",
        "<b>Productividad</b>: automatizacion de tareas cotidianas del escritorio.",
        "<b>Independencia tecnologica</b>: no requiere infraestructura ni proveedores externos.",
    ]))

    # ---- 9. Equipo ----
    E.append(PageBreak())
    E.append(sec(9, "Equipo y desarrollo"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph(
        "Proyecto desarrollado de forma independiente por <b>Alex Qui&ntilde;ones</b>, con "
        "metodologia de desarrollo estructurada (analisis &rarr; diseno &rarr; planificacion "
        "&rarr; desarrollo &rarr; pruebas &rarr; documentacion) y control de versiones con "
        "historial limpio y trazable.", body))

    # ---- 10. Contacto ----
    E.append(sec(10, "Contacto"))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph("<b>Alex Qui&ntilde;ones</b>", body))
    E.append(Paragraph("<i>(Datos de contacto a completar segun la presentacion.)</i>", toc_note))
    E.append(Spacer(1, 14))
    E.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    E.append(Paragraph(
        "<i>GENESIS &mdash; Inteligencia artificial personal, local y soberana.</i>",
        ParagraphStyle('end', parent=body, alignment=TA_CENTER, textColor=ACCENT_D,
                       fontName="Helvetica-Oblique")))

    # multiBuild para resolver TOC
    doc.multiBuild(E)
    return OUT


if __name__ == "__main__":
    path = build()
    print("PDF generado:", path)
    print("Tamano (bytes):", os.path.getsize(path))
