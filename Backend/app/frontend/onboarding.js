// onboarding.js - Manejo del formulario de configuración inicial
import { API_BASE } from "./config.js";
import { checkAuthOrRedirect, getAuthHeaders } from "./auth.js";

const form = document.getElementById('onboardingForm');
const submitBtn = document.getElementById('submitBtn');
const msg = document.getElementById('msg');

// Elementos para manejo de días de entrenamiento
const frequencySelect = document.getElementById('training_frequency');
const daysContainer = document.getElementById('specific_days_container');
const daysCheckboxes = document.querySelectorAll('input[name="training_days"]');
const daysError = document.getElementById('days-error');
const requiredDaysSpan = document.getElementById('required-days');

// Verificar si hay sesión activa
window.addEventListener('load', () => {
    if (!checkAuthOrRedirect()) {
        return;
    }
});

// Utilidad segura para obtener valores y detectar elementos faltantes
function getFieldValueById(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error(`[Onboarding] Elemento no encontrado en DOM: #${elementId}`);
        throw new Error(`Falta el campo del formulario: ${elementId}`);
    }
    return element.value;
}

// Actualizar número requerido cuando se elige frecuencia
if (frequencySelect && requiredDaysSpan) {
    frequencySelect.addEventListener('change', function() {
        const frequency = parseInt(this.value);
        
        if (frequency > 0) {
            // Actualizar número requerido
            requiredDaysSpan.textContent = frequency;
            
            // Limpiar selección previa
            daysCheckboxes.forEach(cb => {
                cb.checked = false;
            });
            
            // Ocultar error
            if (daysError) {
                daysError.style.display = 'none';
            }
        }
    });
}

// Validar número de días seleccionados
daysCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const frequency = parseInt((frequencySelect && typeof frequencySelect.value !== 'undefined') ? frequencySelect.value : '0');
        const selectedDays = document.querySelectorAll('input[name="training_days"]:checked').length;
        
        // Si se intenta seleccionar más días de los permitidos
        if (selectedDays > frequency) {
            // Desmarcar el último checkbox
            this.checked = false;
            
            // Mostrar error
            if (daysError) {
                daysError.style.display = 'block';
            }
        } else if (selectedDays === frequency) {
            // Si se seleccionaron exactamente los días correctos, ocultar error
            if (daysError) {
                daysError.style.display = 'none';
            }
        }
    });
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validar que se haya seleccionado frecuencia
    const frequency = parseInt(getFieldValueById('training_frequency'));
    if (!frequency || frequency === 0) {
        msg.textContent = '⚠️ Debes seleccionar la frecuencia de entrenamiento';
        msg.style.color = '#ef4444';
        document.getElementById('training_frequency').scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }
    
    // Validar días seleccionados
    const selectedDays = document.querySelectorAll('input[name="training_days"]:checked').length;
    
    if (selectedDays === 0) {
        msg.textContent = '⚠️ Debes seleccionar al menos un día de entrenamiento';
        msg.style.color = '#ef4444';
        if (daysContainer) {
            daysContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }
    
    if (selectedDays !== frequency) {
        if (daysError) {
            daysError.style.display = 'block';
        }
        if (daysContainer) {
            daysContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        msg.textContent = `⚠️ Debes seleccionar exactamente ${frequency} días de entrenamiento (seleccionaste ${selectedDays})`;
        msg.style.color = '#ef4444';
        return; // No enviar formulario
    }
    
    // Deshabilitar botón
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creando plan...';
    
    try {
        // Recopilar datos del formulario
        const formData = {
            altura: parseInt(getFieldValueById('altura')),
            peso: parseFloat(getFieldValueById('peso')),
            edad: parseInt(getFieldValueById('edad')),
            sexo: getFieldValueById('sexo'),
            experiencia: getFieldValueById('experiencia'),
            materiales: getSelectedMaterials(),
            tipo_cuerpo: getFieldValueById('tipo_cuerpo'),
            nivel_actividad: getFieldValueById('nivel_actividad'),  // NUEVO CAMPO - Para cálculo TMB
            alergias: (document.getElementById('alergias') ? document.getElementById('alergias').value : null) || null,
            restricciones_dieta: (document.getElementById('restricciones_dieta') ? document.getElementById('restricciones_dieta').value : null) || null,
            lesiones: (document.getElementById('lesiones') ? document.getElementById('lesiones').value : null) || null,
            idioma: 'es',
            puntos_fuertes: null,
            puntos_debiles: null,
            entrenar_fuerte: true,
            
            // NUEVOS CAMPOS - Onboarding avanzado
            gym_goal: getFieldValueById('gym_goal'),
            nutrition_goal: getFieldValueById('nutrition_goal'),
            training_frequency: frequency,
            training_days: Array.from(document.querySelectorAll('input[name="training_days"]:checked')).map(cb => cb.value)
        };
        
        // Debug: mostrar datos en consola
        console.log('📤 Datos de onboarding:', formData);

        // Validaciones básicas
        if (formData.altura < 120 || formData.altura > 250) {
            throw new Error('Altura debe estar entre 120-250 cm');
        }
        if (formData.peso < 30 || formData.peso > 200) {
            throw new Error('Peso debe estar entre 30-200 kg');
        }
        if (formData.edad < 16 || formData.edad > 80) {
            throw new Error('Edad debe estar entre 16-80 años');
        }

        // Enviar datos al backend
        const headers = getAuthHeaders();
        if (!headers) {
            msg.textContent = 'Error: No hay token de autenticación. Por favor, inicia sesión de nuevo.';
            msg.className = 'text-center text-sm text-red-400 min-h-5';
            return;
        }
        
        const response = await fetch(`${API_BASE}/onboarding`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error al crear el plan');
        }

        // Éxito - marcar onboarding como completado y guardar el plan
        localStorage.setItem("onboarding_completed", "true");
        localStorage.setItem("userPlan", JSON.stringify(data));
        msg.textContent = '¡Plan creado exitosamente! Redirigiendo...';
        msg.style.color = '#84cc16';
        
        setTimeout(() => {
            window.location.href = './dashboard.html';
        }, 2000);

    } catch (error) {
        console.error('Error en onboarding:', error);
        msg.textContent = error.message;
        msg.style.color = '#ef4444';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Crear mi plan personalizado';
    }
});

function getSelectedMaterials() {
    // Obtener solo checkboxes de materiales (excluir training_days)
    const materialCheckboxes = document.querySelectorAll('input[type="checkbox"]:checked:not([name="training_days"])');
    return Array.from(materialCheckboxes).map(cb => cb.value);
}

