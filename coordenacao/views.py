from .dashboard_views import (
    dashboard_cozinha,
    dashboard_enfermagem,
    dashboard_financeiro,
    dashboard_fisioterapia,
    dashboard_geral,
    dashboard_transportes,
    dashboard_utentes,
    dashboard_visitas,
)
from .pdf_views import relatorio_visitas_pdf


__all__ = [
    "dashboard_geral",
    "dashboard_utentes",
    "dashboard_visitas",
    "dashboard_transportes",
    "dashboard_enfermagem",
    "dashboard_fisioterapia",
    "dashboard_cozinha",
    "dashboard_financeiro",
    "relatorio_visitas_pdf",
]
