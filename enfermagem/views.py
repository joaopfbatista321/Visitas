from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from clinica.permissoes import (
    filtrar_registos_visiveis,
    utilizador_e_responsavel_area,
    utilizador_pode_editar_registo,
    utilizador_pode_ver_registo,
    utilizador_tem_acesso_area,
)
from visitas.models import Utente

from .forms import (
    AusenciaUtenteForm,
    CabecalhoRegistoQuedaForm,
    FiltroAusenciasForm,
    RegressoAusenciaForm,
    RegistoEnfermagemForm,
    RegistoQuedaForm,
)
from .models import (
    AREA_CLINICA_ENFERMAGEM,
    AcaoHistoricoClinico,
    AusenciaUtente,
    EstadoAusenciaUtente,
    EstadoNotificacaoInstitucional,
    FatorContribuinteQueda,
    GravidadeQueda,
    HistoricoRegistoEnfermagem,
    HistoricoRegistoQueda,
    IntervencaoQueda,
    LesaoIdentificada,
    LocalQueda,
    LocalizacaoLesao,
    MedidaCorretivaQueda,
    RegistoEnfermagem,
    RegistoQueda,
    TipoQueda,
    TipoRegistoEnfermagem,
)
from .servicos_ausencias import (
    cancelar_ausencia as executar_cancelamento_ausencia,
    guardar_ausencia,
    terminar_ausencia as executar_regresso_ausencia,
)


def _mensagens_validacao(erro):
    if hasattr(erro, "message_dict"):
        return [
            mensagem
            for mensagens in erro.message_dict.values()
            for mensagem in mensagens
        ]

    return erro.messages


def _adicionar_erros_formulario(
    formulario,
    erro,
):
    if hasattr(erro, "message_dict"):
        for campo, mensagens in erro.message_dict.items():
            campo_formulario = (
                campo
                if campo in formulario.fields
                else None
            )

            for mensagem in mensagens:
                formulario.add_error(
                    campo_formulario,
                    mensagem,
                )
    else:
        for mensagem in erro.messages:
            formulario.add_error(
                None,
                mensagem,
            )


def _utente_ativo_ou_erro(utente):
    if utente.data_saida:
        raise PermissionDenied(
            "Não é possível criar novos registos "
            "para um utente com alta."
        )


def _utilizador_pode_abrir_historico(
    utilizador,
    utente,
):
    if utilizador_tem_acesso_area(
        utilizador,
        AREA_CLINICA_ENFERMAGEM,
    ):
        return True

    return RegistoEnfermagem.objects.filter(
        utente=utente,
        profissional=utilizador,
    ).exists()


def _nomes_escolhas(valores, escolhas):
    mapa = dict(escolhas)

    return [
        mapa.get(valor, valor)
        for valor in (valores or [])
    ]


def _texto_escolhas(valores, escolhas):
    return ", ".join(
        _nomes_escolhas(valores, escolhas)
    )


def _resumo_resposta_queda(queda):
    partes = [
        (
            "Tipo de queda: "
            f"{queda.get_tipo_queda_display()}."
        ),
        (
            "Grau de lesão: "
            f"{queda.get_gravidade_display()}."
        ),
    ]

    lesoes = _texto_escolhas(
        queda.lesoes_identificadas,
        LesaoIdentificada.choices,
    )

    if lesoes:
        partes.append(
            f"Lesões identificadas: {lesoes}."
        )


def _exigir_enfermagem(utilizador):
    if not utilizador_e_responsavel_area(
        utilizador,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Apenas a equipa de Enfermagem pode "
            "gerir ausências e transferências."
        )


def _pisos_disponiveis():
    modelo_quarto = (
        Utente._meta
        .get_field("quarto")
        .remote_field.model
    )
    campo_piso = modelo_quarto._meta.get_field("piso")
    nomes = dict(campo_piso.flatchoices)

    valores = (
        Utente.objects
        .filter(quarto__isnull=False)
        .exclude(quarto__piso="")
        .values_list("quarto__piso", flat=True)
        .distinct()
        .order_by("quarto__piso")
    )

    return [
        (valor, nomes.get(valor, valor))
        for valor in valores
    ]


