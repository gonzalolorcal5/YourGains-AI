/**
 * Cookie Consent Manager - RGPD Compliant
 * YourGains AI
 */

(function() {
    'use strict';

    const COOKIE_CONSENT_KEY = 'yg_cookie_consent';
    const CONSENT_EXPIRY_DAYS = 365; // 12 meses

    // Configuración de cookies
    const cookieCategories = {
        necessary: {
            name: 'Necesarias',
            description: 'Cookies esenciales para el funcionamiento del sitio. No se pueden desactivar.',
            required: true,
            enabled: true
        },
        analytics: {
            name: 'Analíticas',
            description: 'Cookies de Google Analytics para analizar el uso del sitio de forma anónima.',
            required: false,
            enabled: false
        }
    };

    /**
     * Obtener consentimiento guardado
     */
    function getStoredConsent() {
        try {
            const stored = localStorage.getItem(COOKIE_CONSENT_KEY);
            if (!stored) return null;
            
            const consent = JSON.parse(stored);
            const expiryDate = new Date(consent.expiry);
            
            // Verificar si el consentimiento ha expirado
            if (new Date() > expiryDate) {
                localStorage.removeItem(COOKIE_CONSENT_KEY);
                return null;
            }
            
            return consent;
        } catch (e) {
            console.error('Error reading cookie consent:', e);
            return null;
        }
    }

    /**
     * Guardar consentimiento
     */
    function saveConsent(preferences) {
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + CONSENT_EXPIRY_DAYS);
        
        const consent = {
            preferences: preferences,
            timestamp: new Date().toISOString(),
            expiry: expiryDate.toISOString()
        };
        
        try {
            localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(consent));
            return true;
        } catch (e) {
            console.error('Error saving cookie consent:', e);
            return false;
        }
    }

    /**
     * Cargar Google Analytics dinámicamente
     */
    function loadGoogleAnalytics() {
        if (window.gtag) {
            return; // Ya está cargado
        }

        // Crear script de Google Analytics
        const script1 = document.createElement('script');
        script1.async = true;
        script1.src = 'https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX'; // Reemplazar con tu ID real
        document.head.appendChild(script1);

        // Inicializar gtag
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        window.gtag = gtag;
        gtag('js', new Date());
        gtag('config', 'G-XXXXXXXXXX', {
            anonymize_ip: true,
            cookie_flags: 'SameSite=None;Secure'
        });

        console.log('Google Analytics cargado');
    }

    /**
     * Aplicar preferencias de cookies
     */
    function applyCookiePreferences(preferences) {
        if (preferences.analytics) {
            loadGoogleAnalytics();
        } else {
            // Desactivar Google Analytics si estaba cargado
            if (window.gtag) {
                window.gtag('consent', 'update', {
                    'analytics_storage': 'denied'
                });
            }
        }
    }

    /**
     * Mostrar banner de consentimiento
     */
    function showConsentBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (banner) {
            banner.classList.remove('hidden');
            banner.classList.add('flex');
            // Animación suave
            setTimeout(() => {
                banner.style.opacity = '1';
                banner.style.transform = 'translateY(0)';
            }, 10);
        }
    }

    /**
     * Ocultar banner de consentimiento
     */
    function hideConsentBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (banner) {
            banner.style.opacity = '0';
            banner.style.transform = 'translateY(100%)';
            setTimeout(() => {
                banner.classList.add('hidden');
                banner.classList.remove('flex');
            }, 300);
        }
    }

    /**
     * Mostrar modal de personalización
     */
    function showCustomizeModal() {
        const modal = document.getElementById('cookie-customize-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Ocultar modal de personalización
     */
    function hideCustomizeModal() {
        const modal = document.getElementById('cookie-customize-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.style.overflow = 'auto';
        }
    }

    /**
     * Aceptar todas las cookies
     */
    function acceptAll() {
        const preferences = {
            necessary: true,
            analytics: true
        };
        
        saveConsent(preferences);
        applyCookiePreferences(preferences);
        hideConsentBanner();
    }

    /**
     * Rechazar cookies no esenciales
     */
    function rejectNonEssential() {
        const preferences = {
            necessary: true,
            analytics: false
        };
        
        saveConsent(preferences);
        applyCookiePreferences(preferences);
        hideConsentBanner();
    }

    /**
     * Guardar preferencias personalizadas
     */
    function saveCustomPreferences() {
        const necessaryCheckbox = document.getElementById('cookie-necessary');
        const analyticsCheckbox = document.getElementById('cookie-analytics');
        
        const preferences = {
            necessary: true, // Siempre true (requerida)
            analytics: analyticsCheckbox ? analyticsCheckbox.checked : false
        };
        
        saveConsent(preferences);
        applyCookiePreferences(preferences);
        hideCustomizeModal();
        hideConsentBanner();
    }

    /**
     * Inicializar sistema de consentimiento
     */
    function initCookieConsent() {
        const consent = getStoredConsent();
        
        if (consent) {
            // Ya hay consentimiento, aplicar preferencias
            applyCookiePreferences(consent.preferences);
        } else {
            // No hay consentimiento, mostrar banner
            showConsentBanner();
        }

        // Event listeners para botones del banner
        const acceptAllBtn = document.getElementById('cookie-accept-all');
        const rejectBtn = document.getElementById('cookie-reject');
        const customizeBtn = document.getElementById('cookie-customize');
        
        if (acceptAllBtn) {
            acceptAllBtn.addEventListener('click', acceptAll);
        }
        
        if (rejectBtn) {
            rejectBtn.addEventListener('click', rejectNonEssential);
        }
        
        if (customizeBtn) {
            customizeBtn.addEventListener('click', showCustomizeModal);
        }

        // Event listeners para modal de personalización
        const saveCustomBtn = document.getElementById('cookie-save-custom');
        const cancelCustomBtn = document.getElementById('cookie-cancel-custom');
        const closeModalBtn = document.getElementById('cookie-close-modal');
        
        if (saveCustomBtn) {
            saveCustomBtn.addEventListener('click', saveCustomPreferences);
        }
        
        if (cancelCustomBtn) {
            cancelCustomBtn.addEventListener('click', hideCustomizeModal);
        }
        
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', hideCustomizeModal);
        }

        // Cerrar modal al hacer clic fuera
        const modal = document.getElementById('cookie-customize-modal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    hideCustomizeModal();
                }
            });
        }

        // Cerrar modal con ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                hideCustomizeModal();
            }
        });
    }

    /**
     * Función pública para cambiar preferencias desde el footer
     */
    window.showCookiePreferences = function() {
        const consent = getStoredConsent();
        
        if (consent) {
            // Cargar preferencias actuales en el modal
            const analyticsCheckbox = document.getElementById('cookie-analytics');
            if (analyticsCheckbox) {
                analyticsCheckbox.checked = consent.preferences.analytics || false;
            }
        }
        
        showCustomizeModal();
    };

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCookieConsent);
    } else {
        initCookieConsent();
    }
})();

