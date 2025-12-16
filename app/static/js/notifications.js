/**
 * Toast Notification System - Modern & Smooth
 * Provides elegant user feedback with animated toast notifications
 */

const NotificationManager = {
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'fixed top-6 right-6 z-[9999] space-y-3';
            this.container.style.cssText = 'pointer-events: none;';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 5000) {
        this.init();

        const notification = document.createElement('div');
        notification.className = 'notification-toast';
        notification.style.cssText = `
            transform: translateX(400px);
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: auto;
        `;

        const config = {
            success: {
                icon: 'fa-check-circle',
                bg: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                border: '#10b981',
                text: '#065f46',
                iconColor: '#10b981'
            },
            error: {
                icon: 'fa-exclamation-circle',
                bg: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
                border: '#ef4444',
                text: '#991b1b',
                iconColor: '#ef4444'
            },
            warning: {
                icon: 'fa-exclamation-triangle',
                bg: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)',
                border: '#f59e0b',
                text: '#92400e',
                iconColor: '#f59e0b'
            },
            info: {
                icon: 'fa-info-circle',
                bg: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                border: '#3b82f6',
                text: '#1e40af',
                iconColor: '#3b82f6'
            }
        };

        const { icon, bg, border, text, iconColor } = config[type];

        notification.innerHTML = `
            <div style="
                background: ${bg};
                border-left: 4px solid ${border};
                border-radius: 12px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                padding: 16px 20px;
                min-width: 320px;
                max-width: 420px;
                display: flex;
                align-items: start;
                gap: 12px;
                backdrop-filter: blur(10px);
            ">
                <i class="fas ${icon}" style="
                    color: ${iconColor};
                    font-size: 20px;
                    flex-shrink: 0;
                    margin-top: 2px;
                "></i>
                <p style="
                    color: ${text};
                    font-weight: 600;
                    font-size: 14px;
                    line-height: 1.5;
                    flex: 1;
                    margin: 0;
                ">${message}</p>
                <button onclick="this.closest('.notification-toast').dispatchEvent(new Event('close'))"
                        style="
                            background: none;
                            border: none;
                            color: ${text};
                            opacity: 0.6;
                            cursor: pointer;
                            padding: 0;
                            width: 20px;
                            height: 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            transition: opacity 0.2s;
                            flex-shrink: 0;
                        "
                        onmouseover="this.style.opacity='1'"
                        onmouseout="this.style.opacity='0.6'">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        this.container.appendChild(notification);

        // Animate in
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                notification.style.transform = 'translateX(0)';
                notification.style.opacity = '1';
            });
        });

        // Close event handler
        const closeHandler = () => {
            this.hide(notification);
        };
        notification.addEventListener('close', closeHandler);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.hide(notification);
            }, duration);
        }

        return notification;
    },

    hide(notification) {
        notification.style.transform = 'translateX(400px)';
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 400);
    },

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    },

    error(message, duration = 7000) {
        return this.show(message, 'error', duration);
    },

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    },

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }
};

// Loading overlay system - Modern & Smooth
const LoadingOverlay = {
    overlay: null,

    init() {
        if (!this.overlay) {
            this.overlay = document.createElement('div');
            this.overlay.id = 'loading-overlay';
            this.overlay.className = 'loading-overlay hidden';
            this.overlay.innerHTML = `
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 40px;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 320px;
                    animation: scaleIn 0.3s ease-out;
                ">
                    <div style="
                        width: 64px;
                        height: 64px;
                        border: 4px solid #e5e7eb;
                        border-top-color: #3b82f6;
                        border-radius: 50%;
                        margin: 0 auto 24px;
                        animation: spin 0.8s linear infinite;
                    "></div>
                    <p id="loading-message" style="
                        color: #374151;
                        font-weight: 600;
                        font-size: 16px;
                        margin: 0;
                    ">Traitement en cours...</p>
                </div>
            `;
            document.body.appendChild(this.overlay);
        }
    },

    show(message = 'Traitement en cours...') {
        this.init();
        const messageEl = this.overlay.querySelector('#loading-message');
        if (messageEl) {
            messageEl.textContent = message;
        }
        this.overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    },

    hide() {
        if (this.overlay) {
            this.overlay.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }
};

// Error handler for fetch requests
async function handleFetchResponse(response) {
    if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Une erreur est survenue';

        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            errorMessage = data.error || data.message || errorMessage;
        } else {
            errorMessage = `Erreur ${response.status}: ${response.statusText}`;
        }

        throw new Error(errorMessage);
    }

    return response;
}

// Utility to display validation errors
function displayValidationErrors(errors) {
    if (Array.isArray(errors)) {
        errors.forEach((error, index) => {
            setTimeout(() => {
                NotificationManager.error(error);
            }, index * 150);
        });
    } else if (typeof errors === 'object') {
        let index = 0;
        Object.entries(errors).forEach(([field, messages]) => {
            const errorList = Array.isArray(messages) ? messages : [messages];
            errorList.forEach(msg => {
                setTimeout(() => {
                    NotificationManager.error(`${field}: ${msg}`);
                }, index * 150);
                index++;
            });
        });
    } else {
        NotificationManager.error(errors);
    }
}

// Export for global use
window.NotificationManager = NotificationManager;
window.LoadingOverlay = LoadingOverlay;
window.handleFetchResponse = handleFetchResponse;
window.displayValidationErrors = displayValidationErrors;