def _mensagem_sincronizacao(resultado):
    partes = []

    if resultado["canceladas"]:
        partes.append(
            f"{resultado['canceladas']} marcação(ões) "
            "cancelada(s)"
        )

    if resultado["repostas"]:
        partes.append(
            f"{resultado['repostas']} marcação(ões) "
            "reposta(s)"
        )

    if not partes:
        return "Não existiam marcações a alterar."

    return "; ".join(partes) + "."

    localizacoes = _texto_escolhas(
        queda.localizacoes_lesao,
        LocalizacaoLesao.choices,
    )

    if localizacoes:
        partes.append(
            "Localização das lesões: "
            f"{localizacoes}."
        )

    if queda.reavaliacao_morse_estado:
        texto = (
            "Reavaliação Morse: "
            f"{queda.get_reavaliacao_morse_estado_display()}"
        )

        if queda.score_morse_pos is not None:
            texto += (
                f" — score {queda.score_morse_pos}"
            )

        partes.append(texto + ".")

    partes.append(
        "Notificação institucional: "
        f"{queda.get_notificacao_institucional_estado_display()}."
    )

    return "\n".join(partes)


def _sincronizar_registo_com_queda(
    registo,
    queda,
):
    registo.observacao = (
        queda.descricao_ocorrencia
    )

    intervencoes = _texto_escolhas(
        queda.intervencoes_realizadas,
        IntervencaoQueda.choices,
    )

    if queda.intervencao_outra:
        intervencoes = " — ".join(
            parte
            for parte in [
                intervencoes,
                queda.intervencao_outra,
            ]
            if parte
        )

    registo.cuidados_realizados = intervencoes

    registo.resposta_utente = (
        _resumo_resposta_queda(queda)
    )

    medidas = _texto_escolhas(
        queda.medidas_corretivas,
        MedidaCorretivaQueda.choices,
    )

    if queda.medida_corretiva_outra:
        medidas = " — ".join(
            parte
            for parte in [
                medidas,
                queda.medida_corretiva_outra,
            ]
            if parte
        )

    if queda.observacoes:
        medidas = "\n".join(
            parte
            for parte in [
                medidas,
                queda.observacoes,
            ]
            if parte
        )

    registo.plano_cuidados = medidas


