from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import (
    parse_date,
    parse_datetime,
)
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from config.decorators import grupos_permitidos
from config.permissoes_clinicas import (
    GRUPOS_CLINICOS,
    VisibilidadeRegisto,
)
from visitas.models import Piso, Utente

from .forms import (
    RegistoFisioterapiaForm,
    SessaoFisioterapiaForm,
)
from .models import (
    AreaReabilitacao,
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    GRUPO_POR_AREA_REABILITACAO,
    GRUPOS_REABILITACAO,
    LocalSessaoFisioterapia,
    ParticipacaoFisioterapia,
    RegistoFisioterapia,
    SessaoFisioterapia,
    TipoIntervencaoFisioterapia,
    TipoSessaoFisioterapia,
)
from .services import (
    alterar_estado_participacao,
    cancelar_sessao as executar_cancelamento_sessao,
    sincronizar_participantes,
)
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from clinica.permissoes import (
    filtrar_registos_visiveis,
)
from enfermagem.models import (
    AREA_CLINICA_ENFERMAGEM,
    RegistoQueda,
)
from visitas.models import (
    Isolamento,
    Utente,
)

User = get_user_model()


def _converter_data_hora(valor):
    data_hora = parse_datetime(valor) if valor else None

    if (
        data_hora
        and settings.USE_TZ
        and timezone.is_naive(data_hora)
    ):
        data_hora = timezone.make_aware(
            data_hora,
            timezone.get_current_timezone(),
        )

    return data_hora


def _utilizador_e_fisioterapeuta(utilizador):
    return (
        utilizador.is_authenticated
        and utilizador.groups.filter(
            name__in=GRUPOS_REABILITACAO
        ).exists()
    )


