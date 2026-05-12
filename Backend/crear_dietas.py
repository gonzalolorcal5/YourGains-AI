import json
import os
from pathlib import Path
import random

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent / "app" / "utils" / "dietas_predeterminadas"
os.makedirs(BASE_DIR, exist_ok=True)

OBJETIVOS = ["volumen", "definicion", "mantenimiento", "recomposicion"]
KCAL_RANGOS = [1600, 1800, 2000, 2200, 2500, 2800, 3200, 3600]
RESTRICCIONES = ["ninguna", "vegano", "vegetariano", "sin_lactosa", "sin_gluten", "sin_frutos_secos", "sin_pescado", "sin_brocoli"]

# === LA MEGA BIBLIOTECA: 100 PLATOS BASE ===
ALIMENTOS_BASE = {
    "desayuno": [
        [{"nombre": "Avena", "g_per_100k": 26}, {"nombre": "Leche semidesnatada", "g_per_100k": 220}, {"nombre": "Plátano", "g_per_100k": 112}],
        [{"nombre": "Huevos revueltos", "g_per_100k": 65}, {"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Aguacate", "g_per_100k": 60}],
        [{"nombre": "Yogur griego natural", "g_per_100k": 100}, {"nombre": "Nueces", "g_per_100k": 16}, {"nombre": "Miel", "g_per_100k": 30}],
        [{"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Pechuga de pavo", "g_per_100k": 90}, {"nombre": "Aceite de oliva virgen extra", "g_per_100k": 11}],
        [{"nombre": "Harina de avena", "g_per_100k": 25}, {"nombre": "Claras de huevo", "g_per_100k": 200}, {"nombre": "Arándanos", "g_per_100k": 175}],
        [{"nombre": "Proteína Whey", "g_per_100k": 25}, {"nombre": "Bebida de almendras", "g_per_100k": 400}, {"nombre": "Crema de cacahuete", "g_per_100k": 17}],
        [{"nombre": "Avena", "g_per_100k": 26}, {"nombre": "Huevo cocido", "g_per_100k": 65}, {"nombre": "Espinacas baby", "g_per_100k": 400}],
        [{"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Queso fresco batido", "g_per_100k": 140}, {"nombre": "Tomate natural rallado", "g_per_100k": 500}],
        [{"nombre": "Requesón desnatado", "g_per_100k": 140}, {"nombre": "Almendras", "g_per_100k": 16}, {"nombre": "Manzana", "g_per_100k": 190}],
        [{"nombre": "Huevos", "g_per_100k": 65}, {"nombre": "Jamón cocido", "g_per_100k": 90}, {"nombre": "Tomate", "g_per_100k": 500}],
        [{"nombre": "Tortitas de avena", "g_per_100k": 40}, {"nombre": "Sirope sin azúcar", "g_per_100k": 100}, {"nombre": "Fresas", "g_per_100k": 300}],
        [{"nombre": "Kéfir", "g_per_100k": 150}, {"nombre": "Copos de maíz", "g_per_100k": 25}, {"nombre": "Semillas de chía", "g_per_100k": 20}],
        [{"nombre": "Pan de centeno", "g_per_100k": 40}, {"nombre": "Salmón ahumado", "g_per_100k": 50}, {"nombre": "Queso crema light", "g_per_100k": 60}],
        [{"nombre": "Crema de arroz", "g_per_100k": 28}, {"nombre": "Proteína Whey", "g_per_100k": 25}, {"nombre": "Canela", "g_per_100k": 100}],
        [{"nombre": "Tostadas de arroz", "g_per_100k": 26}, {"nombre": "Atún al natural", "g_per_100k": 90}, {"nombre": "Pimientos asados", "g_per_100k": 300}],
        [{"nombre": "Leche semidesnatada", "g_per_100k": 220}, {"nombre": "Cereales integrales", "g_per_100k": 25}, {"nombre": "Kiwi", "g_per_100k": 160}],
        [{"nombre": "Revuelto de claras", "g_per_100k": 200}, {"nombre": "Champiñones", "g_per_100k": 450}, {"nombre": "Pan integral", "g_per_100k": 40}],
        [{"nombre": "Batido de frutas (Plátano/Fresa)", "g_per_100k": 200}, {"nombre": "Avena", "g_per_100k": 26}, {"nombre": "Proteína Whey", "g_per_100k": 25}],
        [{"nombre": "Pan de espelta", "g_per_100k": 40}, {"nombre": "Huevo a la plancha", "g_per_100k": 65}, {"nombre": "Aguacate", "g_per_100k": 60}],
        [{"nombre": "Porridge de avena", "g_per_100k": 26}, {"nombre": "Leche semidesnatada", "g_per_100k": 220}, {"nombre": "Crema de almendras", "g_per_100k": 17}]
    ],
    "comida": [
        [{"nombre": "Arroz blanco", "g_per_100k": 75}, {"nombre": "Pechuga de pollo", "g_per_100k": 60}, {"nombre": "Brócoli", "g_per_100k": 280}],
        [{"nombre": "Pasta integral", "g_per_100k": 70}, {"nombre": "Ternera magra", "g_per_100k": 40}, {"nombre": "Ensalada mixta", "g_per_100k": 500}],
        [{"nombre": "Lentejas cocidas", "g_per_100k": 86}, {"nombre": "Patata cocida", "g_per_100k": 116}, {"nombre": "Zanahoria", "g_per_100k": 240}],
        [{"nombre": "Garbanzos", "g_per_100k": 60}, {"nombre": "Atún al natural", "g_per_100k": 90}, {"nombre": "Tomate triturado", "g_per_100k": 200}],
        [{"nombre": "Quinoa", "g_per_100k": 26}, {"nombre": "Pavo a la plancha", "g_per_100k": 90}, {"nombre": "Calabacín", "g_per_100k": 600}],
        [{"nombre": "Macarrones", "g_per_100k": 28}, {"nombre": "Carne picada de pollo", "g_per_100k": 65}, {"nombre": "Champiñones", "g_per_100k": 450}],
        [{"nombre": "Arroz integral", "g_per_100k": 28}, {"nombre": "Lomo de cerdo magro", "g_per_100k": 70}, {"nombre": "Pimientos", "g_per_100k": 350}],
        [{"nombre": "Cous cous", "g_per_100k": 26}, {"nombre": "Pechuga de pollo", "g_per_100k": 60}, {"nombre": "Berenjena asada", "g_per_100k": 400}],
        [{"nombre": "Alubias blancas", "g_per_100k": 70}, {"nombre": "Huevo cocido", "g_per_100k": 65}, {"nombre": "Espinacas", "g_per_100k": 400}],
        [{"nombre": "Fideos de arroz", "g_per_100k": 27}, {"nombre": "Tiras de ternera", "g_per_100k": 50}, {"nombre": "Cebolla y zanahoria salteadas", "g_per_100k": 250}],
        [{"nombre": "Ñoquis de patata", "g_per_100k": 60}, {"nombre": "Pechuga de pavo", "g_per_100k": 90}, {"nombre": "Salsa de tomate casera", "g_per_100k": 250}],
        [{"nombre": "Boniato al horno", "g_per_100k": 115}, {"nombre": "Salmón al horno", "g_per_100k": 50}, {"nombre": "Espárragos trigueros", "g_per_100k": 450}],
        [{"nombre": "Guisantes", "g_per_100k": 120}, {"nombre": "Jamón serrano en tacos", "g_per_100k": 60}, {"nombre": "Huevo poché", "g_per_100k": 65}],
        [{"nombre": "Pasta de lentejas rojas", "g_per_100k": 28}, {"nombre": "Gambas peladas", "g_per_100k": 120}, {"nombre": "Ajo y perejil", "g_per_100k": 200}],
        [{"nombre": "Tortitas de trigo (Fajitas)", "g_per_100k": 35}, {"nombre": "Tiras de pollo", "g_per_100k": 60}, {"nombre": "Pimiento rojo y verde", "g_per_100k": 350}],
        [{"nombre": "Ensalada de pasta", "g_per_100k": 28}, {"nombre": "Atún y huevo duro", "g_per_100k": 70}, {"nombre": "Aceitunas y tomate", "g_per_100k": 200}],
        [{"nombre": "Arroz basmati", "g_per_100k": 28}, {"nombre": "Curry de pollo", "g_per_100k": 70}, {"nombre": "Leche de coco light", "g_per_100k": 150}],
        [{"nombre": "Puré de patata", "g_per_100k": 116}, {"nombre": "Albóndigas de ternera", "g_per_100k": 55}, {"nombre": "Guisantes", "g_per_100k": 120}],
        [{"nombre": "Trigo sarraceno", "g_per_100k": 28}, {"nombre": "Pechuga de pavo asada", "g_per_100k": 90}, {"nombre": "Calabaza asada", "g_per_100k": 300}],
        [{"nombre": "Edamame", "g_per_100k": 80}, {"nombre": "Arroz para sushi", "g_per_100k": 75}, {"nombre": "Salmón crudo (Poke)", "g_per_100k": 50}]
    ],
    "cena": [
        [{"nombre": "Salmón a la plancha", "g_per_100k": 50}, {"nombre": "Patata asada", "g_per_100k": 116}, {"nombre": "Espárragos", "g_per_100k": 450}],
        [{"nombre": "Merluza", "g_per_100k": 110}, {"nombre": "Boniato", "g_per_100k": 115}, {"nombre": "Calabacín", "g_per_100k": 500}],
        [{"nombre": "Pechuga de pollo", "g_per_100k": 60}, {"nombre": "Ensalada verde", "g_per_100k": 500}, {"nombre": "Aceite de oliva virgen extra", "g_per_100k": 11}],
        [{"nombre": "Huevos", "g_per_100k": 65}, {"nombre": "Patata cocida", "g_per_100k": 116}, {"nombre": "Cebolla", "g_per_100k": 250}],
        [{"nombre": "Bacalao", "g_per_100k": 120}, {"nombre": "Pimientos asados", "g_per_100k": 300}, {"nombre": "Pan integral", "g_per_100k": 40}],
        [{"nombre": "Hamburguesa de pollo casera", "g_per_100k": 70}, {"nombre": "Pan de hamburguesa", "g_per_100k": 35}, {"nombre": "Tomate y lechuga", "g_per_100k": 400}],
        [{"nombre": "Queso cottage", "g_per_100k": 100}, {"nombre": "Salmón ahumado", "g_per_100k": 50}, {"nombre": "Tostadas integrales", "g_per_100k": 25}],
        [{"nombre": "Pavo al horno", "g_per_100k": 90}, {"nombre": "Puré de patata", "g_per_100k": 116}, {"nombre": "Judías verdes", "g_per_100k": 300}],
        [{"nombre": "Dorada al horno", "g_per_100k": 100}, {"nombre": "Patata panadera", "g_per_100k": 116}, {"nombre": "Champiñones al ajillo", "g_per_100k": 200}],
        [{"nombre": "Carne picada de pollo", "g_per_100k": 65}, {"nombre": "Fideos de calabacín", "g_per_100k": 500}, {"nombre": "Salsa de soja y sésamo", "g_per_100k": 20}],
        [{"nombre": "Tortilla francesa", "g_per_100k": 65}, {"nombre": "Queso tierno", "g_per_100k": 30}, {"nombre": "Ensalada de canónigos", "g_per_100k": 500}],
        [{"nombre": "Sepia a la plancha", "g_per_100k": 120}, {"nombre": "Arroz blanco", "g_per_100k": 75}, {"nombre": "Ajo y perejil", "g_per_100k": 200}],
        [{"nombre": "Pechuga de pavo", "g_per_100k": 90}, {"nombre": "Crema de calabaza", "g_per_100k": 250}, {"nombre": "Picatostes integrales", "g_per_100k": 25}],
        [{"nombre": "Atún a la plancha", "g_per_100k": 70}, {"nombre": "Quinoa", "g_per_100k": 26}, {"nombre": "Ensalada de algas wakame", "g_per_100k": 200}],
        [{"nombre": "Pizza con base de coliflor", "g_per_100k": 150}, {"nombre": "Mozzarella light", "g_per_100k": 60}, {"nombre": "Tomate frito sin azúcar", "g_per_100k": 250}],
        [{"nombre": "Pechuga de pollo asada", "g_per_100k": 60}, {"nombre": "Gazpacho", "g_per_100k": 200}, {"nombre": "Huevo duro picado", "g_per_100k": 65}],
        [{"nombre": "Lubina al horno", "g_per_100k": 100}, {"nombre": "Patatas baby", "g_per_100k": 116}, {"nombre": "Tomates cherry", "g_per_100k": 500}],
        [{"nombre": "Revuelto de gulas", "g_per_100k": 65}, {"nombre": "Gambas", "g_per_100k": 120}, {"nombre": "Pan tostado", "g_per_100k": 40}],
        [{"nombre": "Filete de ternera fino", "g_per_100k": 50}, {"nombre": "Boniato frito (Airfryer)", "g_per_100k": 115}, {"nombre": "Pimientos de Padrón", "g_per_100k": 200}],
        [{"nombre": "Sopa de fideos", "g_per_100k": 150}, {"nombre": "Pollo desmenuzado", "g_per_100k": 60}, {"nombre": "Huevo cocido", "g_per_100k": 65}]
    ],
    "almuerzos": [
        [{"nombre": "Manzana", "g_per_100k": 190}, {"nombre": "Nueces", "g_per_100k": 16}, {"nombre": "Proteína Whey", "g_per_100k": 25}],
        [{"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Pechuga de pavo", "g_per_100k": 90}, {"nombre": "Tomate", "g_per_100k": 500}],
        [{"nombre": "Yogur griego", "g_per_100k": 100}, {"nombre": "Avena", "g_per_100k": 26}, {"nombre": "Miel", "g_per_100k": 30}],
        [{"nombre": "Tortitas de arroz", "g_per_100k": 26}, {"nombre": "Crema de cacahuete", "g_per_100k": 17}, {"nombre": "Plátano", "g_per_100k": 112}],
        [{"nombre": "Kéfir", "g_per_100k": 150}, {"nombre": "Arándanos", "g_per_100k": 175}, {"nombre": "Almendras", "g_per_100k": 16}],
        [{"nombre": "Huevo cocido", "g_per_100k": 65}, {"nombre": "Pan tostado", "g_per_100k": 40}, {"nombre": "Aceite de oliva virgen extra", "g_per_100k": 11}],
        [{"nombre": "Batido de proteínas", "g_per_100k": 25}, {"nombre": "Mandarinas", "g_per_100k": 200}, {"nombre": "Anacardos", "g_per_100k": 17}],
        [{"nombre": "Queso fresco batido", "g_per_100k": 140}, {"nombre": "Semillas de chía", "g_per_100k": 20}, {"nombre": "Kiwi", "g_per_100k": 160}],
        [{"nombre": "Pan de centeno", "g_per_100k": 40}, {"nombre": "Atún al natural", "g_per_100k": 90}, {"nombre": "Pimientos", "g_per_100k": 350}],
        [{"nombre": "Barrita de proteínas (baja en azúcar)", "g_per_100k": 30}, {"nombre": "Pera", "g_per_100k": 170}, {"nombre": "Nueces de macadamia", "g_per_100k": 15}]
    ],
    "meriendas": [
        [{"nombre": "Requesón desnatado", "g_per_100k": 140}, {"nombre": "Sirope cero", "g_per_100k": 100}, {"nombre": "Canela", "g_per_100k": 100}],
        [{"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Jamón serrano magro", "g_per_100k": 60}, {"nombre": "Tomate", "g_per_100k": 500}],
        [{"nombre": "Batido de Proteína", "g_per_100k": 25}, {"nombre": "Leche semidesnatada", "g_per_100k": 220}, {"nombre": "Fresas", "g_per_100k": 300}],
        [{"nombre": "Tortitas de maíz", "g_per_100k": 26}, {"nombre": "Guacamole", "g_per_100k": 60}, {"nombre": "Pechuga de pollo (fiambre)", "g_per_100k": 90}],
        [{"nombre": "Yogur de proteínas", "g_per_100k": 120}, {"nombre": "Granola sin azúcar", "g_per_100k": 25}, {"nombre": "Frambuesas", "g_per_100k": 180}],
        [{"nombre": "Manzana asada", "g_per_100k": 190}, {"nombre": "Yogur natural", "g_per_100k": 150}, {"nombre": "Nueces", "g_per_100k": 16}],
        [{"nombre": "Bocadillo pequeño de atún", "g_per_100k": 50}, {"nombre": "Lechuga", "g_per_100k": 500}, {"nombre": "Aceitunas", "g_per_100k": 70}],
        [{"nombre": "Porridge frío (Overnight oats)", "g_per_100k": 26}, {"nombre": "Proteína Whey", "g_per_100k": 25}, {"nombre": "Plátano", "g_per_100k": 112}],
        [{"nombre": "Queso cottage", "g_per_100k": 100}, {"nombre": "Mermelada light", "g_per_100k": 60}, {"nombre": "Tostadas integrales", "g_per_100k": 25}],
        [{"nombre": "Hummus", "g_per_100k": 60}, {"nombre": "Palitos de zanahoria", "g_per_100k": 240}, {"nombre": "Pechuga de pavo", "g_per_100k": 90}]
    ],
    "pre_entreno": [
        [{"nombre": "Plátano maduro", "g_per_100k": 112}, {"nombre": "Miel", "g_per_100k": 30}, {"nombre": "Café solo", "g_per_100k": 500}],
        [{"nombre": "Crema de arroz", "g_per_100k": 28}, {"nombre": "Proteína Whey aislada", "g_per_100k": 25}, {"nombre": "Mermelada", "g_per_100k": 40}],
        [{"nombre": "Tortitas de arroz", "g_per_100k": 26}, {"nombre": "Crema de cacahuete", "g_per_100k": 17}, {"nombre": "Miel", "g_per_100k": 30}],
        [{"nombre": "Dátiles", "g_per_100k": 35}, {"nombre": "Nueces", "g_per_100k": 16}, {"nombre": "Batido de proteínas", "g_per_100k": 25}],
        [{"nombre": "Avena cocida", "g_per_100k": 26}, {"nombre": "Pasas", "g_per_100k": 30}, {"nombre": "Leche desnatada", "g_per_100k": 250}],
        [{"nombre": "Pan blanco", "g_per_100k": 35}, {"nombre": "Mermelada", "g_per_100k": 40}, {"nombre": "Queso fresco", "g_per_100k": 100}],
        [{"nombre": "Zumo de naranja natural", "g_per_100k": 200}, {"nombre": "Tostada", "g_per_100k": 40}, {"nombre": "Pavo", "g_per_100k": 90}],
        [{"nombre": "Manzana", "g_per_100k": 190}, {"nombre": "Crema de almendras", "g_per_100k": 17}, {"nombre": "Café", "g_per_100k": 500}],
        [{"nombre": "Cereales tipo Corn Flakes", "g_per_100k": 25}, {"nombre": "Leche", "g_per_100k": 220}, {"nombre": "Plátano", "g_per_100k": 112}],
        [{"nombre": "Gominolas deportivas o ositos", "g_per_100k": 30}, {"nombre": "Proteína Whey", "g_per_100k": 25}, {"nombre": "Pre-entreno líquido", "g_per_100k": 300}]
    ],
    "post_entreno": [
        [{"nombre": "Batido de Proteína Whey", "g_per_100k": 25}, {"nombre": "Plátano", "g_per_100k": 112}, {"nombre": "Cereales", "g_per_100k": 25}],
        [{"nombre": "Queso fresco batido", "g_per_100k": 140}, {"nombre": "Avena", "g_per_100k": 26}, {"nombre": "Chocolate negro 85%", "g_per_100k": 18}],
        [{"nombre": "Caseína micelar", "g_per_100k": 25}, {"nombre": "Crema de cacahuete", "g_per_100k": 17}, {"nombre": "Leche", "g_per_100k": 220}],
        [{"nombre": "Yogur griego", "g_per_100k": 100}, {"nombre": "Arándanos", "g_per_100k": 175}, {"nombre": "Almendras", "g_per_100k": 16}],
        [{"nombre": "Huevos revueltos", "g_per_100k": 65}, {"nombre": "Pan integral", "g_per_100k": 40}, {"nombre": "Aguacate", "g_per_100k": 60}],
        [{"nombre": "Requesón", "g_per_100k": 140}, {"nombre": "Miel", "g_per_100k": 30}, {"nombre": "Nueces", "g_per_100k": 16}],
        [{"nombre": "Atún al natural", "g_per_100k": 90}, {"nombre": "Tortitas de arroz", "g_per_100k": 26}, {"nombre": "Tomate", "g_per_100k": 500}],
        [{"nombre": "Pechuga de pavo", "g_per_100k": 90}, {"nombre": "Pan", "g_per_100k": 40}, {"nombre": "Queso light", "g_per_100k": 60}],
        [{"nombre": "Leche con cacao puro", "g_per_100k": 220}, {"nombre": "Pan tostado", "g_per_100k": 40}, {"nombre": "Crema de almendras", "g_per_100k": 17}],
        [{"nombre": "Puding de chía (Proteína + Chía + Leche)", "g_per_100k": 100}, {"nombre": "Fresas", "g_per_100k": 300}, {"nombre": "Sirope cero", "g_per_100k": 100}]
    ]
}

