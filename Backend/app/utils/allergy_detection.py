#!/usr/bin/env python3
"""
Sistema de detección y validación de alergias alimentarias
"""

import re
import logging
from typing import List, Dict, Any, Tuple
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Diccionario de alergias comunes y sus variaciones
ALLERGY_DATABASE = {
    "nueces": ["nueces", "nuez", "nuez de brasil", "nuez pecan", "nuez macadamia", "pistachos", "almendras", "avellanas", "anacardos", "castañas"],
    "cacahuetes": ["cacahuetes", "cacahuete", "maní", "mani", "mantequilla de cacahuete", "aceite de cacahuete"],
    "lacteos": ["leche", "lacteos", "lácteos", "queso", "yogur", "yoghurt", "mantequilla", "nata", "crema"],
    "huevos": ["huevos", "huevo", "clara de huevo", "yema de huevo", "ovoproductos"],
    "soja": ["soja", "soya", "tofu", "tempeh", "miso", "salsa de soja", "aceite de soja"],
    "gluten": ["gluten", "trigo", "cebada", "centeno", "avena", "pan", "pasta", "harina"],
    "mariscos": ["mariscos", "camarones", "langostinos", "cangrejo", "langosta", "ostras", "mejillones"],
    "pescado": ["pescado", "atun", "atún", "salmón", "salmon", "merluza", "bacalao", "anchoas"],
    "frutos secos": ["frutos secos", "frutossecos", "frutos-secos"],
    "semillas": ["semillas", "semilla", "sésamo", "sesamo", "chia", "chía", "lino", "girasol"]
}

def detect_typo_in_allergies(user_input: str) -> Tuple[List[str], List[str]]:
    """
    Detecta errores tipográficos en alergias y sugiere correcciones
    
    Args:
        user_input: Texto del usuario (ej: "alergia a nuecesdd")
        
    Returns:
        Tuple de (alergias_detectadas, sugerencias_correccion)
    """
    alergias_detectadas = []
    sugerencias_correccion = []
    
    # Buscar patrones como "alergia a X", "soy alérgico a X", etc.
    allergy_patterns = [
        r'alergia\s+a\s+([^,\n]+)',
        r'alérgico\s+a\s+([^,\n]+)',
        r'alérgica\s+a\s+([^,\n]+)',
        r'soy\s+alérgico\s+a\s+([^,\n]+)',
        r'soy\s+alérgica\s+a\s+([^,\n]+)',
        r'no\s+puedo\s+comer\s+([^,\n]+)',
        r'evitar\s+([^,\n]+)',
        r'restringir\s+([^,\n]+)'
    ]
    
    for pattern in allergy_patterns:
        matches = re.findall(pattern, user_input.lower())
        for match in matches:
            # Limpiar el match
            allergy_text = match.strip()
            
            # Buscar coincidencias exactas en la base de datos
            exact_match = find_exact_allergy_match(allergy_text)
            if exact_match:
                alergias_detectadas.append(exact_match)
            else:
                # Buscar coincidencias aproximadas (errores tipográficos)
                suggestions = find_typo_suggestions(allergy_text)
                if suggestions:
                    sugerencias_correccion.append({
                        "original": allergy_text,
                        "suggestions": suggestions
                    })
    
    return alergias_detectadas, sugerencias_correccion

def find_exact_allergy_match(text: str) -> str:
    """Busca coincidencias exactas en la base de datos de alergias"""
    text_lower = text.lower().strip()
    
    for allergy_type, variations in ALLERGY_DATABASE.items():
        for variation in variations:
            if variation.lower() == text_lower:
                return allergy_type
            # También buscar si el texto contiene la variación
            if variation.lower() in text_lower or text_lower in variation.lower():
                return allergy_type
    
    return None

def find_typo_suggestions(text: str) -> List[str]:
    """Encuentra sugerencias para errores tipográficos"""
    text_lower = text.lower().strip()
    suggestions = []
    
    # Recopilar todas las variaciones de alergias
    all_variations = []
    for allergy_type, variations in ALLERGY_DATABASE.items():
        all_variations.extend(variations)
    
    # Buscar coincidencias aproximadas
    close_matches = get_close_matches(text_lower, all_variations, n=3, cutoff=0.6)
    
    if close_matches:
        # Mapear las variaciones de vuelta a los tipos de alergia
        for match in close_matches:
            for allergy_type, variations in ALLERGY_DATABASE.items():
                if match in variations:
                    if allergy_type not in suggestions:
                        suggestions.append(allergy_type)
    
    return suggestions

