"""Parches especificos de ESTA pagina.

Los de PARCHES_BUNDLE y CSS_BASE sirven para cualquier export y conviene
dejarlos. PARCHES_TEMPLATE arranca vacio: ahi va el cableado entre el componente
que genero Claude Design y PaginaNotion, que cambia en cada pagina porque cambia
el codigo del componente.

Cada parche es (nombre, viejo, nuevo). `viejo` puede ser texto exacto o un regex
compilado, y tiene que encontrar exactamente una coincidencia.

Para escribir uno: abri el template con `python3 tools/build.py --ver-template`,
busca el fragmento del componente que queres cambiar y pegalo tal cual como
`viejo`.
"""

import re

# --- Envoltorio del bundle (sirve para cualquier export) ---------------------
#
# Mientras desempaqueta, el bundler pinta un SVG de portada a pantalla completa
# con su propio titulo, mas un cartel de "Unpacking...". Se lee como un primer
# pantallazo distinto al del sitio. Sacandolos queda el fondo del body hasta que
# aparece la pagina. El JS del bundler ya contempla que no existan.
PRECARGA_RE = re.compile(
    r'\n *<div id="__bundler_thumbnail">.*?</div>\n *<div id="__bundler_loading">.*?</div>\n',
    re.S,
)

PARCHES_BUNDLE = [
    ("pantalla de precarga", PRECARGA_RE, "\n"),
]

# --- CSS que se inyecta en el <helmet> ---------------------------------------
#
# El export usa estilos inline en todos lados. Esto es lo unico que puede definir
# media queries y pseudo-elementos, que inline no se pueden escribir.
#
# OJO: un estilo inline le gana a cualquier clase de aca. Para pisar algo que el
# diseno trae inline hace falta !important.
CSS_BASE = """
  /* El <input type="file"> se dibuja con el boton nativo del navegador, con la
     tipografia del sistema y el nombre del archivo recortado. Estas reglas lo
     alinean con el diseno; cambia los colores por los de tu pagina. */
  .pn-archivo { width: 100%; max-width: 100%; font-size: 12px; }
  .pn-archivo::file-selector-button {
    font: inherit;
    text-transform: uppercase;
    border: 0;
    padding: 10px 14px;
    margin-right: 12px;
    cursor: pointer;
  }
  /* Un nombre de archivo largo no tiene donde cortar: sin esto se desborda. */
  .pn-nombre-archivo { overflow-wrap: anywhere; }

  @media (max-width: 640px) {
    /* En mobile el boton y el nombre se apilan, asi cada uno tiene el ancho
       completo y el control entra en cualquier idioma del navegador. */
    .pn-archivo::file-selector-button { display: block; width: 100%; margin: 0 0 10px; }
    .pn-acciones { flex-direction: column; }
    .pn-acciones > button { width: 100%; flex: 0 0 auto !important; }
  }
"""

# --- Cableado del componente (especifico de esta pagina) ---------------------
#
# Ejemplo de como suele quedar, tomado de una pagina real. Reemplazalo por los
# parches de la tuya.
#
# PARCHES_TEMPLATE = [
#     ("leer el estado al cargar", """  componentDidMount() {}""", """  componentDidMount() {
#     PaginaNotion.estado().then(estado => { if (estado) this.setState({ estado }); });
#   }"""),
#     ("enviar el formulario", """  submit = () => {
#     this.setState({ step:3 });
#   };""", """  submit = async () => {
#     if (this.state.enviando) return;
#     this.setState({ enviando:true, error:'' });
#     const r = await PaginaNotion.enviar({
#       nombre: this.state.nombre,
#       email: this.state.email,
#     });
#     if (r.estado) this.setState({ estado: r.estado });
#     if (!r.ok) return this.setState({ enviando:false, error:r.error });
#     this.setState({ step:3, enviando:false });
#   };"""),
# ]