# Mega-Sustituciones para soportar los 100 platos
SUSTITUCIONES = {
    "vegano": {
        "Pechuga de pollo": "Tofu firme", "Leche semidesnatada": "Bebida de soja", "Huevos revueltos": "Revuelto de tofu", 
        "Ternera magra": "Heura", "Salmón a la plancha": "Tempeh", "Merluza": "Seitan", "Huevos": "Tofu revuelto",
        "Pechuga de pavo": "Lonchas de pavo vegano", "Yogur griego natural": "Yogur de soja", "Miel": "Sirope de agave", 
        "Claras de huevo": "Aquafaba o harina de garbanzo", "Proteína Whey": "Proteína de guisante", "Huevo cocido": "Tofu marinado",
        "Queso fresco batido": "Yogur natural de soja", "Requesón desnatado": "Tofu sedoso", "Jamón cocido": "Lonchas vegetales", 
        "Atún al natural": "Heura en trozos", "Pavo a la plancha": "Tempeh a la plancha", "Carne picada de pollo": "Soja texturizada",
        "Lomo de cerdo magro": "Seitan en tiras", "Tiras de ternera": "Heura en tiras", "Bacalao": "Tempeh marinado", 
        "Hamburguesa de pollo casera": "Hamburguesa vegetal", "Queso cottage": "Tofu desmigado", "Salmón ahumado": "Zanahoria marinada (salmón vegano)",
        "Pavo al horno": "Tofu al horno", "Dorada al horno": "Seitan asado", "Leche": "Bebida de avena", "Yogur griego": "Yogur de coco",
        "Kéfir": "Kéfir de agua o soja", "Queso crema light": "Queso crema vegano", "Revuelto de claras": "Revuelto de tofu",
        "Huevo a la plancha": "Filete de tofu", "Salmón al horno": "Tempeh asado", "Jamón serrano en tacos": "Tacos de soja texturizada",
        "Gambas peladas": "Champiñones salteados", "Tiras de pollo": "Tiras de Heura", "Albóndigas de ternera": "Albóndigas vegetales",
        "Pechuga de pavo asada": "Seitan asado", "Salmón crudo (Poke)": "Edamame extra", "Tortilla francesa": "Tortilla de harina de garbanzo",
        "Queso tierno": "Queso vegano", "Sepia a la plancha": "Setas ostra a la plancha", "Atún a la plancha": "Tofu a la plancha",
        "Mozzarella light": "Mozzarella vegana", "Huevo duro picado": "Tofu picado", "Lubina al horno": "Tempeh al horno",
        "Revuelto de gulas": "Revuelto de calabacín", "Gambas": "Heura", "Filete de ternera fino": "Filete de seitán",
        "Pollo desmenuzado": "Jackfruit", "Batido de Proteína": "Batido de Proteína Vegetal", "Queso fresco": "Tofu firme",
        "Caseína micelar": "Proteína de cáñamo o arroz", "Jamón serrano magro": "Lonchas veganas", "Pechuga de pollo (fiambre)": "Fiambre vegetal"
    },
    "vegetariano": {
        "Pechuga de pollo": "Huevos duros", "Ternera magra": "Queso fresco batido", "Salmón a la plancha": "Hamburguesa vegetal", 
        "Merluza": "Heura", "Pechuga de pavo": "Queso havarti", "Atún al natural": "Huevo cocido", "Pavo a la plancha": "Tofu a la plancha", 
        "Carne picada de pollo": "Soja texturizada", "Lomo de cerdo magro": "Seitan", "Tiras de ternera": "Heura",
        "Bacalao": "Queso halloumi", "Hamburguesa de pollo casera": "Hamburguesa de lentejas", "Salmón ahumado": "Huevo poché", 
        "Pavo al horno": "Tempeh al horno", "Dorada al horno": "Heura asada", "Salmón al horno": "Tortilla francesa", 
        "Jamón serrano en tacos": "Dados de queso", "Gambas peladas": "Huevo duro", "Tiras de pollo": "Tiras de soja", 
        "Albóndigas de ternera": "Albóndigas de soja", "Pechuga de pavo asada": "Queso plancha", "Salmón crudo (Poke)": "Huevo poché",
        "Sepia a la plancha": "Setas a la plancha", "Atún a la plancha": "Hamburguesa vegetal", "Lubina al horno": "Berenjena rellena",
        "Revuelto de gulas": "Revuelto de ajetes", "Gambas": "Champiñones", "Filete de ternera fino": "Tortilla francesa",
        "Pollo desmenuzado": "Huevo rallado", "Jamón serrano magro": "Queso curado", "Pechuga de pollo (fiambre)": "Queso en lonchas"
    },
    "sin_lactosa": {
        "Leche semidesnatada": "Leche sin lactosa", "Yogur griego natural": "Yogur sin lactosa", "Proteína Whey": "Proteína aislada (Isolate) o Vegetal", 
        "Queso fresco batido": "Queso fresco sin lactosa", "Requesón desnatado": "Requesón sin lactosa", "Queso cottage": "Queso sin lactosa",
        "Kéfir": "Kéfir de agua", "Queso crema light": "Queso crema sin lactosa", "Leche": "Leche sin lactosa", "Yogur griego": "Yogur sin lactosa",
        "Queso tierno": "Queso tierno sin lactosa", "Mozzarella light": "Mozzarella sin lactosa", "Queso fresco": "Queso fresco sin lactosa",
        "Caseína micelar": "Proteína de ternera o huevo", "Yogur de proteínas": "Yogur de soja", "Yogur natural": "Yogur sin lactosa",
        "Queso light": "Queso en lonchas sin lactosa"
    },
    "sin_gluten": {
        "Avena": "Copos de avena sin gluten", "Pan integral": "Pan sin gluten", "Pasta integral": "Pasta de arroz o maíz", 
        "Harina de avena": "Harina de avena sin gluten", "Macarrones": "Macarrones de sarraceno", "Cous cous": "Quinoa", 
        "Pan de hamburguesa": "Pan de hamburguesa sin gluten", "Tostadas integrales": "Tostadas de arroz",
        "Tortitas de avena": "Tortitas de harina de arroz", "Copos de maíz": "Copos de maíz sin gluten", "Pan de centeno": "Pan sin gluten",
        "Cereales integrales": "Cereales sin gluten", "Pan de espelta": "Pan de trigo sarraceno", "Porridge de avena": "Porridge de arroz",
        "Ñoquis de patata": "Ñoquis sin gluten", "Pasta de lentejas rojas": "Pasta de arroz", "Tortitas de trigo (Fajitas)": "Tortitas de maíz",
        "Ensalada de pasta": "Ensalada de arroz", "Trigo sarraceno": "Quinoa", "Pan tostado": "Pan tostado sin gluten",
        "Sopa de fideos": "Sopa de arroz", "Barrita de proteínas (baja en azúcar)": "Barrita de proteínas sin gluten",
        "Bocadillo pequeño de atún": "Bocadillo de pan sin gluten", "Pan blanco": "Pan blanco sin gluten",
        "Cereales tipo Corn Flakes": "Corn Flakes sin gluten", "Cereales": "Cereales sin gluten", "Pan": "Pan sin gluten"
    },
    "sin_pescado": {
        "Salmón a la plancha": "Pechuga de pavo", "Merluza": "Pollo desmenuzado", "Atún al natural": "Huevo cocido", "Bacalao": "Pechuga de pollo",
        "Salmón ahumado": "Jamón serrano magro", "Dorada al horno": "Muslo de pollo deshuesado", "Salmón al horno": "Pechuga de pollo asada",
        "Gambas peladas": "Tiras de pavo", "Salmón crudo (Poke)": "Tofu marinado", "Sepia a la plancha": "Pechuga a la plancha",
        "Atún a la plancha": "Lomo de cerdo", "Lubina al horno": "Pavo al horno", "Revuelto de gulas": "Revuelto de champiñones",
        "Gambas": "Tacos de pavo", "Bocadillo pequeño de atún": "Bocadillo pequeño de pollo"
    },
    "sin_frutos_secos": {
        "Crema de cacahuete": "Aceite de oliva virgen extra", "Nueces": "Semillas de chía", "Almendras": "Semillas de calabaza",
        "Bebida de almendras": "Leche semidesnatada", "Crema de almendras": "Aceite de coco o mantequilla", "Anacardos": "Pipas de girasol",
        "Nueces de macadamia": "Semillas de lino"
    },
    "sin_brocoli": {
        "Brócoli": "Coliflor"
    }
}