def _profissionais_fisioterapia():
    return (
        User.objects
        .filter(
            is_active=True,
            groups__name__in=GRUPOS_REABILITACAO,
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )


def _nome_profissional(utilizador):
    if not utilizador:
        return "-"

    nome = utilizador.get_full_name().strip()
    return nome or utilizador.username


def _resumo_intervencoes(sessao):
    nomes = [
        intervencao.nome
        for intervencao in sessao.tipos_intervencao.all()
    ]

    if not nomes:
        return "Fisioterapia/Reabilitação"

    if len(nomes) <= 2:
        return " + ".join(nomes)

    return (
        " + ".join(nomes[:2])
        + f" +{len(nomes) - 2}"
    )


def _registos_visiveis(utilizador, queryset=None):
    if queryset is None:
        queryset = RegistoFisioterapia.objects.all()

    if not utilizador.is_authenticated:
        return queryset.none()

    grupos = set(
        utilizador.groups.values_list(
            "name",
            flat=True,
        )
    )

    condicoes = Q(
        profissional=utilizador
    )

    areas_profissional = [
        area
        for area, grupo in GRUPO_POR_AREA_REABILITACAO.items()
        if grupo in grupos
    ]

    if areas_profissional:
        condicoes |= Q(
            visibilidade=VisibilidadeRegisto.GRUPO,
            area__in=areas_profissional,
        )

    if grupos.intersection(GRUPOS_CLINICOS):
        condicoes |= Q(
            visibilidade=VisibilidadeRegisto.TODOS
        )

    return queryset.filter(condicoes).distinct()


def _registar_alteracao_estado_sessao(
    sessao,
    estado_anterior,
    utilizador,
):
    sessao.refresh_from_db(
        fields=["estado"]
    )

    if sessao.estado == estado_anterior:
        return

    sessao.estado_atualizado_por = utilizador
    sessao.estado_atualizado_em = timezone.now()

    sessao.save(
        update_fields=[
            "estado_atualizado_por",
            "estado_atualizado_em",
            "atualizado_em",
        ]
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def calendario_fisioterapia(request):
    hoje = timezone.localdate()

    sessoes_hoje = SessaoFisioterapia.objects.filter(
        inicio__date=hoje,
    )

    participacoes_por_validar = (
        ParticipacaoFisioterapia.objects
        .filter(
            estado=EstadoParticipacaoFisioterapia.AGENDADO,
            sessao__inicio__lt=timezone.now(),
        )
        .exclude(
            sessao__estado=EstadoSessaoFisioterapia.CANCELADA
        )
        .count()
    )

    return render(
        request,
        "fisioterapia/calendario.html",
        {
            "total_sessoes_hoje": (
                sessoes_hoje.count()
            ),
            "total_individuais_hoje": (
                sessoes_hoje.filter(
                    tipo=TipoSessaoFisioterapia.INDIVIDUAL
                ).count()
            ),
            "total_grupo_hoje": (
                sessoes_hoje.filter(
                    tipo=TipoSessaoFisioterapia.GRUPO
                ).count()
            ),
            "total_por_validar": (
                participacoes_por_validar
            ),
            "estados": (
                EstadoSessaoFisioterapia.choices
            ),
            "tipos": TipoSessaoFisioterapia.choices,
            "profissionais": (
                _profissionais_fisioterapia()
            ),
            "tipos_intervencao": (
                TipoIntervencaoFisioterapia.objects
                .filter(ativo=True)
                .order_by(
                    "area",
                    "ordem",
                    "categoria",
                    "nome",
                )
            ),
            "locais": LocalSessaoFisioterapia.choices,
            "pisos": Piso.choices,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
@never_cache
def eventos_fisioterapia(request):
    inicio = _converter_data_hora(
        request.GET.get("start")
    )

    fim = _converter_data_hora(
        request.GET.get("end")
    )

    estado = request.GET.get(
        "estado",
        "",
    ).strip()

    tipo = request.GET.get(
        "tipo",
        "",
    ).strip()

    profissional_id = request.GET.get(
        "profissional",
        "",
    ).strip()

    intervencao_id = request.GET.get(
        "intervencao",
        "",
    ).strip()

    local_realizacao = request.GET.get(
        "local_realizacao",
        "",
    ).strip()

    piso = request.GET.get(
        "piso",
        "",
    ).strip()

    sessoes = (
        SessaoFisioterapia.objects
        .select_related(
            "profissional",
            "criado_por",
        )
        .prefetch_related(
            "participacoes__utente__quarto",
            "tipos_intervencao",
        )
    )

    if inicio:
        sessoes = sessoes.filter(
            fim__gt=inicio
        )

    if fim:
        sessoes = sessoes.filter(
            inicio__lt=fim
        )

    if estado:
        sessoes = sessoes.filter(
            estado=estado
        )

    if tipo:
        sessoes = sessoes.filter(
            tipo=tipo
        )

    if profissional_id.isdigit():
        sessoes = sessoes.filter(
            profissional_id=profissional_id
        )

    if intervencao_id.isdigit():
        sessoes = sessoes.filter(
            tipos_intervencao__id=intervencao_id
        )

    locais_validos = {
        valor
        for valor, _ in LocalSessaoFisioterapia.choices
    }

    if local_realizacao in locais_validos:
        sessoes = sessoes.filter(
            local_realizacao=local_realizacao
        )

    pisos_validos = {
        valor
        for valor, _ in Piso.choices
    }

    if piso in pisos_validos:
        sessoes = sessoes.filter(
            participacoes__utente__quarto__piso=piso
        )

    sessoes = sessoes.distinct()

    eventos = []

    for sessao in sessoes:
        participacoes = list(
            sessao.participacoes.all()
        )

        participacoes_ativas = [
            participacao
            for participacao in participacoes
            if participacao.estado not in {
                EstadoParticipacaoFisioterapia.CANCELADO,
                EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
            }
        ]

        nomes_ativos = [
            participacao.utente.nome
            for participacao in participacoes_ativas
        ]

        todos_nomes = [
            participacao.utente.nome
            for participacao in participacoes
        ]

        localizacoes_utentes = []

        for participacao in participacoes_ativas:
            utente = participacao.utente
            quarto = utente.quarto

            if quarto:
                localizacoes_utentes.append(
                    (
                        f"{utente.nome}: quarto "
                        f"{quarto.codigo}, "
                        f"{quarto.get_piso_display()}"
                    )
                )
            else:
                localizacoes_utentes.append(
                    f"{utente.nome}: sem quarto/piso"
                )

        if sessao.tipo == TipoSessaoFisioterapia.GRUPO:
            quantidade = len(nomes_ativos)

            if quantidade == 1:
                identificacao = "Grupo (1 utente)"
            else:
                identificacao = (
                    f"Grupo ({quantidade} utentes)"
                )
        elif nomes_ativos:
            identificacao = nomes_ativos[0]
        elif todos_nomes:
            identificacao = todos_nomes[0]
        else:
            identificacao = "Sessão individual"

        profissional = _nome_profissional(
            sessao.profissional
        )

        intervencoes = _resumo_intervencoes(
            sessao
        )

        titulo = (
            f"{identificacao} — "
            f"{intervencoes} · "
            f"{profissional}"
        )

        if (
            sessao.estado
            == EstadoSessaoFisioterapia.CANCELADA
        ):
            cor = "#6c757d"
        elif (
            sessao.estado
            == EstadoSessaoFisioterapia.REALIZADA
        ):
            cor = "#198754"
        elif (
            sessao.tipo
            == TipoSessaoFisioterapia.GRUPO
        ):
            cor = "#6f42c1"
        else:
            cor = "#0d6efd"

        eventos.append({
            "id": sessao.pk,
            "title": titulo,
            "start": sessao.inicio.isoformat(),
            "end": sessao.fim.isoformat(),
            "url": reverse(
                "fisioterapia:detalhe_sessao",
                args=[sessao.pk],
            ),
            "backgroundColor": cor,
            "borderColor": cor,
            "extendedProps": {
                "tipo": sessao.get_tipo_display(),
                "estado": sessao.get_estado_display(),
                "profissional": profissional,
                "criado_por": _nome_profissional(
                    sessao.criado_por
                ),
                "local": sessao.local_exibicao,
                "intervencoes": [
                    intervencao.nome
                    for intervencao
                    in sessao.tipos_intervencao.all()
                ],
                "participantes": nomes_ativos,
                "localizacoes_utentes": (
                    localizacoes_utentes
                ),
            },
        })

    return JsonResponse(
        eventos,
        safe=False,
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def lista_sessoes(request):
    sessoes = (
        SessaoFisioterapia.objects
        .select_related(
            "profissional",
            "criado_por",
        )
        .prefetch_related(
            "participacoes__utente__quarto",
            "tipos_intervencao",
        )
    )

    q = request.GET.get(
        "q",
        "",
    ).strip()

    estado = request.GET.get(
        "estado",
        "",
    ).strip()

    tipo = request.GET.get(
        "tipo",
        "",
    ).strip()

    data = parse_date(
        request.GET.get("data", "")
    )

    profissional_id = request.GET.get(
        "profissional",
        "",
    ).strip()

    intervencao_id = request.GET.get(
        "intervencao",
        "",
    ).strip()

    local_realizacao = request.GET.get(
        "local_realizacao",
        "",
    ).strip()

    piso = request.GET.get(
        "piso",
        "",
    ).strip()

    por_validar = (
        request.GET.get(
            "por_validar",
            "",
        ).strip()
        == "1"
    )

    if q:
        sessoes = sessoes.filter(
            Q(local__icontains=q)
            | Q(trabalho_planeado__icontains=q)
            | Q(observacoes__icontains=q)
            | Q(
                tipos_intervencao__nome__icontains=q
            )
            | Q(
                participacoes__utente__nome__icontains=q
            )
            | Q(
                participacoes__utente__numero_processo__icontains=q
            )
            | Q(
                participacoes__utente__quarto__codigo__icontains=q
            )
            | Q(
                profissional__first_name__icontains=q
            )
            | Q(
                profissional__last_name__icontains=q
            )
            | Q(
                profissional__username__icontains=q
            )
        )

    if estado:
        sessoes = sessoes.filter(
            estado=estado
        )

    if tipo:
        sessoes = sessoes.filter(
            tipo=tipo
        )

    if data:
        sessoes = sessoes.filter(
            inicio__date=data
        )

    if profissional_id.isdigit():
        sessoes = sessoes.filter(
            profissional_id=profissional_id
        )

    if intervencao_id.isdigit():
        sessoes = sessoes.filter(
            tipos_intervencao__id=intervencao_id
        )

    locais_validos = {
        valor
        for valor, _ in LocalSessaoFisioterapia.choices
    }

    if local_realizacao in locais_validos:
        sessoes = sessoes.filter(
            local_realizacao=local_realizacao
        )

    pisos_validos = {
        valor
        for valor, _ in Piso.choices
    }

    if piso in pisos_validos:
        sessoes = sessoes.filter(
            participacoes__utente__quarto__piso=piso
        )

    if por_validar:
        sessoes = (
            sessoes
            .filter(
                profissional=request.user,
                inicio__lt=timezone.now(),
                participacoes__estado=(
                    EstadoParticipacaoFisioterapia
                    .AGENDADO
                ),
            )
            .exclude(
                estado=(
                    EstadoSessaoFisioterapia.CANCELADA
                )
            )
        )

    sessoes = sessoes.distinct().order_by(
        "-inicio"
    )

    return render(
        request,
        "fisioterapia/lista_sessoes.html",
        {
            "sessoes": sessoes,
            "q": q,
            "estado": estado,
            "tipo": tipo,
            "data": data,
            "profissional_id": profissional_id,
            "intervencao_id": intervencao_id,
            "local_realizacao": local_realizacao,
            "piso": piso,
            "por_validar": por_validar,
            "estados": (
                EstadoSessaoFisioterapia.choices
            ),
            "tipos": TipoSessaoFisioterapia.choices,
            "profissionais": (
                _profissionais_fisioterapia()
            ),
            "tipos_intervencao": (
                TipoIntervencaoFisioterapia.objects
                .filter(ativo=True)
                .order_by(
                    "area",
                    "ordem",
                    "categoria",
                    "nome",
                )
            ),
            "locais": LocalSessaoFisioterapia.choices,
            "pisos": Piso.choices,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def criar_sessao(request):
    inicio = _converter_data_hora(
        request.GET.get("inicio")
    )

    initial = {}

    area_pedida = request.GET.get("area")
    if area_pedida in _areas_reabilitacao_utilizador(request.user):
        initial["area"] = area_pedida

    if inicio:
        initial["inicio"] = inicio
        initial["fim"] = (
            inicio + timedelta(hours=1)
        )

    if request.method == "POST":
        form = SessaoFisioterapiaForm(
            request.POST,
            profissional=request.user,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    sessao = form.save(
                        commit=False
                    )

                    sessao.criado_por = request.user

                    sessao.full_clean()
                    sessao.save()

                    form.save_m2m()

                    sincronizar_participantes(
                        sessao=sessao,
                        utentes=form.cleaned_data[
                            "utentes"
                        ],
                        utilizador=request.user,
                    )

            except ValidationError as erro:
                form.add_error(
                    None,
                    " ".join(erro.messages),
                )

            else:
                messages.success(
                    request,
                    (
                        "Sessão criada e atribuída a "
                        f"{_nome_profissional(sessao.profissional)}."
                    ),
                )

                return redirect(
                    "fisioterapia:detalhe_sessao",
                    pk=sessao.pk,
                )
    else:
        form = SessaoFisioterapiaForm(
            initial=initial,
            profissional=request.user,
        )

    return render(
        request,
        "fisioterapia/form_sessao.html",
        {
            "form": form,
            "sessao": None,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def editar_sessao(request, pk):
    sessao = get_object_or_404(
        SessaoFisioterapia.objects
        .select_related(
            "profissional",
            "criado_por",
        )
        .prefetch_related(
            "tipos_intervencao",
        ),
        pk=pk,
    )

    if not sessao.pode_editar(request.user):
        raise PermissionDenied(
            (
                "Só o fisioterapeuta responsável "
                "pode editar esta sessão."
            )
        )

    if (
        sessao.estado
        != EstadoSessaoFisioterapia.AGENDADA
    ):
        messages.warning(
            request,
            (
                "Apenas sessões agendadas "
                "podem ser editadas."
            ),
        )

        return redirect(
            "fisioterapia:detalhe_sessao",
            pk=sessao.pk,
        )

    if request.method == "POST":
        form = SessaoFisioterapiaForm(
            request.POST,
            instance=sessao,
            profissional=request.user,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    sessao = form.save(
                        commit=False
                    )

                    sessao.full_clean()
                    sessao.save()

                    form.save_m2m()

                    sincronizar_participantes(
                        sessao=sessao,
                        utentes=form.cleaned_data[
                            "utentes"
                        ],
                        utilizador=request.user,
                    )

            except ValidationError as erro:
                form.add_error(
                    None,
                    " ".join(erro.messages),
                )

            else:
                messages.success(
                    request,
                    (
                        "Sessão atualizada. O profissional "
                        "responsável é "
                        f"{_nome_profissional(sessao.profissional)}."
                    ),
                )

                return redirect(
                    "fisioterapia:detalhe_sessao",
                    pk=sessao.pk,
                )
    else:
        form = SessaoFisioterapiaForm(
            instance=sessao,
            profissional=request.user,
        )

    return render(
        request,
        "fisioterapia/form_sessao.html",
        {
            "form": form,
            "sessao": sessao,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def detalhe_sessao(request, pk):
    sessao = get_object_or_404(
        SessaoFisioterapia.objects
        .select_related(
            "profissional",
            "criado_por",
            "estado_atualizado_por",
        )
        .prefetch_related(
            "tipos_intervencao",
        ),
        pk=pk,
    )

    participacoes = (
        sessao.participacoes
        .select_related(
            "utente",
            "estado_atualizado_por",
        )
        .prefetch_related(
            "historico__alterado_por",
            "registos_clinicos__tipos_intervencao",
        )
        .order_by("utente__nome")
    )

    for participacao in participacoes:
        participacao.registos_visiveis = (
            _registos_visiveis(
                request.user,
                participacao.registos_clinicos
                .select_related("profissional")
                .prefetch_related(
                    "tipos_intervencao"
                ),
            )
        )

    pode_editar = sessao.pode_editar(
        request.user
    )

    return render(
        request,
        "fisioterapia/detalhe_sessao.html",
        {
            "sessao": sessao,
            "participacoes": participacoes,
            "pode_editar": pode_editar,
            "pode_validar": pode_editar,
        },
    )


@require_POST
@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def acao_participacao(request, pk, acao):
    with transaction.atomic():
        participacao = get_object_or_404(
            ParticipacaoFisioterapia.objects
            .select_for_update()
            .select_related(
                "sessao",
                "utente",
            ),
            pk=pk,
        )

        sessao = participacao.sessao

        if not sessao.pode_registar_presencas(
            request.user
        ):
            raise PermissionDenied(
                (
                    "Só o fisioterapeuta responsável "
                    "pode validar esta presença."
                )
            )

        estados = {
            "realizado": (
                EstadoParticipacaoFisioterapia.REALIZADO
            ),
            "faltou": (
                EstadoParticipacaoFisioterapia.FALTOU
            ),
            "cancelar": (
                EstadoParticipacaoFisioterapia.CANCELADO
            ),
            "reagendar": (
                EstadoParticipacaoFisioterapia.AGENDADO
            ),
            "reativar": (
                EstadoParticipacaoFisioterapia.AGENDADO
            ),
        }

        novo_estado = estados.get(acao)

        if not novo_estado:
            messages.error(
                request,
                "A ação indicada não é válida.",
            )

            return redirect(
                "fisioterapia:detalhe_sessao",
                pk=sessao.pk,
            )



        motivo = request.POST.get(
            "motivo",
            "",
        ).strip()

        estado_anterior_sessao = sessao.estado

        try:
            alterar_estado_participacao(
                participacao=participacao,
                novo_estado=novo_estado,
                utilizador=request.user,
                motivo=motivo,
            )

            _registar_alteracao_estado_sessao(
                sessao=sessao,
                estado_anterior=estado_anterior_sessao,
                utilizador=request.user,
            )

        except ValidationError as erro:
            messages.error(
                request,
                " ".join(erro.messages),
            )

        else:
            messages.success(
                request,
                "Estado do utente atualizado.",
            )

    return redirect(
        "fisioterapia:detalhe_sessao",
        pk=participacao.sessao_id,
    )


@require_POST
@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def marcar_todos_realizados(request, pk):
    with transaction.atomic():
        sessao = get_object_or_404(
            SessaoFisioterapia.objects
            .select_for_update()
            .select_related("profissional"),
            pk=pk,
        )

        if not sessao.pode_registar_presencas(
            request.user
        ):
            raise PermissionDenied(
                (
                    "Só o fisioterapeuta responsável "
                    "pode validar esta sessão."
                )
            )



        participacoes = list(
            sessao.participacoes
            .select_for_update()
            .filter(
                estado=(
                    EstadoParticipacaoFisioterapia.AGENDADO
                )
            )
        )

        if not participacoes:
            messages.warning(
                request,
                (
                    "Não existem utentes agendados "
                    "por validar."
                ),
            )

            return redirect(
                "fisioterapia:detalhe_sessao",
                pk=sessao.pk,
            )

        estado_anterior_sessao = sessao.estado

        for participacao in participacoes:
            alterar_estado_participacao(
                participacao=participacao,
                novo_estado=(
                    EstadoParticipacaoFisioterapia.REALIZADO
                ),
                utilizador=request.user,
                motivo=(
                    "Presença validada em conjunto."
                ),
            )

        _registar_alteracao_estado_sessao(
            sessao=sessao,
            estado_anterior=estado_anterior_sessao,
            utilizador=request.user,
        )

    messages.success(
        request,
        (
            f"{len(participacoes)} presença(s) "
            "marcada(s) como realizada(s)."
        ),
    )

    return redirect(
        "fisioterapia:detalhe_sessao",
        pk=sessao.pk,
    )


@require_POST
@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def cancelar_sessao(request, pk):
    with transaction.atomic():
        sessao = get_object_or_404(
            SessaoFisioterapia.objects
            .select_for_update()
            .select_related("profissional"),
            pk=pk,
        )

        if not sessao.pode_editar(request.user):
            raise PermissionDenied(
                (
                    "Só o fisioterapeuta responsável "
                    "pode cancelar esta sessão."
                )
            )

        motivo = request.POST.get(
            "motivo",
            "",
        ).strip()

        if not motivo:
            motivo = (
                "Sessão cancelada pelo fisioterapeuta."
            )

        estado_anterior_sessao = sessao.estado

        executar_cancelamento_sessao(
            sessao=sessao,
            utilizador=request.user,
            motivo=motivo,
        )

        _registar_alteracao_estado_sessao(
            sessao=sessao,
            estado_anterior=estado_anterior_sessao,
            utilizador=request.user,
        )

    messages.success(
        request,
        "Sessão cancelada.",
    )

    return redirect(
        "fisioterapia:detalhe_sessao",
        pk=sessao.pk,
    )


@login_required
@grupos_permitidos(*GRUPOS_CLINICOS)
def registos_utente(request, utente_id):
    utente = get_object_or_404(
        Utente.objects.select_related("quarto"),
        pk=utente_id,
    )

    registos_base = _registos_visiveis(
        request.user,
        RegistoFisioterapia.objects.filter(
            utente=utente
        ),
    )

    q = request.GET.get(
        "q",
        "",
    ).strip()

    data = parse_date(
        request.GET.get("data", "")
    )

    profissional_id = request.GET.get(
        "profissional",
        "",
    ).strip()

    intervencao_id = request.GET.get(
        "intervencao",
        "",
    ).strip()

    visibilidade = request.GET.get(
        "visibilidade",
        "",
    ).strip()

    profissionais_registos = (
        User.objects
        .filter(
            pk__in=registos_base.values_list(
                "profissional_id",
                flat=True,
            )
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    intervencoes_registos = (
        TipoIntervencaoFisioterapia.objects
        .filter(
            registos__in=registos_base
        )
        .distinct()
        .order_by(
            "area",
            "ordem",
            "categoria",
            "nome",
        )
    )

    registos = registos_base

    if q:
        registos = registos.filter(
            Q(tipo_trabalho__icontains=q)
            | Q(trabalho_realizado__icontains=q)
            | Q(resposta_utente__icontains=q)
            | Q(plano_seguinte__icontains=q)
            | Q(
                tipos_intervencao__nome__icontains=q
            )
            | Q(
                profissional__first_name__icontains=q
            )
            | Q(
                profissional__last_name__icontains=q
            )
            | Q(
                profissional__username__icontains=q
            )
        )

    if data:
        registos = registos.filter(
            data_registo__date=data
        )

    if profissional_id.isdigit():
        registos = registos.filter(
            profissional_id=profissional_id
        )

    if intervencao_id.isdigit():
        registos = registos.filter(
            tipos_intervencao__id=intervencao_id
        )

    visibilidades_validas = {
        valor
        for valor, _ in VisibilidadeRegisto.choices
    }

    if visibilidade in visibilidades_validas:
        registos = registos.filter(
            visibilidade=visibilidade
        )

    registos = (
        registos
        .select_related(
            "profissional",
            "participacao__sessao",
        )
        .prefetch_related(
            "tipos_intervencao"
        )
        .distinct()
        .order_by("-data_registo")
    )

    return render(
        request,
        "fisioterapia/registos_utente.html",
        {
            "utente": utente,
            "registos": registos,
            "pode_criar": (
                _utilizador_e_fisioterapeuta(
                    request.user
                )
            ),
            "q": q,
            "data": data,
            "profissional_id": profissional_id,
            "intervencao_id": intervencao_id,
            "visibilidade": visibilidade,
            "profissionais_registos": (
                profissionais_registos
            ),
            "intervencoes_registos": (
                intervencoes_registos
            ),
            "visibilidades": (
                VisibilidadeRegisto.choices
            ),
            "tem_filtros": bool(
                q
                or data
                or profissional_id
                or intervencao_id
                or visibilidade
            ),
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def criar_registo(
    request,
    utente_id,
    participacao_id=None,
):
    utente = get_object_or_404(
        Utente,
        pk=utente_id,
    )

    participacao = None

    if participacao_id is not None:
        participacao = get_object_or_404(
            ParticipacaoFisioterapia.objects
            .select_related(
                "sessao__profissional",
                "utente",
            )
            .prefetch_related(
                "sessao__tipos_intervencao"
            ),
            pk=participacao_id,
            utente=utente,
        )

        if not participacao.sessao.pode_editar(
            request.user
        ):
            raise PermissionDenied(
                (
                    "Apenas o fisioterapeuta responsável "
                    "pela sessão pode criar este registo."
                )
            )

        if (
            participacao.estado
            != EstadoParticipacaoFisioterapia.REALIZADO
        ):
            messages.warning(
                request,
                (
                    "O registo clínico associado à sessão "
                    "só pode ser criado depois de validar "
                    "que o utente realizou a sessão."
                ),
            )

            return redirect(
                "fisioterapia:detalhe_sessao",
                pk=participacao.sessao_id,
            )

    area_registo = (
        participacao.sessao.area
        if participacao
        else _area_principal_utilizador(request.user)
    )

    if request.method == "POST":
        form = RegistoFisioterapiaForm(
            request.POST,
            participacao=participacao,
            area=area_registo,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    registo = form.save(
                        commit=False
                    )

                    registo.utente = utente
                    registo.participacao = participacao
                    registo.area = area_registo
                    registo.profissional = request.user

                    registo.full_clean()
                    registo.save()

                    form.save_m2m()

            except ValidationError as erro:
                form.add_error(
                    None,
                    " ".join(erro.messages),
                )

            else:
                messages.success(
                    request,
                    "Registo de fisioterapia criado.",
                )

                if participacao:
                    return redirect(
                        "fisioterapia:detalhe_sessao",
                        pk=participacao.sessao_id,
                    )

                return redirect(
                    "fisioterapia:registos_utente",
                    utente_id=utente.pk,
                )
    else:
        form = RegistoFisioterapiaForm(
            participacao=participacao,
            area=area_registo,
        )

    return render(
        request,
        "fisioterapia/form_registo.html",
        {
            "form": form,
            "utente": utente,
            "participacao": participacao,
            "registo": None,
            "area_reabilitacao": AreaReabilitacao(
                area_registo
            ).label,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def editar_registo(request, pk):
    registo = get_object_or_404(
        RegistoFisioterapia.objects
        .select_related(
            "utente",
            "participacao__sessao",
        )
        .prefetch_related(
            "tipos_intervencao"
        ),
        pk=pk,
    )

    if not registo.pode_editar(request.user):
        raise PermissionDenied(
            "Só o autor pode editar este registo."
        )

    if request.method == "POST":
        form = RegistoFisioterapiaForm(
            request.POST,
            instance=registo,
            area=registo.area,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    registo = form.save(
                        commit=False
                    )

                    registo.full_clean()
                    registo.save()

                    form.save_m2m()

            except ValidationError as erro:
                form.add_error(
                    None,
                    " ".join(erro.messages),
                )

            else:
                messages.success(
                    request,
                    (
                        "Registo de fisioterapia "
                        "atualizado."
                    ),
                )

                return redirect(
                    "fisioterapia:registos_utente",
                    utente_id=registo.utente_id,
                )
    else:
        form = RegistoFisioterapiaForm(
            instance=registo,
            area=registo.area,
        )

    return render(
        request,
        "fisioterapia/form_registo.html",
        {
            "form": form,
            "utente": registo.utente,
            "participacao": registo.participacao,
            "registo": registo,
            "area_reabilitacao": registo.get_area_display(),
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_CLINICOS)
def detalhe_registo(request, pk):
    registo = get_object_or_404(
        RegistoFisioterapia.objects
        .select_related(
            "utente",
            "profissional",
            "participacao__sessao",
        )
        .prefetch_related(
            "tipos_intervencao"
        ),
        pk=pk,
    )

    if not registo.pode_ver(request.user):
        raise PermissionDenied(
            (
                "Não tem autorização para "
                "consultar este registo."
            )
        )

    return render(
        request,
        "fisioterapia/detalhe_registo.html",
        {
            "registo": registo,
            "pode_editar": registo.pode_editar(
                request.user
            ),
        },
    )

@login_required
@grupos_permitidos(*GRUPOS_REABILITACAO)
def alertas_clinicos(request):
    agora = timezone.now()
    limite_quedas = agora - timedelta(hours=24)

    quedas_recentes = (
        RegistoQueda.objects
        .filter(
            data_hora_queda__gte=limite_quedas,
            data_hora_queda__lte=agora,
            registo_enfermagem__utente__data_saida__isnull=True,
        )
        .select_related(
            "registo_enfermagem",
            "registo_enfermagem__utente",
            "registo_enfermagem__utente__quarto",
            "registo_enfermagem__profissional",
        )
    )

    quedas_recentes = filtrar_registos_visiveis(
        quedas_recentes,
        request.user,
        AREA_CLINICA_ENFERMAGEM,
        campo_autor=(
            "registo_enfermagem__profissional_id"
        ),
        campo_visibilidade=(
            "registo_enfermagem__visibilidade"
        ),
    )

    isolamentos_ativos = (
        Isolamento.objects
        .filter(
            ativo=True,
            utente__data_saida__isnull=True,
        )
        .select_related(
            "utente",
            "utente__quarto",
            "criado_por",
        )
    )

    pesquisa = request.GET.get(
        "q",
        "",
    ).strip()

    if pesquisa:
        filtro_utente = (
            Q(
                registo_enfermagem__utente__nome__icontains=(
                    pesquisa
                )
            )
            | Q(
                registo_enfermagem__utente__numero_processo__icontains=(
                    pesquisa
                )
            )
            | Q(
                registo_enfermagem__utente__quarto__codigo__icontains=(
                    pesquisa
                )
            )
        )

        quedas_recentes = quedas_recentes.filter(
            filtro_utente
        )

        isolamentos_ativos = (
            isolamentos_ativos.filter(
                Q(utente__nome__icontains=pesquisa)
                | Q(
                    utente__numero_processo__icontains=(
                        pesquisa
                    )
                )
                | Q(
                    utente__quarto__codigo__icontains=(
                        pesquisa
                    )
                )
            )
        )

    quedas_recentes = quedas_recentes.order_by(
        "-data_hora_queda"
    )

    isolamentos_ativos = isolamentos_ativos.order_by(
        "utente__quarto__piso",
        "utente__quarto__codigo",
        "utente__nome",
    )

    context = {
        "quedas_recentes": quedas_recentes,
        "isolamentos_ativos": isolamentos_ativos,
        "total_quedas_recentes": (
            quedas_recentes.count()
        ),
        "total_isolamentos_ativos": (
            isolamentos_ativos.count()
        ),
        "limite_quedas": limite_quedas,
        "pesquisa": pesquisa,
    }

    return render(
        request,
        "fisioterapia/alertas_clinicos.html",
        context,
    )


def _areas_reabilitacao_utilizador(utilizador):
    grupos = set(
        utilizador.groups.values_list("name", flat=True)
    )

    return [
        area
        for area, grupo in GRUPO_POR_AREA_REABILITACAO.items()
        if grupo in grupos
    ]


def _area_principal_utilizador(utilizador):
    areas = _areas_reabilitacao_utilizador(utilizador)
    return areas[0] if areas else AreaReabilitacao.FISIOTERAPIA
