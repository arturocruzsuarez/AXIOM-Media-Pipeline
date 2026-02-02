import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class PipelineStabilityIndex:
    """
    Fusión Maestra: Persistencia en Redis + Pesos de Criticidad + Ventana Estadística.
    """
    CALIBRATION_BASELINE = 0.132336
    WINDOW_SIZE = 50 # Analizamos los últimos 50 eventos por sensor
    CACHE_KEY = "axiom_psi_data"

    def __init__(self):
        # Pesos: La suma de la importancia de los componentes
        self.weights = {
            'database': 0.35,  # Crítico
            'storage': 0.40,   # Importante
            'ffmpeg': 0.15,    # Operativo
            'integrity': 0.10  # Informativo
        }

    def _get_history(self):
        """Recupera el historial de éxitos (1) y fallos (0) de Redis."""
        # Estructura: {'ffmpeg': [1, 1, 0, ...], 'database': [...]}
        return cache.get(self.CACHE_KEY, {k: [] for k in self.weights.keys()})

    def report_status(self, component, success):
        """Registra un evento y mantiene la ventana deslizante de 50."""
        if component not in self.weights:
            return

        history = self._get_history()
        val = 1 if success else 0
        
        # Añadimos el nuevo evento y recortamos a los últimos 50
        history[component].append(val)
        if len(history[component]) > self.WINDOW_SIZE:
            history[component].pop(0)

        cache.set(self.CACHE_KEY, history, timeout=None)
        logger.info(f"PSI Log: {component} {'✅' if success else '❌'}")

    def get_diagnostics(self):
        """
        Calcula la salud exacta y la divergencia global.
        Fórmula: PSI = Baseline + Σ((1 - Health) * Weight)
        """
        history = self._get_history()
        component_report = {}
        total_drift = 0.0

        for comp, weight in self.weights.items():
            events = history.get(comp, [])
            # Si no hay eventos, la salud es 100% (1.0)
            health = sum(events) / len(events) if events else 1.0
            
            # El 'drift' es qué tanto se aleja este componente de la perfección
            component_drift = (1.0 - health) * weight
            total_drift += component_drift

            component_report[comp] = {
                'health_pct': round(health * 100, 2),
                'status': self._get_label(health),
                'events_count': len(events)
            }

        # Resultado final: Tu número especial + la desviación técnica
        psi_score = self.CALIBRATION_BASELINE + total_drift
        diff = psi_score - self.CALIBRATION_BASELINE

        return {
            'psi_score': f"{psi_score:.6f}",
            'status': self._get_global_label(diff),
            'world_line': "0.132336 (Baseline)" if diff == 0 else "Attractor Field Drift",
            'components': component_report,
            'is_stable': diff < 0.05
        }

    def _get_label(self, health):
        if health >= 0.98: return "NOMINAL"
        if health >= 0.85: return "DEGRADED"
        return "CRITICAL"

    def _get_global_label(self, diff):
        if diff == 0: return "OPTIMAL"
        if diff < 0.02: return "STABLE"
        if diff < 0.07: return "WARNING"
        return "SYSTEMIC FAILURE"