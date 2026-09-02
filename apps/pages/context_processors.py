from clinica.permissoes import (
    utilizador_e_responsavel_area,
    utilizador_tem_acesso_area,
)
from config.permissoes_clinicas import GRUPOS_CLINICOS
from enfermagem.models import AREA_CLINICA_ENFERMAGEM


def permissoes_portal(request):
    user = request.user

    if not user.is_authenticated:
        return {}

    grupos = set(
        user.groups.values_list(
            "name",
            flat=True,
        )
    )

    def tem_grupo(*nomes):
        return (
            user.is_superuser
            or bool(grupos.intersection(nomes))
        )

    # Estas permissões respeitam os grupos configurados
    # na área clínica através do Django Admin.
    pode_ver_enfermagem = (
        utilizador_tem_acesso_area(
            user,
            AREA_CLINICA_ENFERMAGEM,
        )
    )

    pode_criar_enfermagem = (
        utilizador_e_responsavel_area(
            user,
            AREA_CLINICA_ENFERMAGEM,
        )
    )

    return {
        # Dashboard
        "pode_ver_dashboard_geral": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        # Visitas
        "pode_ver_visitas": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        # Utentes
        "pode_ver_utentes": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Enfermagem",
            "UCCI_Medicos",
            "UCCI_Psicologia",
            "UCCI_Fisioterapia",
            "UCCI_TerapiaOcupacional",
            "UCCI_TerapiaFala",
            "UCCI_ServicoSocial",
            "UCCI_Coordenacao",
        ),

        "pode_gerir_utentes": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        # Isolamentos
        "pode_ver_isolamentos": tem_grupo(
            "UCCI_Enfermagem",
            "UCCI_Medicos",
            "UCCI_Coordenacao",
        ),

        # Transportes
        "pode_ver_transportes": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Transportes",
            "UCCI_Coordenacao",
        ),

        "pode_pedir_transporte": tem_grupo(
            "UCCI_Enfermagem",
            "UCCI_Medicos",
            "UCCI_ServicoSocial",
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        "pode_ver_pedidos_transporte": tem_grupo(
            "UCCI_Enfermagem",
            "UCCI_Medicos",
            "UCCI_ServicoSocial",
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        "pode_validar_pedidos_transporte": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        "pode_gerir_planeamento_transportes": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        "pode_confirmar_transporte_interno": tem_grupo(
            "UCCI_Transportes",
            "UCCI_Coordenacao",
        ),

        "pode_confirmar_transporte_externo": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        # Fisioterapia
        # Não concede acesso clínico automático ao superutilizador.
        "pode_gerir_fisioterapia": (
            bool(
                grupos.intersection(
                    {
                        "UCCI_Fisioterapia",
                        "UCCI_TerapiaOcupacional",
                        "UCCI_TerapiaFala",
                    }
                )
            )
        ),

        # Registos clínicos gerais
        # Não utiliza tem_grupo(), para impedir acesso clínico
        # automático aos superutilizadores.
        "pode_ver_registos_clinicos": bool(
            grupos.intersection(
                GRUPOS_CLINICOS
            )
        ),

        # Enfermagem
        # Calculado através da configuração da área clínica.
        "pode_ver_registos_enfermagem": (
            pode_ver_enfermagem
        ),

        "pode_criar_registos_enfermagem": (
            pode_criar_enfermagem
        ),

        # Externos
        "pode_ver_externos": tem_grupo(
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        # Financeiro
        "pode_ver_financeiro": tem_grupo(
            "Financeiro",
            "UCCI_Rececao",
            "UCCI_Coordenacao",
        ),

        "pode_ver_mapa_ocupacao": tem_grupo(
            "UCCI_ServicoSocial",
            "UCCI_Coordenacao",
        ),

        # Coordenação
        "pode_ver_coordenacao": tem_grupo(
            "UCCI_Coordenacao",
        ),


        "pode_ver_cozinha": tem_grupo(
            "UCCI_Enfermagem",
            "UCCI_Cozinha",
            "UCCI_Coordenacao",
        ),

        "pode_criar_pedido_cozinha": tem_grupo(
            "UCCI_Enfermagem",
            "UCCI_Coordenacao",
        ),

        "pode_gerir_cozinha": tem_grupo(
            "UCCI_Cozinha",
            "UCCI_Coordenacao",
        ),

        "pode_relatorios_cozinha": tem_grupo(
            "UCCI_Cozinha",
            "UCCI_Coordenacao",
        ),
    }