# --- Cableado de ESTA pagina -------------------------------------------------
#
# El componente nace como demo autocontenida: guarda cada inscripcion en el
# localStorage del visitante, cuenta los 50 cupos contra ese mismo localStorage
# y el panel de organizacion exporta un CSV desde ahi. Publicado asi, nadie de
# Limit Lab recibiria una sola inscripcion y el cupo no limitaria nada, porque
# para cada visitante el contador arranca en cero.
#
# Estos parches reemplazan esas tres piezas por el backend de Notion.

# 1. Estado nuevo: lo que responde /api/estado, y el envio en curso.
ESTADO_VIEJO = """  state = { now: Date.now(), step: 1, done: false, openFaq: 0, mobile: false, formInView: false, err: {}, stored: 0,"""
ESTADO_NUEVO = """  state = { now: Date.now(), step: 1, done: false, openFaq: 0, mobile: false, formInView: false, err: {}, stored: 0,
    estado: null, enviando: false, envioError: '',"""

# 2. Al cargar, los cupos salen de Notion y no del navegador.
#
#    Si la consulta falla, estado queda null y la pagina sigue abierta: mostrar
#    "cupo completo" por un error de red seria peor que aceptar una inscripcion
#    de mas, que despues se ve en Notion.
MOUNT_VIEJO = """    this.setState({ stored: this.load().length });"""
MOUNT_NUEVO = """    PaginaNotion.estado().then(estado => { if (estado) this.setState({ estado }); });"""

# 3. El archivo de verdad, no solo su nombre.
#
#    f.comprobante sigue guardando el nombre porque lo usan fileLabel y la
#    validacion; el File va aparte, que es lo que necesita PaginaNotion.
ARCHIVO_VIEJO = """      onFile: e => { const fl = e.target.files && e.target.files[0]; this.upd('comprobante', fl ? fl.name : ''); },"""
ARCHIVO_NUEVO = """      onFile: e => { const fl = e.target.files && e.target.files[0]; this.archivo = fl || null; this.upd('comprobante', fl ? fl.name : ''); },"""

# 4. El envio.
#
#    comunidad viaja como la clave del diseno (raptor / karen / limitlab); la
#    traduccion al nombre de la columna en Notion la hace pagina.config.json.
SUBMIT_VIEJO = """  submit() {
    if (!this.validate2()) return;
    const f = this.state.f, list = this.load();
    list.push({ ...f, dni: f.dni.replace(/\\./g, '').trim(), ts: new Date().toISOString() });
    try { localStorage.setItem(this.KEY, JSON.stringify(list)); } catch (e) {}
    this.setState({ done: true, stored: list.length }); this.scrollToForm();
  }"""
SUBMIT_NUEVO = """  async submit() {
    if (this.state.enviando) return;
    if (!this.validate2()) return;
    if (!this.archivo) return this.setState({ err: { ...this.state.err, comprobante: 'Volvé a elegir el comprobante.' } });

    this.setState({ enviando: true, envioError: '' });
    const f = this.state.f;
    const r = await PaginaNotion.enviar({
      nombre: f.nombre.trim(),
      dni: f.dni.replace(/\\./g, '').trim(),
      nacimiento: f.nacimiento,
      whatsapp: f.whatsapp.trim(),
      mail: f.mail.trim(),
      instagram: f.instagram.trim(),
      comunidad: f.comunidad,
      lesion: f.lesion.trim(),
      comprobante: this.archivo,
    });
    // Cuando rechaza por cupo, el servidor manda el estado al dia: asi la
    // pagina pasa sola a "cupo completo" en vez de seguir ofreciendo lugar.
    if (r.estado) this.setState({ estado: r.estado });
    if (!r.ok) return this.setState({ enviando: false, envioError: r.error });
    this.archivo = null;
    this.setState({ done: true, enviando: false, envioError: '' });
    this.scrollToForm();
  }"""

