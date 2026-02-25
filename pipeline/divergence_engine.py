import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class PipelineStabilityIndex:
    """
    Motor de Divergencia (SRE Entropy Monitor).
    Calcula la tasa de error del sistema basado en los últimos 50 eventos transaccionales.
    0.000000 = Cero Errores (Línea Alpha).
    """
    IDEAL_STATE = 0.000000
    WINDOW_SIZE = 50 # Analizamos los últimos 50 eventos para permitir que el sistema "sane"
    CACHE_KEY = "axiom_psi_data"

    def __init__(self):
        # Pesos: Suman 1.0 (100% del sistema)
        self.weights = {
            'database': 0.35,  # Caída de DB = Desastre total
            'storage': 0.40,   # Sin disco no hay archivos (Pipeline bloqueado)
            'ffmpeg': 0.15,    # Si falla, no hay proxies, pero los originales se salvan
            'integrity': 0.10  # Fallos de Checksum/SSOT
        }

    def _get_history(self):
        """Recupera el historial de éxitos (1) y fallos (0) de Redis."""
        return cache.get(self.CACHE_KEY, {k: [] for k in self.weights.keys()})

    def report_status(self, component, success):
        """Registra un evento asíncrono y desplaza la ventana estadística."""
        if component not in self.weights:
            return

        history = self._get_history()
        val = 1 if success else 0
        
        history[component].append(val)
        if len(history[component]) > self.WINDOW_SIZE:
            history[component].pop(0)

        cache.set(self.CACHE_KEY, history, timeout=None)
        logger.info(f"PSI Telemetry: {component} {'✅ OK' if success else '❌ FAIL'}")

    def get_diagnostics(self):
        """
        Calcula la entropía/divergencia real.
        Fórmula: Entropía Total = Σ((1.0 - Salud_Componente) * Peso_Componente)
        """
        history = self._get_history()
        component_report = {}
        total_entropy = 0.0

        for comp, weight in self.weights.items():
            events = history.get(comp, [])
            
            # Si no hay eventos aún, asumimos que el componente está sano (1.0)
            health = sum(events) / len(events) if events else 1.0
            
            # La entropía es el porcentaje de fallos multiplicado por el peso del componente
            component_entropy = (1.0 - health) * weight
            total_entropy += component_entropy

            component_report[comp] = {
                'health_pct': round(health * 100, 2),
                'status': self._get_label(health),
                'events_count': len(events)
            }

        # La divergencia final es simplemente la entropía sumada al estado ideal (0.0)
        divergence_score = self.IDEAL_STATE + total_entropy

        return {
            'psi_score': f"{divergence_score:.6f}",
            'status': self._get_global_label(total_entropy),
            'world_line': "0.000000 (Alpha Line)" if total_entropy == 0 else f"{divergence_score:.6f} (Attractor Field)",
            'components': component_report,
            'is_stable': total_entropy < 0.05
        }

    def _get_label(self, health):
        if health >= 0.98: return "NOMINAL"
        if health >= 0.85: return "DEGRADED"
        return "CRITICAL"

    def _get_global_label(self, entropy):
        if entropy == 0: return "OPTIMAL"
        if entropy < 0.02: return "STABLE"
        if entropy < 0.07: return "WARNING"
        return "SYSTEMIC FAILURE"