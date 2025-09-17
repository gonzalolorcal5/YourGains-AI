// onboarding.js - Manejo del formulario de configuración inicial
const isLocal = location.hostname === "127.0.0.1" || location.hostname === "localhost" || location.protocol === "file:";
const API_BASE = isLocal ? "http://127.0.0.1:8000" : "https://yourgains-ai-production.up.railway.app";

const form = document.getElementById('onboardingForm');
const submitBtn = document.getElementById('submitBtn');
const msg = document.getElementById('msg');

// Verificar si hay sesión activa
window.addEventListener('load', () => {
    const token = localStorage.getItem("accessToken");
    const email = localStorage.getItem("email");
    
    if (!token || !email) {
        window.location.href = "./login.html";
        return;
    }
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Deshabilitar botón
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creando plan...';
    
    try {
        // Recopilar datos del formulario
        const formData = {
            altura: parseInt(document.getElementById('altura').value),
            peso: parseFloat(document.getElementById('peso').value),
            edad: parseInt(document.getElementById('edad').value),
            sexo: document.getElementById('sexo').value,
            objetivo: document.getElementById('objetivo').value,
            experiencia: document.getElementById('experiencia').value,
            materiales: getSelectedMaterials(),
            tipo_cuerpo: document.getElementById('tipo_cuerpo').value,
            alergias: document.getElementById('alergias').value || null,
            restricciones_dieta: document.getElementById('restricciones_dieta').value || null,
            lesiones: document.getElementById('lesiones').value || null,
            idioma: 'es',
            puntos_fuertes: null,
            puntos_debiles: null,
            entrenar_fuerte: true
        };

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
        const response = await fetch(`${API_BASE}/onboarding`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                'X-User-Email': localStorage.getItem('email')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error al crear el plan');
        }

        // Éxito - redirigir al dashboard
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
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

