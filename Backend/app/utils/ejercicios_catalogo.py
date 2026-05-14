"""
Catálogo curado de ejercicios canónicos para el editor de rutina.
Los nombres son la fuente de verdad: el frontend los muestra tal cual,
el backend los normaliza con .strip() pero NO cambia capitalización.

Agrupados por grupo muscular para mostrar en selector con secciones.
"""

EJERCICIOS_CATALOGO = {
    "Pecho": [
        "Press banca",
        "Press banca inclinado",
        "Press banca declinado",
        "Press con mancuernas",
        "Press inclinado con mancuernas",
        "Aperturas con mancuernas",
        "Cruces en polea",
        "Fondos en paralelas",
        "Flexiones",
    ],
    "Espalda": [
        "Dominadas",
        "Jalón al pecho",
        "Remo con barra",
        "Remo con mancuerna",
        "Remo en polea baja",
        "Peso muerto",
        "Peso muerto rumano",
        "Pullover con mancuerna",
        "Hiperextensiones",
    ],
    "Pierna": [
        "Sentadilla",
        "Sentadilla frontal",
        "Prensa de piernas",
        "Hack squat",
        "Extensiones de cuádriceps",
        "Curl femoral tumbado",
        "Curl femoral sentado",
        "Peso muerto rumano (pierna)",
        "Zancadas",
        "Búlgaras",
        "Elevación de gemelos de pie",
        "Elevación de gemelos sentado",
    ],
    "Hombro": [
        "Press militar",
        "Press militar con mancuernas",
        "Elevaciones laterales",
        "Elevaciones frontales",
        "Pájaros",
        "Face pull",
        "Encogimientos",
    ],
    "Brazos": [
        "Curl con barra",
        "Curl con mancuernas",
        "Curl martillo",
        "Curl en banco Scott",
        "Extensión de tríceps en polea",
        "Press francés",
        "Patada de tríceps",
        "Fondos entre bancos",
    ],
    "Core": [
        "Plancha",
        "Crunch abdominal",
        "Elevación de piernas colgado",
        "Rueda abdominal",
        "Russian twist",
    ],
}


def get_catalogo() -> dict:
    """Devuelve el catálogo completo como dict {grupo: [ejercicios]}."""
    return EJERCICIOS_CATALOGO


def get_todos_los_nombres() -> list[str]:
    """Lista plana con todos los nombres de ejercicios. Útil para validación."""
    nombres = []
    for ejercicios in EJERCICIOS_CATALOGO.values():
        nombres.extend(ejercicios)
    return nombres