def validate_food_against_allergies(food_item: str, allergies: List[str]) -> Dict[str, Any]:
    """
    Valida si un alimento contiene alguna alergia
    
    Args:
        food_item: Alimento a validar
        allergies: Lista de alergias del usuario
        
    Returns:
        Dict con resultado de validación
    """
    food_lower = food_item.lower()
    conflicts = []
    
    for allergy in allergies:
        if allergy in ALLERGY_DATABASE:
            variations = ALLERGY_DATABASE[allergy]
            for variation in variations:
                if variation.lower() in food_lower:
                    conflicts.append({
                        "allergy": allergy,
                        "variation": variation,
                        "food_item": food_item
                    })
    
    return {
        "is_safe": len(conflicts) == 0,
        "conflicts": conflicts,
        "safe": len(conflicts) == 0
    }

def get_allergy_safe_alternatives(original_food: str, allergies: List[str]) -> List[str]:
    """
    Obtiene alternativas seguras para un alimento que contiene alergias
    
    Args:
        original_food: Alimento original
        allergies: Lista de alergias del usuario
        
    Returns:
        Lista de alternativas seguras
    """
    # Diccionario de alternativas por tipo de alergia
    alternatives = {
        "nueces": ["semillas de girasol", "semillas de calabaza", "coco rallado", "cacao en polvo"],
        "cacahuetes": ["mantequilla de almendras", "mantequilla de girasol", "tahini", "aguacate"],
        "lacteos": ["leche de almendras", "leche de avena", "leche de coco", "yogur de soja"],
        "huevos": ["tofu", "semillas de chia", "aquafaba", "harina de garbanzo"],
        "gluten": ["arroz", "quinoa", "avena sin gluten", "pasta de arroz", "pan sin gluten"],
        "soja": ["tofu de garbanzo", "tempeh de guisantes", "proteína de cáñamo"],
        "mariscos": ["tofu", "tempeh", "setas", "proteína vegetal"],
        "pescado": ["tofu", "tempeh", "legumbres", "setas", "proteína vegetal"]
    }
    
    safe_alternatives = []
    
    # Buscar alternativas para cada alergia presente
    for allergy in allergies:
        if allergy in alternatives:
            safe_alternatives.extend(alternatives[allergy])
    
    # Eliminar duplicados y filtrar por el tipo de alimento
    safe_alternatives = list(set(safe_alternatives))
    
    # Filtrar alternativas que también podrían tener alergias
    filtered_alternatives = []
    for alt in safe_alternatives:
        validation = validate_food_against_allergies(alt, allergies)
        if validation["is_safe"]:
            filtered_alternatives.append(alt)
    
    return filtered_alternatives[:5]  # Máximo 5 alternativas

def process_user_allergies(user_input: str, current_allergies: List[str] = None) -> Dict[str, Any]:
    """
    Procesa las alergias del usuario y detecta errores tipográficos
    
    Args:
        user_input: Input del usuario
        current_allergies: Alergias actuales del usuario
        
    Returns:
        Dict con alergias detectadas, sugerencias y validación
    """
    if current_allergies is None:
        current_allergies = []
    
    # Detectar alergias en el input
    detected_allergies, typo_suggestions = detect_typo_in_allergies(user_input)
    
    # Combinar alergias actuales con las nuevas
    all_allergies = list(set(current_allergies + detected_allergies))
    
    result = {
        "detected_allergies": detected_allergies,
        "all_allergies": all_allergies,
        "typo_suggestions": typo_suggestions,
        "has_typos": len(typo_suggestions) > 0,
        "needs_confirmation": len(typo_suggestions) > 0
    }
    
    return result

# Función de utilidad para logging
def log_allergy_detection(user_input: str, result: Dict[str, Any]):
    """Log de detección de alergias"""
    logger.info(f"🔍 Detección de alergias en: '{user_input}'")
    logger.info(f"✅ Alergias detectadas: {result['detected_allergies']}")
    
    if result['has_typos']:
        logger.warning(f"⚠️ Errores tipográficos detectados:")
        for suggestion in result['typo_suggestions']:
            logger.warning(f"  '{suggestion['original']}' → {suggestion['suggestions']}")
    else:
        logger.info("✅ Sin errores tipográficos detectados")
