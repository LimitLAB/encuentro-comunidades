"""Lectura y escritura del template dentro de un export de Claude Design.

Claude Design exporta la pagina como un bundle autocontenido: un HTML que lleva
el HTML real adentro de un <script type="__bundler/template"> como string JSON,
junto con las fuentes, las imagenes y React en base64, y lo desempaqueta en el
navegador.

Este modulo es la parte reutilizable entre paginas: abrir ese sobre sin romperlo
y volver a cerrarlo. Lo especifico de cada pagina va en parches.py.
"""

import json
import re

TEMPLATE_RE = re.compile(
    r'(<script type="__bundler/template">\s*)(.*?)(\s*</script>)', re.S
)


class BundleInvalido(Exception):
    pass


def leer_template(bundle):
    """Devuelve (template, reemplazar) para el bundle dado.

    `reemplazar(nuevo_template)` devuelve el bundle completo con el template
    cambiado, respetando el escapado que espera el navegador.
    """
    match = TEMPLATE_RE.search(bundle)
    if not match:
        raise BundleInvalido(
            "El archivo no parece un export de Claude Design: no tiene "
            '<script type="__bundler/template">.'
        )

    def reemplazar(nuevo):
        # ensure_ascii deja el bundle en ASCII puro, como lo genera Claude Design.
        #
        # El replace de "</" NO es opcional: el template contiene "</script>" y,
        # sin escapar esa barra, el navegador cierra el <script> contenedor en esa
        # primera aparicion en vez de al final, y la pagina queda rota sin ningun
        # error visible. El bundler original hace exactamente lo mismo.
        serializado = json.dumps(nuevo).replace("</", "<\\u002F")
        return (
            bundle[: match.start()]
            + match.group(1) + serializado + match.group(3)
            + bundle[match.end():]
        )

    return json.loads(match.group(2)), reemplazar


def aplicar(texto, parches, donde):
    """Aplica (nombre, viejo, nuevo) o (nombre, viejo, nuevo, veces_esperadas).

    Por defecto exige exactamente una coincidencia. Un parche que toca muchos
    lugares a la vez —por ejemplo bajar los minimos de todos los clamp()— declara
    cuantas espera, asi sigue habiendo un numero que verificar.

    Fallar es deliberado: si el diseno se re-exporta y un anclaje ya no existe,
    es mejor cortar que publicar una pagina a medio conectar.
    """
    for parche in parches:
        nombre, viejo, nuevo = parche[:3]
        esperadas = parche[3] if len(parche) > 3 else 1
        if hasattr(viejo, "subn"):
            texto, veces = viejo.subn(nuevo, texto)
        else:
            veces = texto.count(viejo)
            if veces == esperadas:
                texto = texto.replace(viejo, nuevo)
        if veces != esperadas:
            raise BundleInvalido(
                f"El parche '{nombre}' ({donde}) esperaba {esperadas} coincidencia(s) "
                f"y encontro {veces}.\n"
                "El export de Claude Design cambio: hay que actualizar tools/parches.py."
            )
    return texto


def inyectar_css(template, css):
    """Agrega CSS al <style> del <helmet>, que es el que sobrevive al render."""
    ancla = "</style>\n</helmet>"
    if template.count(ancla) != 1:
        raise BundleInvalido("No se encontro el <style> del helmet para inyectar el CSS.")
    return template.replace(ancla, f"\n{css}\n{ancla}")


def inyectar_js(bundle, js):
    """Agrega el runtime al <head> del bundle. Recibe el bundle, no el template.

    Que sea el <head> del documento externo no es un detalle. Dentro del
    template, el <script> no corre al parsear el HTML sino cuando el bundler
    desempaqueta el template y lo mete en el DOM, y esa inyeccion no esta
    ordenada contra el montaje de los componentes: a veces componentDidMount
    corre primero y revienta con "PaginaNotion is not defined". Falla una de
    cada tres cargas, y cuando falla la pagina no consulta los cupos ni puede
    enviar el formulario.

    En el <head> del documento externo es un script inline comun: corre al
    parsear, mucho antes de que exista ningun componente.
    """
    ancla = '<meta charset="utf-8">'
    if bundle.count(ancla) != 1:
        raise BundleInvalido(
            f"No se encontro un unico {ancla} en el <head> del bundle "
            "para inyectar el runtime."
        )
    return bundle.replace(ancla, f"{ancla}\n<script>\n{js}\n</script>", 1)


# --- Compresion de espaciados en mobile --------------------------------------
#
# Claude Design escribe casi todo el espaciado como clamp(min, Xvw, max). Un
# clamp solo usa su minimo cuando Xvw queda por debajo, asi que bajar el minimo
# comprime las pantallas angostas y no toca las anchas: en una pagina tipica, a
# 390px manda el minimo en casi todos los clamp y a 1280px en ninguno.
#
# Es preferible a un @media con !important: no pelea contra los estilos inline
# del diseno, y la version de escritorio queda igual por construccion, no por
# haber acertado los selectores.

CLAMP = r"clamp\(\s*(\d+)px\s*,\s*([\d.]+)vw\s*,\s*(\d+)px\s*\)"

# Una declaracion "prop: valor" cuyo valor contiene al menos un clamp().
DECL_CLAMP = re.compile(
    r"(?P<prop>[a-z-]+)\s*:\s*(?P<val>[^;\"]*?clamp\([^)]*\)[^;\"]*?)(?=[;\"])"
)


def _escalar(texto, factor, piso):
    def r(m):
        minimo, vw, maximo = int(m.group(1)), m.group(2), int(m.group(3))
        return f"clamp({max(piso, round(minimo * factor))}px,{vw}vw,{maximo}px)"

    return re.sub(CLAMP, r, texto)


def comprimir_clamps(reglas, piso_lateral=16):
    """Devuelve el reemplazo para usar como `nuevo` de un parche con DECL_CLAMP.

    `reglas` es {propiedad: (factor, piso)}. Las propiedades que no esten quedan
    intactas.

    El padding se trata por posicion: en "padding: A B", A es el alto y B es el
    margen lateral. Comprimir el alto esta bien; pegar el texto al borde de la
    pantalla, no. Por eso el lateral baja poco y nunca de `piso_lateral`.
    """

    def reemplazo(m):
        prop, val = m.group("prop"), m.group("val")
        if prop not in reglas:
            return m.group(0)
        partes = val.split()
        if prop == "padding" and len(partes) == 2:
            nuevo = f"{_escalar(partes[0], *reglas[prop])} {_escalar(partes[1], 0.85, piso_lateral)}"
        elif prop == "padding":
            # Un solo valor va tambien a los lados: manda el piso lateral.
            nuevo = _escalar(val, reglas[prop][0], piso_lateral)
        else:
            nuevo = _escalar(val, *reglas[prop])
        return f"{prop}:{nuevo}"

    return reemplazo
