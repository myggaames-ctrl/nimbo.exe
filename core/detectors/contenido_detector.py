import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ContenidoDetector:

    REDES = ["instagram", "tiktok", "facebook", "whatsapp", "fb", "ig", "tt"]

    PATTERNS_POST = [
        r"^post\s+(?:para\s+)?(?:de\s+)?(.+?)\s+(?:de\s+|sobre\s+)?(.+)$",
        r"^crea[r]?\s+post\s+(?:para\s+)?(.+?)\s+(?:de\s+|sobre\s+)?(.+)$",
        r"^genera[r]?\s+post\s+(?:para\s+)?(.+?)\s+(?:de\s+|sobre\s+)?(.+)$",
        r"^post\s+(.+)$",
    ]

    PATTERNS_PUBLICAR = [
        r"^publica[r]?\s+(?:en\s+)?(?:facebook|fb|instagram|ig)\s+(?:el\s+)?(?:video|foto|post)\s+(?:de\s+)?(.+)$",
        r"^(?:sube|comparte?)\s+(?:el\s+)?(?:video|foto)\s+(?:de\s+)?(.+?)\s+(?:en\s+)?(?:facebook|fb|instagram|ig)$",
        r"^publica[r]?\s+(?:el\s+)?video\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_VIDEO_PRODUCTO = [
        r"^(?:genera[r]?|crea[r]?|haz|hacer)\s+(?:un\s+)?video\s+(?:de\s+|para\s+|del?\s+)?(.+)$",
        r"^video\s+(?:de\s+|para\s+|del?\s+)?(.+)$",
        r"^(?:graba[r]?|filma[r]?)\s+(?:un\s+)?video\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_SCRIPT = [
        r"^script\s+(?:para\s+)?(?:video|reel)?\s*(?:de\s+|sobre\s+)?(.+)$",
        r"^guion\s+(?:para\s+)?(?:video|reel)?\s*(?:de\s+|sobre\s+)?(.+)$",
        r"^video\s+(?:de\s+|sobre\s+)?(.+)$",
        r"^reel\s+(?:de\s+|sobre\s+)?(.+)$",
    ]

    PATTERNS_CATALOGO = [
        r"^descripcion\s+(?:de\s+)?(?:catalogo\s+)?(?:de\s+|para\s+)?(.+)$",
        r"^catalogo\s+(?:de\s+)?(.+)$",
        r"^describe\s+(?:el\s+producto\s+)?(.+)$",
    ]

    PATTERNS_IDEAS = [
        r"^ideas?\s+(?:de\s+)?contenido",
        r"^que\s+(?:puedo\s+)?publicar",
        r"^sugerir?\s+(?:contenido|posts?|ideas?)",
        r"^contenido\s+(?:para\s+)?(?:esta\s+)?semana",
        r"^plan\s+(?:de\s+)?contenido",
    ]

    PATTERNS_PROGRAMACION = [
        r"^programa[r]?\s+(?:publicaciones?|posts?|contenido)",
        r"^(?:cuantas?|como)\s+(?:veces?)?\s+publicar",
        r"^horario\s+(?:de\s+)?publicaciones?",
        r"^calendario\s+(?:de\s+)?contenido",
    ]

    PATTERNS_DESCRIPCION = [
        r"^(?:agrega[r]?|edita[r]?|cambia[r]?|pon[e]?|actualiza[r]?|modifica[r]?)\s+(?:la\s+)?descripcion\s+(?:de\s+|del?\s+)?(.+)$",
        r"^descripcion\s+(?:de\s+)?(.+?)\s+es\s+(.+)$",
        r"^(?:escribe|poner|guardar)\s+descripcion\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_FOTO = [
        r"^(?:muestrame|ver?|muestra)\s+(?:la\s+)?foto\s+(?:de\s+)?(.+)$",
        r"^foto\s+(?:de\s+)?(.+)$",
        r"^imagen\s+(?:de\s+)?(.+)$",
        r"^como\s+(?:es|se\s+ve)\s+(?:el?\s+|la\s+)?(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_FOTO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "contenido.foto", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_DESCRIPCION:
            match = re.search(pattern, text)
            if match:
                grupos = match.groups()
                if len(grupos) >= 2 and grupos[1]:
                    return {"intent": "contenido.set_descripcion", "query": grupos[0].strip(), "descripcion": grupos[1].strip()}
                return {"intent": "contenido.set_descripcion", "query": grupos[0].strip(), "descripcion": ""}

        for pattern in self.PATTERNS_IDEAS:
            if re.search(pattern, text):
                return {"intent": "contenido.ideas"}

        for pattern in self.PATTERNS_PROGRAMACION:
            if re.search(pattern, text):
                return {"intent": "contenido.programacion"}

        for pattern in self.PATTERNS_PUBLICAR:
            match = re.search(pattern, text)
            if match:
                red = "facebook" if "facebook" in text or "fb" in text else "instagram" if "instagram" in text or "ig" in text else "facebook"
                return {"intent": "contenido.publicar", "query": match.group(1).strip(), "red": red}

        for pattern in self.PATTERNS_VIDEO_PRODUCTO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "contenido.video", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_SCRIPT:
            match = re.search(pattern, text)
            if match:
                return {"intent": "contenido.script", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_CATALOGO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "contenido.catalogo", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_POST:
            match = re.search(pattern, text)
            if match:
                grupos = match.groups()
                red = grupos[0].strip()
                producto = grupos[1].strip() if len(grupos) > 1 else red
                if red in self.REDES or any(r in red for r in self.REDES):
                    return {"intent": "contenido.post", "red": red, "query": producto}
                else:
                    return {"intent": "contenido.post", "red": "general", "query": red}

        return None