def generar_macros(kcal, objetivo):
    if objetivo == "volumen":
        return {"proteinas_g": int(kcal * 0.25 / 4), "carbohidratos_g": int(kcal * 0.50 / 4), "grasas_g": int(kcal * 0.25 / 9)}
    elif objetivo == "definicion":
        return {"proteinas_g": int(kcal * 0.35 / 4), "carbohidratos_g": int(kcal * 0.35 / 4), "grasas_g": int(kcal * 0.30 / 9)}
    else: 
        return {"proteinas_g": int(kcal * 0.30 / 4), "carbohidratos_g": int(kcal * 0.40 / 4), "grasas_g": int(kcal * 0.30 / 9)}

def adaptar_alimentos(comida_base, restriccion, kcal_comida):
    alimentos_adaptados = []
    kcal_por_ingrediente = kcal_comida / len(comida_base)
    for ing in comida_base:
        nombre = ing["nombre"]
        if restriccion in SUSTITUCIONES and nombre in SUSTITUCIONES[restriccion]:
            nombre = SUSTITUCIONES[restriccion][nombre]
        cantidad_g = int((kcal_por_ingrediente / 100) * ing.get("g_per_100k", 100))
        alimentos_adaptados.append({
            "nombre": nombre,
            "cantidad": f"{cantidad_g}g" if "Leche" not in nombre and "Bebida" not in nombre and "Zumo" not in nombre else f"{cantidad_g}ml"
        })
    return alimentos_adaptados