# 5. "Cupo completo" tambien cuando Notion dice que se lleno, no solo cuando
#    alguien cierra las inscripciones a mano con el prop.
CERRADO_VIEJO = """    const closed = (p.inscripciones ?? 'abiertas') === 'cerradas';"""
CERRADO_NUEVO = """    const closed = (p.inscripciones ?? 'abiertas') === 'cerradas' || !!(s.estado && s.estado.lleno);"""

# 6. El boton dice en que anda y no se puede tocar dos veces.
BOTON_VIEJO = """      submit: () => this.submit(),"""
BOTON_NUEVO = """      submit: () => this.submit(),
      enviando: s.enviando,
      hayEnvioError: !!s.envioError,
      envioError: s.envioError,
      botonEnviar: s.enviando ? 'Enviando…' : 'Me sumo',
      lugares: s.estado ? `Quedan ${Math.max(0, s.estado.cupoTotal - s.estado.total)} de ${s.estado.cupoTotal} lugares.` : 'Cupo limitado a 50 personas.',"""

# 7. El error del envio, arriba de los botones, y el boton que se bloquea.
ACCIONES_VIEJO = ("""                <div style="display:flex;gap:10px">
                  <button type="button" sc-camel-on-click="{{ back }}\"""")
ACCIONES_NUEVO = ("""                <sc-if value="{{hayEnvioError}}" hint-placeholder-val="{{false}}">
                  <p style="margin:0 0 12px;border-left:3px solid #e08a7f;padding:10px 12px;background:rgba(224,138,127,.12);font-size:13px;line-height:1.5;color:#fff">{{envioError}}</p>
                </sc-if>
                <div style="display:flex;gap:10px">
                  <button type="button" sc-camel-on-click="{{ back }}\"""")

BOTON_TXT_VIEJO = """style-active="transform:scale(.98)">Me sumo</button>"""
BOTON_TXT_NUEVO = """style-active="transform:scale(.98)" disabled="{{enviando}}">{{botonEnviar}}</button>"""

# 8. El cupo que se muestra sale de Notion.
CUPO_VIEJO = """Cupo limitado a 50 personas. Inscripciones abiertas hasta completar el cupo."""
CUPO_NUEVO = """{{ lugares }} Inscripciones abiertas hasta completar el cupo."""

# 9. Fuera el panel de organizacion.
#
#    El propio diseno lo marca como demo: "los registros se guardan en este
#    navegador. En produccion, conectar a un destino privado con acceso
#    restringido". Las inscripciones ahora viven en Notion, que ya tiene control
#    de acceso y exporta CSV. Dejar el panel pidiendo ese listado desde una
#    pagina publica significaria exponer nombre, DNI y fecha de nacimiento de
#    las 50 personas a cualquiera que abra la URL.
PANEL_RE = re.compile(
    r'\n *<section data-screen-label="Panel organización".*?</section>\n',
    re.S,
)

PARCHES_TEMPLATE = [
    ("estado del componente", ESTADO_VIEJO, ESTADO_NUEVO),
    ("leer los cupos al cargar", MOUNT_VIEJO, MOUNT_NUEVO),
    ("guardar el archivo del comprobante", ARCHIVO_VIEJO, ARCHIVO_NUEVO),
    ("enviar a Notion", SUBMIT_VIEJO, SUBMIT_NUEVO),
    ("cupo completo cierra el formulario", CERRADO_VIEJO, CERRADO_NUEVO),
    ("claves nuevas del template", BOTON_VIEJO, BOTON_NUEVO),
    ("error de envio sobre los botones", ACCIONES_VIEJO, ACCIONES_NUEVO),
    ("boton con estado de envio", BOTON_TXT_VIEJO, BOTON_TXT_NUEVO),
    ("lugares restantes desde Notion", CUPO_VIEJO, CUPO_NUEVO),
    ("sacar el panel de organizacion", PANEL_RE, "\n"),
]
