# app/routes/onboarding.py
"""
Onboarding UPSERT: sirve tanto para registro inicial (FREE) como para actualización (PREMIUM).
Patrón idempotente: buscar plan por user_id → actualizar o crear según corresponda.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from app.database import get_db
from app.models import Usuario, Plan
from app.auth_utils import get_current_user
from app.utils.gpt import generar_plan_personalizado
from app.utils.routine_templates import get_generic_plan

router = APIRouter()


class OnboardingRequest(BaseModel):
    altura: int
    peso: float
    edad: int
    sexo: str
    experiencia: str
    materiales: str
    tipo_cuerpo: str
    nivel_actividad: str
    alergias: Optional[str] = None
    restricciones_dieta: Optional[str] = None
    lesiones: Optional[str] = None
    idioma: str = "es"
    puntos_fuertes: Optional[str] = None
    puntos_debiles: Optional[str] = None
    entrenar_fuerte: bool = True
    gym_goal: str
    nutrition_goal: str
    training_frequency: int
    training_days: List[str]
    session_duration: Optional[str] = "45-60"


def _user_data_from_request(data: OnboardingRequest) -> dict:
    """Construye el diccionario user_data para GPT/templates."""
    return {
        "altura": data.altura,
        "peso": data.peso,
        "edad": data.edad,
        "sexo": data.sexo,
        "experiencia": data.experiencia,
        "materiales": data.materiales,
        "tipo_cuerpo": data.tipo_cuerpo,
        "nivel_actividad": data.nivel_actividad,
        "alergias": data.alergias or "Ninguna",
        "restricciones": data.restricciones_dieta or "Ninguna",
        "lesiones": data.lesiones or "Ninguna",
        "idioma": data.idioma,
        "puntos_fuertes": data.puntos_fuertes or "Ninguno",
        "puntos_debiles": data.puntos_debiles or "Ninguno",
        "entrenar_fuerte": data.entrenar_fuerte,
        "gym_goal": data.gym_goal,
        "nutrition_goal": data.nutrition_goal,
        "training_frequency": data.training_frequency,
        "training_days": data.training_days,
        "session_duration": data.session_duration or "45-60",
    }


def _apply_metadata(rutina_json: dict, dieta_json: dict, data: OnboardingRequest) -> None:
    """Añade metadata a rutina y dieta in-place."""
    if "metadata" not in rutina_json:
        rutina_json["metadata"] = {}
    rutina_json["metadata"].update({
        "gym_goal": data.gym_goal,
        "training_frequency": data.training_frequency,
        "training_days": data.training_days,
    })
    if "metadata" not in dieta_json:
        dieta_json["metadata"] = {}
    dieta_json["metadata"].update({"nutrition_goal": data.nutrition_goal})


def _kcal_from_dieta(dieta_json: dict, data: OnboardingRequest) -> int:
    """Obtiene kcal objetivo desde macros o nutrition_calculator."""
    macros = dieta_json.get("macros", {}) or {}
    if not isinstance(macros, dict):
        macros = {}
    if not macros:
        meta = dieta_json.get("metadata", {}).get("macros_objetivo", {})
        if meta:
            macros = {
                "proteina": meta.get("proteina", 0),
                "carbohidratos": meta.get("carbohidratos", 0),
                "grasas": meta.get("grasas", 0),
            }
    kcal = macros.get("calorias") if isinstance(macros, dict) else None
    if not kcal or kcal <= 0:
        try:
            from app.utils.nutrition_calculator import get_complete_nutrition_plan
            np = get_complete_nutrition_plan({
                "peso": data.peso, "altura": data.altura, "edad": data.edad,
                "sexo": data.sexo, "nivel_actividad": data.nivel_actividad,
            }, data.nutrition_goal)
            kcal = np.get("calorias_objetivo")
        except Exception:
            pass
    if not kcal or kcal <= 0:
        kcal = sum(m.get("kcal", 0) for m in dieta_json.get("comidas", []))
    return int(kcal) if kcal else 2200


def _build_current_routine_diet(rutina_json: dict, dieta_json: dict, data: OnboardingRequest) -> tuple:
    """Construye (current_routine_dict, current_diet_dict) para Usuario."""
    exercises = []
    if "dias" in rutina_json:
        for dia in rutina_json.get("dias", []):
            for ej in dia.get("ejercicios", []):
                exercises.append({
                    "name": ej.get("nombre", ""),
                    "sets": ej.get("series", 3),
                    "reps": ej.get("repeticiones", "10-12"),
                    "weight": "moderado",
                    "day": dia.get("dia", ""),
                })
    current_routine = {
        "exercises": exercises,
        "schedule": {},
        "created_at": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "metadata": {
            "gym_goal": data.gym_goal,
            "training_frequency": data.training_frequency,
            "training_days": data.training_days,
        },
    }
    macros = dieta_json.get("macros", {}) or {}
    if not macros and dieta_json.get("metadata", {}).get("macros_objetivo"):
        macros = dieta_json["metadata"]["macros_objetivo"]
    current_diet = {
        "meals": dieta_json.get("comidas", []),
        "total_kcal": _kcal_from_dieta(dieta_json, data),
        "macros": macros,
        "created_at": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "metadata": {"nutrition_goal": data.nutrition_goal},
    }
    return current_routine, current_diet


def _plan_physical_fields(data: OnboardingRequest) -> dict:
    """Campos físicos/objetivos para actualizar en Plan (sin rutina/dieta/motivacion)."""
    return {
        "altura": data.altura,
        "peso": str(int(data.peso)),
        "edad": data.edad,
        "sexo": data.sexo,
        "experiencia": data.experiencia,
        "objetivo": f"{data.gym_goal} + {data.nutrition_goal}",
        "objetivo_gym": data.gym_goal,
        "objetivo_dieta": data.nutrition_goal,
        "objetivo_nutricional": data.nutrition_goal,
        "materiales": data.materiales,
        "tipo_cuerpo": getattr(data, "tipo_cuerpo", None),
        "nivel_actividad": data.nivel_actividad,
        "idioma": data.idioma,
        "puntos_fuertes": data.puntos_fuertes,
        "puntos_debiles": data.puntos_debiles,
        "entrenar_fuerte": str(data.entrenar_fuerte),
        "lesiones": data.lesiones,
        "alergias": data.alergias,
        "restricciones_dieta": data.restricciones_dieta,
        "session_duration": getattr(data, "session_duration", None) or "45-60",
    }


def _create_plan_entity(usuario_id: int, data: OnboardingRequest, plan_data: dict) -> Plan:
    """Crea una instancia Plan (sin añadir a sesión) con datos del formulario y plan_data (rutina/dieta/motivacion)."""
    rutina_json = plan_data.get("rutina", {})
    dieta_json = plan_data.get("dieta", {})
    _apply_metadata(rutina_json, dieta_json, data)
    return Plan(
        user_id=usuario_id,
        altura=data.altura,
        peso=str(int(data.peso)),
        edad=data.edad,
        sexo=data.sexo,
        experiencia=data.experiencia,
        objetivo=f"{data.gym_goal} + {data.nutrition_goal}",
        objetivo_gym=data.gym_goal,
        objetivo_dieta=data.nutrition_goal,
        objetivo_nutricional=data.nutrition_goal,
        materiales=data.materiales,
        tipo_cuerpo=getattr(data, "tipo_cuerpo", None),
        nivel_actividad=data.nivel_actividad,
        idioma=data.idioma,
        puntos_fuertes=data.puntos_fuertes,
        puntos_debiles=data.puntos_debiles,
        entrenar_fuerte=str(data.entrenar_fuerte),
        lesiones=data.lesiones,
        alergias=data.alergias,
        restricciones_dieta=data.restricciones_dieta,
        session_duration=getattr(data, "session_duration", None) or "45-60",
        rutina=json.dumps(rutina_json, ensure_ascii=False),
        dieta=json.dumps(dieta_json, ensure_ascii=False),
        motivacion=plan_data.get("motivacion", ""),
        fecha_creacion=datetime.utcnow(),
    )


@router.post("/onboarding")
async def process_onboarding(
    data: OnboardingRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    UPSERT de onboarding: registro inicial (FREE) o actualización de objetivos (PREMIUM).
    - FREE + plan existe: actualiza solo datos físicos; mantiene rutina/dieta template.
    - FREE + no plan: crea Plan con template.
    - PREMIUM + plan existe: sobrescribe todo con resultado de IA.
    - PREMIUM + no plan: crea Plan con resultado de IA.
    Siempre deja al usuario con onboarding_completed=True.
    """
    try:
        # Limpieza de sesión para evitar caché/duplicados
        try:
            db.rollback()
            db.expire_all()
            print(f"✅ Sesión limpiada para user_id {usuario.id}")
        except Exception as cleanup_err:
            print(f"⚠️ Limpieza inicial: {cleanup_err}")

        plan_existente = db.query(Plan).filter_by(user_id=usuario.id).first()
        is_premium = usuario.is_premium or (getattr(usuario, "plan_type", None) or "").upper() == "PREMIUM"
        user_data = _user_data_from_request(data)

        print(f"🔍 Onboarding user_id={usuario.id} premium={is_premium} plan_existente={plan_existente is not None}")

        if is_premium:
            # PREMIUM: IA; si hay plan, sobrescribir todo; si no, crear.
            try:
                plan_data = await generar_plan_personalizado(user_data)
                print(f"✅ Plan IA generado para user_id {usuario.id}")
            except Exception as e:
                print(f"⚠️ GPT falló para premium: {e}; fallback a template")
                plan_data = get_generic_plan(user_data)

            rutina_json = plan_data.get("rutina", {})
            dieta_json = plan_data.get("dieta", {})
            _apply_metadata(rutina_json, dieta_json, data)

            if plan_existente:
                # Sobrescribir todos los campos
                for key, value in _plan_physical_fields(data).items():
                    setattr(plan_existente, key, value)
                plan_existente.rutina = json.dumps(rutina_json, ensure_ascii=False)
                plan_existente.dieta = json.dumps(dieta_json, ensure_ascii=False)
                plan_existente.motivacion = plan_data.get("motivacion", "")
                plan_existente.fecha_creacion = datetime.utcnow()
                plan_id = plan_existente.id
                print(f"✅ Plan existente actualizado con IA (id={plan_id})")
            else:
                nuevo = _create_plan_entity(usuario.id, data, plan_data)
                db.add(nuevo)
                db.flush()
                plan_id = nuevo.id
                print(f"✅ Plan nuevo creado con IA (id={plan_id})")

            current_routine, current_diet = _build_current_routine_diet(rutina_json, dieta_json, data)
            motivacion = plan_data.get("motivacion", "")
            rutina_return = rutina_json
            dieta_return = dieta_json

        else:
            # FREE
            if plan_existente:
                # Solo actualizar datos físicos; mantener rutina/dieta (template) existentes
                for key, value in _plan_physical_fields(data).items():
                    setattr(plan_existente, key, value)
                plan_id = plan_existente.id
                try:
                    rutina_json = json.loads(plan_existente.rutina or "{}")
                except (TypeError, json.JSONDecodeError):
                    rutina_json = {}
                try:
                    dieta_json = json.loads(plan_existente.dieta or "{}")
                except (TypeError, json.JSONDecodeError):
                    dieta_json = {}
                _apply_metadata(rutina_json, dieta_json, data)
                current_routine, current_diet = _build_current_routine_diet(rutina_json, dieta_json, data)
                motivacion = plan_existente.motivacion or ""
                rutina_return = rutina_json
                dieta_return = dieta_json
                print(f"✅ Plan existente actualizado (solo datos físicos) id={plan_id}")
            else:
                plan_data = get_generic_plan(user_data)
                rutina_json = plan_data.get("rutina", {})
                dieta_json = plan_data.get("dieta", {})
                _apply_metadata(rutina_json, dieta_json, data)
                nuevo = _create_plan_entity(usuario.id, data, plan_data)
                db.add(nuevo)
                db.flush()
                plan_id = nuevo.id
                current_routine, current_diet = _build_current_routine_diet(rutina_json, dieta_json, data)
                motivacion = plan_data.get("motivacion", "")
                rutina_return = rutina_json
                dieta_return = dieta_json
                print(f"✅ Plan nuevo creado con template id={plan_id}")

        # Siempre marcar onboarding completado y sincronizar current_routine/current_diet
        db.query(Usuario).filter(Usuario.id == usuario.id).update({
            "onboarding_completed": True,
            "current_routine": json.dumps(current_routine, ensure_ascii=False),
            "current_diet": json.dumps(current_diet, ensure_ascii=False),
        })
        db.commit()

        return {
            "message": "Plan personalizado creado exitosamente",
            "plan_id": plan_id,
            "rutina": rutina_return,
            "dieta": dieta_return,
            "motivacion": motivacion or "¡Vamos a por ello! Con constancia y dedicación alcanzarás tu objetivo.",
        }

    except IntegrityError as e:
        db.rollback()
        error_detail = str(getattr(e, "orig", e)).lower()
        print(f"🚨 IntegrityError onboarding user_id={usuario.id}: {error_detail}")

        # Asegurar que el usuario termine con onboarding_completed=True
        try:
            db.query(Usuario).filter(Usuario.id == usuario.id).update({"onboarding_completed": True})
            db.commit()
        except Exception:
            db.rollback()

        if "foreign key" in error_detail or "fkey" in error_detail:
            raise HTTPException(
                status_code=401,
                detail="Sesión inválida. Por favor, cierra sesión y vuelve a iniciar sesión con Google.",
            )
        if "unique" in error_detail or "duplicate key" in error_detail:
            # Recuperación: devolver plan existente si hay
            plan_existente = db.query(Plan).filter_by(user_id=usuario.id).first()
            if plan_existente:
                try:
                    rutina = json.loads(plan_existente.rutina or "{}")
                except (TypeError, json.JSONDecodeError):
                    rutina = {}
                try:
                    dieta = json.loads(plan_existente.dieta or "{}")
                except (TypeError, json.JSONDecodeError):
                    dieta = {}
                return {
                    "message": "Plan personalizado creado exitosamente",
                    "plan_id": plan_existente.id,
                    "rutina": rutina,
                    "dieta": dieta,
                    "motivacion": plan_existente.motivacion or "",
                }
            raise HTTPException(
                status_code=500,
                detail="Error temporal al crear plan. Recarga la página e intenta de nuevo en unos segundos.",
            )
        raise HTTPException(
            status_code=500,
            detail="Error al validar datos del plan. Verifica que todos los campos estén completos e intenta de nuevo.",
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Error onboarding user_id={usuario.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al crear el plan: {str(e)}")