contador = 0
for objetivo in OBJETIVOS:
    for kcal in KCAL_RANGOS:
        if objetivo == "definicion" and kcal > 2800: continue
        if objetivo == "volumen" and kcal < 2200: continue
        
        for restriccion in RESTRICCIONES:
            macros_totales = generar_macros(kcal, objetivo)
            
            kcal_desayuno = int(kcal * 0.25)
            kcal_snack1 = int(kcal * 0.15)
            kcal_comida = int(kcal * 0.30)
            kcal_snack2 = int(kcal * 0.10)
            kcal_cena = int(kcal * 0.20)
            
            tipo_snack1 = random.choice(["almuerzos", "pre_entreno"])
            tipo_snack2 = random.choice(["meriendas", "post_entreno"])
            nombre_snack1 = "Media Mañana / Pre-entreno" if tipo_snack1 == "pre_entreno" else "Media Mañana"
            nombre_snack2 = "Merienda / Post-entreno" if tipo_snack2 == "post_entreno" else "Merienda"
            
            dieta = {
                "id": f"{objetivo}_{kcal}_{restriccion}",
                "objetivo": objetivo,
                "kcal_objetivo": kcal,
                "restriccion": restriccion,
                "macros": macros_totales,
                "comidas": [
                    {
                        "nombre": "Desayuno", "kcal": kcal_desayuno,
                        "alimentos": adaptar_alimentos(random.choice(ALIMENTOS_BASE["desayuno"]), restriccion, kcal_desayuno),
                        "macros": generar_macros(kcal_desayuno, objetivo)
                    },
                    {
                        "nombre": nombre_snack1, "kcal": kcal_snack1,
                        "alimentos": adaptar_alimentos(random.choice(ALIMENTOS_BASE[tipo_snack1]), restriccion, kcal_snack1),
                        "macros": generar_macros(kcal_snack1, objetivo)
                    },
                    {
                        "nombre": "Almuerzo / Comida", "kcal": kcal_comida,
                        "alimentos": adaptar_alimentos(random.choice(ALIMENTOS_BASE["comida"]), restriccion, kcal_comida),
                        "macros": generar_macros(kcal_comida, objetivo)
                    },
                    {
                        "nombre": nombre_snack2, "kcal": kcal_snack2,
                        "alimentos": adaptar_alimentos(random.choice(ALIMENTOS_BASE[tipo_snack2]), restriccion, kcal_snack2),
                        "macros": generar_macros(kcal_snack2, objetivo)
                    },
                    {
                        "nombre": "Cena", "kcal": kcal_cena,
                        "alimentos": adaptar_alimentos(random.choice(ALIMENTOS_BASE["cena"]), restriccion, kcal_cena),
                        "macros": generar_macros(kcal_cena, objetivo)
                    }
                ],
                "consejos": [
                    "Bebe al menos 2.5L de agua al día.",
                    "Puedes cambiar las especias al gusto, no suman calorías.",
                    f"Plan ajustado para requerimientos: {restriccion.replace('_', ' ').capitalize()}."
                ],
                "locked": False,
                "version": "2.1.0"
            }
            
            filename = f"{objetivo}_{kcal}kcal_{restriccion}.json"
            filepath = BASE_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([dieta], f, ensure_ascii=False, indent=2)
            contador += 1

print(f"✅ ¡Éxito! Se han generado {contador} dietas JSON de 5 comidas en app/utils/dietas_predeterminadas/")