def _converter_data(valor):
    if not valor:
        return None

    try:
        return datetime.strptime(
            valor,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return None


@login_required
def registos_utente(request, utente_pk):
    utente = get_object_or_404(
        Utente.objects.select_related("quarto"),
        pk=utente_pk,
    )

    if not _utilizador_pode_abrir_historico(
        request.user,
        utente,
    ):
        raise PermissionDenied(
            "Não tem autorização para consultar "
            "os registos de Enfermagem."
        )

    registos = (
        RegistoEnfermagem.objects
        .filter(utente=utente)
        .select_related(
            "tipo_registo",
            "profissional",
            "queda",
        )
    )

    registos = filtrar_registos_visiveis(
        registos,
        request.user,
        AREA_CLINICA_ENFERMAGEM,
    )

    pode_criar = (
        not utente.data_saida
        and utilizador_e_responsavel_area(
            request.user,
            AREA_CLINICA_ENFERMAGEM,
        )
    )

    return render(
        request,
        "enfermagem/registos_utente.html",
        {
            "utente": utente,
            "registos": registos,
            "pode_criar": pode_criar,
        },
    )


@login_required
def criar_registo(request, utente_pk):
    utente = get_object_or_404(
        Utente,
        pk=utente_pk,
    )

    if not utilizador_e_responsavel_area(
        request.user,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Apenas a equipa de Enfermagem pode "
            "criar estes registos."
        )

    _utente_ativo_ou_erro(utente)

    form = RegistoEnfermagemForm(
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        registo = form.save(commit=False)
        registo.utente = utente
        registo.profissional = request.user

        try:
            registo.full_clean()

            with transaction.atomic():
                registo.save()

                HistoricoRegistoEnfermagem.objects.create(
                    registo=registo,
                    acao=AcaoHistoricoClinico.CRIADO,
                    dados=registo.dados_para_historico(),
                    profissional=request.user,
                )

        except ValidationError as erro:
            _adicionar_erros_formulario(
                form,
                erro,
            )
        else:
            messages.success(
                request,
                "Registo de Enfermagem criado.",
            )

            return redirect(
                "enfermagem:detalhe_registo",
                pk=registo.pk,
            )

    return render(
        request,
        "enfermagem/form_registo.html",
        {
            "form": form,
            "utente": utente,
            "registo": None,
        },
    )


@login_required
def detalhe_registo(request, pk):
    registo = get_object_or_404(
        RegistoEnfermagem.objects.select_related(
            "utente",
            "utente__quarto",
            "tipo_registo",
            "profissional",
        ),
        pk=pk,
    )

    if not utilizador_pode_ver_registo(
        request.user,
        registo,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Não tem autorização para consultar "
            "este registo."
        )

    if registo.tem_registo_queda:
        return redirect(
            "enfermagem:detalhe_queda",
            pk=registo.queda.pk,
        )

    return render(
        request,
        "enfermagem/detalhe_registo.html",
        {
            "registo": registo,
            "pode_editar": (
                utilizador_pode_editar_registo(
                    request.user,
                    registo,
                    AREA_CLINICA_ENFERMAGEM,
                )
            ),
        },
    )


@login_required
def editar_registo(request, pk):
    registo = get_object_or_404(
        RegistoEnfermagem.objects.select_related(
            "utente",
            "tipo_registo",
            "profissional",
        ),
        pk=pk,
    )

    if not utilizador_pode_editar_registo(
        request.user,
        registo,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Apenas o autor pode alterar este registo."
        )

    if registo.tem_registo_queda:
        return redirect(
            "enfermagem:editar_queda",
            pk=registo.queda.pk,
        )

    form = RegistoEnfermagemForm(
        request.POST or None,
        instance=registo,
    )

    if request.method == "POST" and form.is_valid():
        registo = form.save(commit=False)
        registo.profissional = request.user

        try:
            registo.full_clean()

            with transaction.atomic():
                registo.save()

                HistoricoRegistoEnfermagem.objects.create(
                    registo=registo,
                    acao=AcaoHistoricoClinico.ALTERADO,
                    dados=registo.dados_para_historico(),
                    profissional=request.user,
                )

        except ValidationError as erro:
            _adicionar_erros_formulario(
                form,
                erro,
            )
        else:
            messages.success(
                request,
                "Registo de Enfermagem atualizado.",
            )

            return redirect(
                "enfermagem:detalhe_registo",
                pk=registo.pk,
            )

    return render(
        request,
        "enfermagem/form_registo.html",
        {
            "form": form,
            "utente": registo.utente,
            "registo": registo,
        },
    )


@login_required
def criar_queda(request, utente_pk):
    utente = get_object_or_404(
        Utente.objects.select_related("quarto"),
        pk=utente_pk,
    )

    if not utilizador_e_responsavel_area(
        request.user,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Apenas a equipa de Enfermagem pode "
            "registar quedas."
        )

    _utente_ativo_ou_erro(utente)

    cabecalho_form = CabecalhoRegistoQuedaForm(
        request.POST or None,
        prefix="cabecalho",
    )

    queda_form = RegistoQuedaForm(
        request.POST or None,
        prefix="queda",
    )

    formularios_validos = (
        request.method == "POST"
        and cabecalho_form.is_valid()
        and queda_form.is_valid()
    )

    if formularios_validos:
        try:
            tipo_queda = (
                TipoRegistoEnfermagem.objects.get(
                    codigo="queda",
                    ativo=True,
                )
            )
        except TipoRegistoEnfermagem.DoesNotExist:
            messages.error(
                request,
                (
                    "O tipo de registo 'queda' não está "
                    "ativo. Verifique a configuração "
                    "no Django Admin."
                ),
            )
        else:
            registo = cabecalho_form.save(
                commit=False
            )

            queda = queda_form.save(
                commit=False
            )

            registo.utente = utente
            registo.tipo_registo = tipo_queda
            registo.profissional = request.user

            _sincronizar_registo_com_queda(
                registo,
                queda,
            )

            try:
                with transaction.atomic():
                    registo.full_clean()
                    registo.save()

                    queda.registo_enfermagem = registo
                    queda.preencher_identificacao_utente()
                    queda.full_clean()
                    queda.save()

                    HistoricoRegistoEnfermagem.objects.create(
                        registo=registo,
                        acao=AcaoHistoricoClinico.CRIADO,
                        dados=(
                            registo.dados_para_historico()
                        ),
                        profissional=request.user,
                    )

                    HistoricoRegistoQueda.objects.create(
                        registo=queda,
                        acao=AcaoHistoricoClinico.CRIADO,
                        dados=queda.dados_para_historico(),
                        profissional=request.user,
                    )

            except ValidationError as erro:
                _adicionar_erros_formulario(
                    queda_form,
                    erro,
                )
            else:
                messages.success(
                    request,
                    "Registo de queda criado.",
                )

                if queda.notificacao_fora_prazo:
                    messages.warning(
                        request,
                        (
                            "A queda foi notificada mais de "
                            "24 horas após a ocorrência."
                        ),
                    )

                return redirect(
                    "enfermagem:detalhe_queda",
                    pk=queda.pk,
                )

    return render(
        request,
        "enfermagem/form_queda.html",
        {
            "cabecalho_form": cabecalho_form,
            "queda_form": queda_form,
            "utente": utente,
            "queda": None,
        },
    )


@login_required
def detalhe_queda(request, pk):
    queda = get_object_or_404(
        RegistoQueda.objects.select_related(
            "registo_enfermagem",
            "registo_enfermagem__utente",
            "registo_enfermagem__utente__quarto",
            "registo_enfermagem__tipo_registo",
            "registo_enfermagem__profissional",
        ),
        pk=pk,
    )

    registo = queda.registo_enfermagem

    if not utilizador_pode_ver_registo(
        request.user,
        registo,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Não tem autorização para consultar "
            "este registo de queda."
        )

    return render(
        request,
        "enfermagem/detalhe_queda.html",
        {
            "queda": queda,
            "registo": registo,
            "lesoes": _nomes_escolhas(
                queda.lesoes_identificadas,
                LesaoIdentificada.choices,
            ),
            "localizacoes_lesao": _nomes_escolhas(
                queda.localizacoes_lesao,
                LocalizacaoLesao.choices,
            ),
            "fatores_contribuintes": _nomes_escolhas(
                queda.fatores_contribuintes,
                FatorContribuinteQueda.choices,
            ),
            "intervencoes": _nomes_escolhas(
                queda.intervencoes_realizadas,
                IntervencaoQueda.choices,
            ),
            "medidas_corretivas": _nomes_escolhas(
                queda.medidas_corretivas,
                MedidaCorretivaQueda.choices,
            ),
            "pode_editar": (
                utilizador_pode_editar_registo(
                    request.user,
                    registo,
                    AREA_CLINICA_ENFERMAGEM,
                )
            ),
        },
    )


@login_required
def editar_queda(request, pk):
    queda = get_object_or_404(
        RegistoQueda.objects.select_related(
            "registo_enfermagem",
            "registo_enfermagem__utente",
            "registo_enfermagem__tipo_registo",
            "registo_enfermagem__profissional",
        ),
        pk=pk,
    )

    registo = queda.registo_enfermagem

    if not utilizador_pode_editar_registo(
        request.user,
        registo,
        AREA_CLINICA_ENFERMAGEM,
    ):
        raise PermissionDenied(
            "Apenas o autor pode alterar este registo."
        )

    cabecalho_form = CabecalhoRegistoQuedaForm(
        request.POST or None,
        instance=registo,
        prefix="cabecalho",
    )

    queda_form = RegistoQuedaForm(
        request.POST or None,
        instance=queda,
        prefix="queda",
    )

    formularios_validos = (
        request.method == "POST"
        and cabecalho_form.is_valid()
        and queda_form.is_valid()
    )

    if formularios_validos:
        registo = cabecalho_form.save(
            commit=False
        )

        queda = queda_form.save(
            commit=False
        )

        registo.profissional = request.user

        _sincronizar_registo_com_queda(
            registo,
            queda,
        )

        if not queda.identificacao_utente:
            queda.preencher_identificacao_utente()

        try:
            registo.full_clean()
            queda.full_clean()

            with transaction.atomic():
                registo.save()
                queda.save()

                HistoricoRegistoEnfermagem.objects.create(
                    registo=registo,
                    acao=AcaoHistoricoClinico.ALTERADO,
                    dados=registo.dados_para_historico(),
                    profissional=request.user,
                )

                HistoricoRegistoQueda.objects.create(
                    registo=queda,
                    acao=AcaoHistoricoClinico.ALTERADO,
                    dados=queda.dados_para_historico(),
                    profissional=request.user,
                )

        except ValidationError as erro:
            _adicionar_erros_formulario(
                queda_form,
                erro,
            )
        else:
            messages.success(
                request,
                "Registo de queda atualizado.",
            )

            return redirect(
                "enfermagem:detalhe_queda",
                pk=queda.pk,
            )

    return render(
        request,
        "enfermagem/form_queda.html",
        {
            "cabecalho_form": cabecalho_form,
            "queda_form": queda_form,
            "utente": registo.utente,
            "queda": queda,
        },
    )


@login_required
def lista_quedas(request):
    if not utilizador_tem_acesso_area(
        request.user,
        AREA_CLINICA_ENFERMAGEM,
    ):
        tem_registos_proprios = (
            RegistoQueda.objects.filter(
                registo_enfermagem__profissional=(
                    request.user
                )
            ).exists()
        )

        if not tem_registos_proprios:
            raise PermissionDenied(
                "Não tem autorização para consultar "
                "os registos de quedas."
            )

    quedas = (
        RegistoQueda.objects
        .select_related(
            "registo_enfermagem",
            "registo_enfermagem__utente",
            "registo_enfermagem__utente__quarto",
            "registo_enfermagem__profissional",
        )
    )

    quedas = filtrar_registos_visiveis(
        quedas,
        request.user,
        AREA_CLINICA_ENFERMAGEM,
        campo_autor=(
            "registo_enfermagem__profissional_id"
        ),
        campo_visibilidade=(
            "registo_enfermagem__visibilidade"
        ),
    )

    q = request.GET.get("q", "").strip()
    gravidade = request.GET.get(
        "gravidade",
        "",
    )
    tipo_queda = request.GET.get(
        "tipo_queda",
        "",
    )
    local = request.GET.get("local", "")
    notificacao = request.GET.get(
        "notificacao",
        "",
    )
    data_de_texto = request.GET.get("data_de", "")
    data_ate_texto = request.GET.get(
        "data_ate",
        "",
    )

    data_de = _converter_data(data_de_texto)
    data_ate = _converter_data(data_ate_texto)

    if q:
        quedas = quedas.filter(
            Q(
                registo_enfermagem__utente__nome__icontains=q
            )
            | Q(
                registo_enfermagem__utente__numero_processo__icontains=q
            )
            | Q(
                descricao_ocorrencia__icontains=q
            )
            | Q(
                registo_enfermagem__profissional__first_name__icontains=q
            )
            | Q(
                registo_enfermagem__profissional__last_name__icontains=q
            )
            | Q(
                registo_enfermagem__profissional__username__icontains=q
            )
        )

    if gravidade:
        quedas = quedas.filter(
            gravidade=gravidade
        )

    if tipo_queda:
        quedas = quedas.filter(
            tipo_queda=tipo_queda
        )

    if local:
        quedas = quedas.filter(
            local_queda=local
        )

    if notificacao:
        quedas = quedas.filter(
            notificacao_institucional_estado=(
                notificacao
            )
        )

    if data_de:
        quedas = quedas.filter(
            data_hora_queda__date__gte=data_de
        )

    if data_ate:
        quedas = quedas.filter(
            data_hora_queda__date__lte=data_ate
        )

    pode_criar = utilizador_e_responsavel_area(
        request.user,
        AREA_CLINICA_ENFERMAGEM,
    )

    return render(
        request,
        "enfermagem/lista_quedas.html",
        {
            "quedas": quedas,
            "q": q,
            "gravidade": gravidade,
            "tipo_queda": tipo_queda,
            "local": local,
            "notificacao": notificacao,
            "data_de": data_de_texto,
            "data_ate": data_ate_texto,
            "gravidades": GravidadeQueda.choices,
            "tipos_queda": TipoQueda.choices,
            "locais": LocalQueda.choices,
            "estados_notificacao": (
                EstadoNotificacaoInstitucional.choices
            ),
            "pode_criar": pode_criar,
        },
    )


@login_required
def lista_ausencias(request):
    _exigir_enfermagem(request.user)

    base = (
        AusenciaUtente.objects
        .select_related(
            "utente",
            "utente__quarto",
            "criado_por",
            "estado_atualizado_por",
        )
    )

    formulario = FiltroAusenciasForm(
        request.GET or None,
        pisos=_pisos_disponiveis(),
    )

    ausencias = base

    if formulario.is_valid():
        q = formulario.cleaned_data["q"]
        estado = formulario.cleaned_data["estado"]
        tipo = formulario.cleaned_data["tipo"]
        piso = formulario.cleaned_data["piso"]

        if q:
            ausencias = ausencias.filter(
                Q(utente__nome__icontains=q)
                | Q(
                    utente__numero_processo__icontains=q
                )
                | Q(destino__icontains=q)
                | Q(motivo__icontains=q)
            )

        if estado:
            ausencias = ausencias.filter(estado=estado)

        if tipo:
            ausencias = ausencias.filter(tipo=tipo)

        if piso:
            ausencias = ausencias.filter(
                utente__quarto__piso=piso,
            )

    return render(
        request,
        "enfermagem/ausencias/lista.html",
        {
            "ausencias": ausencias,
            "formulario": formulario,
            "total_ativas": base.filter(
                estado=EstadoAusenciaUtente.ATIVA,
            ).count(),
            "total_terminadas": base.filter(
                estado=EstadoAusenciaUtente.TERMINADA,
            ).count(),
            "total_transferencias": base.filter(
                tipo="TRANSFERENCIA",
            ).count(),
        },
    )


@login_required
def criar_ausencia(request, utente_pk):
    _exigir_enfermagem(request.user)

    utente = get_object_or_404(
        Utente.objects.select_related("quarto"),
        pk=utente_pk,
    )
    _utente_ativo_ou_erro(utente)

    ausencia_existente = (
        AusenciaUtente.objects
        .filter(
            utente=utente,
            estado=EstadoAusenciaUtente.ATIVA,
        )
        .first()
    )

    if ausencia_existente:
        messages.warning(
            request,
            "Este utente já possui uma ausência ativa.",
        )
        return redirect(
            "enfermagem:detalhe_ausencia",
            pk=ausencia_existente.pk,
        )

    formulario = AusenciaUtenteForm(
        request.POST or None,
    )

    if request.method == "POST" and formulario.is_valid():
        ausencia = formulario.save(commit=False)
        ausencia.utente = utente

        try:
            ausencia, resultado = guardar_ausencia(
                ausencia,
                request.user,
            )
        except ValidationError as erro:
            _adicionar_erros_formulario(
                formulario,
                erro,
            )
        else:
            messages.success(
                request,
                "Ausência registada. "
                + _mensagem_sincronizacao(resultado),
            )
            return redirect(
                "enfermagem:detalhe_ausencia",
                pk=ausencia.pk,
            )

    return render(
        request,
        "enfermagem/ausencias/form.html",
        {
            "formulario": formulario,
            "utente": utente,
            "ausencia": None,
        },
    )


@login_required
def detalhe_ausencia(request, pk):
    _exigir_enfermagem(request.user)

    ausencia = get_object_or_404(
        AusenciaUtente.objects
        .select_related(
            "utente",
            "utente__quarto",
            "criado_por",
            "estado_atualizado_por",
        )
        .prefetch_related(
            "historico__profissional",
            (
                "participacoes_reabilitacao_canceladas"
                "__sessao"
            ),
        ),
        pk=pk,
    )

    return render(
        request,
        "enfermagem/ausencias/detalhe.html",
        {
            "ausencia": ausencia,
            "pode_alterar": (
                ausencia.estado
                == EstadoAusenciaUtente.ATIVA
            ),
        },
    )


@login_required
def editar_ausencia(request, pk):
    _exigir_enfermagem(request.user)

    ausencia = get_object_or_404(
        AusenciaUtente.objects.select_related(
            "utente",
            "utente__quarto",
        ),
        pk=pk,
    )

    if ausencia.estado != EstadoAusenciaUtente.ATIVA:
        raise PermissionDenied(
            "Apenas uma ausência ativa pode ser alterada."
        )

    formulario = AusenciaUtenteForm(
        request.POST or None,
        instance=ausencia,
    )

    if request.method == "POST" and formulario.is_valid():
        ausencia = formulario.save(commit=False)

        try:
            ausencia, resultado = guardar_ausencia(
                ausencia,
                request.user,
            )
        except ValidationError as erro:
            _adicionar_erros_formulario(
                formulario,
                erro,
            )
        else:
            messages.success(
                request,
                "Período da ausência atualizado. "
                + _mensagem_sincronizacao(resultado),
            )
            return redirect(
                "enfermagem:detalhe_ausencia",
                pk=ausencia.pk,
            )

    return render(
        request,
        "enfermagem/ausencias/form.html",
        {
            "formulario": formulario,
            "utente": ausencia.utente,
            "ausencia": ausencia,
        },
    )


@login_required
def registar_regresso_ausencia(request, pk):
    _exigir_enfermagem(request.user)

    ausencia = get_object_or_404(
        AusenciaUtente.objects.select_related(
            "utente",
            "utente__quarto",
        ),
        pk=pk,
        estado=EstadoAusenciaUtente.ATIVA,
    )

    formulario = RegressoAusenciaForm(
        request.POST or None,
        ausencia=ausencia,
    )

    if request.method == "POST" and formulario.is_valid():
        try:
            with transaction.atomic():
                observacoes = (
                    formulario.cleaned_data["observacoes"]
                    .strip()
                )

                if observacoes:
                    ausencia.observacoes = "\n".join(
                        parte
                        for parte in [
                            ausencia.observacoes,
                            "Regresso: " + observacoes,
                        ]
                        if parte
                    )
                    ausencia.save(
                        update_fields=[
                            "observacoes",
                            "atualizado_em",
                        ]
                    )

                ausencia, resultado = (
                    executar_regresso_ausencia(
                        ausencia,
                        request.user,
                        momento=formulario.cleaned_data[
                            "data_hora_regresso"
                        ],
                    )
                )
        except ValidationError as erro:
            _adicionar_erros_formulario(
                formulario,
                erro,
            )
        else:
            messages.success(
                request,
                "Regresso registado. "
                + _mensagem_sincronizacao(resultado),
            )
            return redirect(
                "enfermagem:detalhe_ausencia",
                pk=ausencia.pk,
            )

    return render(
        request,
        "enfermagem/ausencias/regresso.html",
        {
            "formulario": formulario,
            "ausencia": ausencia,
        },
    )


@require_POST
@login_required
def cancelar_ausencia(request, pk):
    _exigir_enfermagem(request.user)

    ausencia = get_object_or_404(
        AusenciaUtente,
        pk=pk,
        estado=EstadoAusenciaUtente.ATIVA,
    )

    try:
        ausencia, resultado = executar_cancelamento_ausencia(
            ausencia,
            request.user,
        )
    except ValidationError as erro:
        messages.error(
            request,
            " ".join(_mensagens_validacao(erro)),
        )
    else:
        messages.success(
            request,
            "Registo de ausência cancelado. "
            + _mensagem_sincronizacao(resultado),
        )

    return redirect(
        "enfermagem:detalhe_ausencia",
        pk=ausencia.pk,
    )
