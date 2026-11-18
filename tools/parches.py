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

PARCHES_TEMPLATE = []
