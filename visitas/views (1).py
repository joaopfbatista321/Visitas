from datetime import timedelta, date

from django.contrib.auth.decorators import login_required
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import localdate
from django.db.models import Q
from django.core.paginator import Paginator
from config.decorators import grupos_permitidos
from .forms import (
    UtenteForm,
    VisitaForm,
    ExternoForm,
    UtenteSaidaForm,
    IsolamentoForm,
    MovimentoFinanceiroForm,
    TransporteForm,
    ViaturaForm,
    CondutorForm,
    IndisponibilidadeForm,
    PedidoTransporteForm,
    ValidarPedidoTransporteForm,
)

import json
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.urls import reverse
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_POST
from xhtml2pdf import pisa

from .models import (
    Visita,
    Utente,
    TipoAlta,
    TipoInternamento,
    Genero,
    Externo,
    Isolamento,
    MovimentoFinanceiro,
    Viatura,
    Condutor,
    PedidoTransporte,
    EstadoPedidoTransporte,
    Transporte,
    Indisponibilidade,
    EstadoTransporte,
    TipoDeslocacao,
    MeioTransporte,
)
from django.contrib import messages


GRUPOS_CONSULTA_UTENTES = (
    "UCCI_Rececao",
    "UCCI_Enfermagem",
    "UCCI_Medicos",
    "UCCI_Psicologia",
    "UCCI_Fisioterapia",
    "UCCI_ServicoSocial",
    "UCCI_Coordenacao",
)

GRUPOS_GESTAO_UTENTES = (
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)

GRUPOS_ISOLAMENTOS = (
    "UCCI_Enfermagem",
    "UCCI_Medicos",
    "UCCI_Coordenacao",
)

GRUPOS_FINANCEIRO = (
    "Financeiro",
    "UCCI_Coordenacao",
)

GRUPOS_TRANSPORTES = (
    "UCCI_Rececao",
    "UCCI_Transportes",
    "UCCI_Coordenacao",
)

GRUPOS_PLANEAMENTO_TRANSPORTES = (
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)

GRUPOS_CRIAR_PEDIDO_TRANSPORTE = (
    "UCCI_Enfermagem",
    "UCCI_Medicos",
    "UCCI_ServicoSocial",
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)

GRUPOS_VALIDAR_PEDIDO_TRANSPORTE = (
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)


# ============================================================
# UTENTES
# ============================================================

@login_required
@grupos_permitidos(*GRUPOS_CONSULTA_UTENTES)
def lista_utentes(request):
    # Filtros vindos da querystring
    estado = request.GET.get("estado", "ativos")  # 'ativos', 'inativos', 'todos'
    q = request.GET.get("q", "").strip()

    # NOVO: parâmetros de ordenação
    ordenar = request.GET.get("ordenar", "nome")      # nome, numero_processo, quarto, data_entrada, data_saida, estado
    direcao = request.GET.get("direcao", "asc")       # asc ou desc

    utentes = Utente.objects.all()

    # Filtro de estado
    if estado == "ativos":
        utentes = utentes.filter(data_saida__isnull=True)
    elif estado == "inativos":
        utentes = utentes.filter(data_saida__isnull=False)

    # Pesquisa
    if q:
        utentes = utentes.filter(
            Q(nome__icontains=q)
            | Q(numero_processo__icontains=q)
            | Q(quarto__codigo__icontains=q)
        )

    # Annotate para saber se é ativo (1) ou não (0)
    utentes = utentes.annotate(
        is_ativo=models.Case(
            models.When(data_saida__isnull=True, then=models.Value(1)),
            default=models.Value(0),
            output_field=models.IntegerField(),
        )
    )

    # Mapeamento dos nomes de colunas do front → campos da BD
    ordenar_map = {
        "nome": "nome",
        "numero_processo": "numero_processo",
        "quarto": "quarto__codigo",   # se o teu quarto não tiver 'codigo', podes pôr só "quarto"
        "data_entrada": "data_entrada",
        "data_saida": "data_saida",
        "estado": "is_ativo",
    }

    campo = ordenar_map.get(ordenar, "nome")

    # Direção
    if direcao == "desc":
        campo = f"-{campo}"

    # Ordem final:
    # - se não estivermos a ordenar por estado, mantemos "ativos primeiro"
    order_by_list = []
    if ordenar != "estado":
        order_by_list.append("-is_ativo")
    order_by_list.append(campo)
    # secundário por nome para estabilizar
    if ordenar != "nome":
        order_by_list.append("nome")

    utentes = utentes.order_by(*order_by_list)

    # Paginação
    paginator = Paginator(utentes, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "estado": estado,
        "q": q,
        "ordenar": ordenar,
        "direcao": direcao,
    }
    return render(request, "visitas/lista_utentes.html", context)



@login_required
@grupos_permitidos(*GRUPOS_CONSULTA_UTENTES)
def detalhe_utente(request, pk):
    utente = get_object_or_404(Utente, pk=pk)

    visitas = (
        Visita.objects
        .filter(utente=utente)
        .order_by("-data_hora_entrada")
    )

    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    if q:
        visitas = visitas.filter(
            Q(nome_visitante__icontains=q) |
            Q(parentesco__icontains=q) |
            Q(motivo__icontains=q)
        )

    if estado == "em_curso":
        visitas = visitas.filter(data_hora_saida__isnull=True)
    elif estado == "terminada":
        visitas = visitas.filter(data_hora_saida__isnull=False)

    if tipo:
        visitas = visitas.filter(tipo_visitante=tipo)

    is_financeiro = request.user.groups.filter(name="Financeiro").exists()

    context = {
        "utente": utente,
        "visitas": visitas,
        "is_financeiro": is_financeiro,
        "q": q,
        "estado": estado,
        "tipo": tipo,
        "tipos_visitante": Visita._meta.get_field("tipo_visitante").choices,
    }

    return render(request, "visitas/detalhe_utente.html", context)


@login_required
@grupos_permitidos(*GRUPOS_GESTAO_UTENTES)
def criar_utente(request):
    if request.method == "POST":
        form = UtenteForm(request.POST)
        if form.is_valid():
            utente = form.save(commit=False)
            if utente.registado_entrada_por is None:
                utente.registado_entrada_por = request.user
            utente.save()
            return redirect("visitas:detalhe_utente", pk=utente.pk)
    else:
        form = UtenteForm()

    return render(request, "visitas/form_utente.html", {
        "form": form,
        "utente": None,
    })


@login_required
@grupos_permitidos(*GRUPOS_GESTAO_UTENTES)
def editar_utente(request, pk):
    utente = get_object_or_404(Utente, pk=pk)
    data_saida_antiga = utente.data_saida

    if request.method == "POST":
        form = UtenteForm(request.POST, instance=utente)
        if form.is_valid():
            utente = form.save(commit=False)

            # Se passou a ter data de saída e ainda não tinha quem registou a saída
            if utente.data_saida and not data_saida_antiga and utente.registado_saida_por is None:
                utente.registado_saida_por = request.user

            utente.save()
            return redirect("visitas:detalhe_utente", pk=utente.pk)
    else:
        form = UtenteForm(instance=utente)

    return render(request, "visitas/form_utente.html", {
        "form": form,
        "utente": utente,
    })

@login_required
@grupos_permitidos(*GRUPOS_GESTAO_UTENTES)
def saida_utente(request, pk):
    utente = get_object_or_404(Utente, pk=pk)

    if request.method == "POST":
        form = UtenteSaidaForm(request.POST, instance=utente)
        if form.is_valid():
            utente = form.save(commit=False)
            utente.registado_saida_por = request.user
            utente.save()
            return redirect("visitas:detalhe_utente", pk=utente.pk)
    else:
        form = UtenteSaidaForm(instance=utente)

    return render(request, "visitas/saida_utente.html", {
        "utente": utente,
        "form": form,
    })




# ============================================================
# VISITAS (ligadas a utentes)
# ============================================================

@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def registar_visita_utente(request, utente_id):
    utente = get_object_or_404(Utente, pk=utente_id)

    # id da visita a copiar (se vier da querystring)
    copiar_de_id = request.GET.get("from")
    initial = {}
    visita_original = None

    if copiar_de_id:
        # garantes que a visita é do mesmo utente
        visita_original = get_object_or_404(
            Visita,
            pk=copiar_de_id,
            utente=utente
        )

        # Campos a reutilizar
        initial = {
            "tipo_visitante": visita_original.tipo_visitante,
            "nome_visitante": visita_original.nome_visitante,
            "documento_identificacao": visita_original.documento_identificacao,
            "telefone": visita_original.telefone,
            "parentesco": visita_original.parentesco,
            # normalmente queres nova data/hora,
            # por isso não copio estas (deixas o utilizador meter):
            # "data_hora_entrada": visita_original.data_hora_entrada,
            # "data_hora_saida": visita_original.data_hora_saida,
            "motivo": visita_original.motivo,
            "observacoes": visita_original.observacoes,
        }

    if request.method == "POST":
        form = VisitaForm(request.POST)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.utente = utente
            visita.registado_por = request.user
            # se quiseres no futuro ligar a nova visita à original,
            # aqui poderias fazer algo como: visita.reaberta_de = visita_original
            visita.save()
            return redirect("visitas:detalhe_utente", pk=utente.pk)
    else:
        form = VisitaForm(initial=initial)

    return render(request, "visitas/form_visita.html", {
        "form": form,
        "utente": utente,
    })



@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def registar_saida_visita(request, visita_id):
    visita = get_object_or_404(Visita, pk=visita_id)

    if visita.data_hora_saida is not None:
        return redirect("visitas:detalhe_utente", pk=visita.utente.pk)

    if request.method == "POST":
        visita.data_hora_saida = timezone.now()
        visita.save()
        return redirect("visitas:detalhe_utente", pk=visita.utente.pk)

    return render(request, "visitas/confirmar_saida_visita.html", {
        "visita": visita,
    })


# ============================================================
# EXTERNOS (prestadores de serviços, técnicos, etc.)
# ============================================================

@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def lista_externos(request):
    externos = Externo.objects.all().order_by("-data_hora_entrada")
    return render(request, "visitas/lista_externos.html", {
        "externos": externos,
    })


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def registar_entrada_externo(request):
    if request.method == "POST":
        form = ExternoForm(request.POST)
        if form.is_valid():
            externo = form.save(commit=False)
            externo.registado_por = request.user
            externo.save()
            return redirect("visitas:lista_externos")
    else:
        form = ExternoForm()

    return render(request, "visitas/form_externo.html", {
        "form": form,
        "externo": None,
    })


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def registar_saida_externo(request, pk):
    externo = get_object_or_404(Externo, pk=pk)

    if externo.data_hora_saida is not None:
        return redirect("visitas:lista_externos")

    if request.method == "POST":
        externo.data_hora_saida = timezone.now()
        externo.save()
        return redirect("visitas:lista_externos")

    return render(request, "visitas/confirmar_saida_externo.html", {
        "externo": externo,
    })


# ============================================================
# RELATÓRIOS E DASHBOARD
# ============================================================

@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def visitas_hoje(request):
    hoje = localdate()
    visitas = (
        Visita.objects
        .filter(data_hora_entrada__date=hoje)
        .select_related("utente")
        .order_by("-data_hora_entrada")
    )

    return render(request, "visitas/visitas_hoje.html", {
        "visitas": visitas,
        "hoje": hoje,
    })


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def visitas_ativas(request):
    visitas = (
        Visita.objects
        .filter(data_hora_saida__isnull=True)
        .select_related("utente")
        .order_by("-data_hora_entrada")
    )

    return render(request, "visitas/visitas_ativas.html", {
        "visitas": visitas,
    })


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def visitas_relatorio(request):
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    visitas = None

    if data_inicio and data_fim:
        visitas = (
            Visita.objects
            .filter(data_hora_entrada__date__range=[data_inicio, data_fim])
            .select_related("utente")
            .order_by("-data_hora_entrada")
        )

    return render(request, "visitas/visitas_relatorio.html", {
        "visitas": visitas,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    })



@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def dashboard_visitas(request):
    today = timezone.localdate()
    last_7_days = today - timedelta(days=6)

    # ---------------------------------------------------
    # FILTRO POR ANO (opcional)
    # ---------------------------------------------------
    # Anos disponíveis (com base na data_entrada dos utentes)
    anos_qs = Utente.objects.dates("data_entrada", "year").distinct()
    anos_disponiveis = [d.year for d in anos_qs]

    ano_param = request.GET.get("ano")
    try:
        ano = int(ano_param) if ano_param else None
    except ValueError:
        ano = None

    # ---------------------------------------------------
    # BASES DE QUERY (com ou sem filtro por ano)
    # ---------------------------------------------------
    utentes_base = Utente.objects.all()
    visitas_base = Visita.objects.all()

    if ano:
        # Utentes filtrados por ano de entrada
        utentes_base = utentes_base.filter(data_entrada__year=ano)
        # Visitas filtradas por ano da data de entrada
        visitas_base = visitas_base.filter(data_hora_entrada__year=ano)

    # ---------------------------------------------------
    # VISITAS - KPIs (respeitam o filtro por ano)
    # ---------------------------------------------------
    visitas_hoje = visitas_base.filter(
        data_hora_entrada__date=today
    ).count()

    visitas_semana = visitas_base.filter(
        data_hora_entrada__date__gte=last_7_days
    ).count()

    visitas_ativas = visitas_base.filter(
        data_hora_saida__isnull=True
    ).count()

    visitas_por_dia = (
        visitas_base
        .filter(data_hora_entrada__date__gte=last_7_days)
        .annotate(day=TruncDate("data_hora_entrada"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    # ---------------------------------------------------
    # UTENTES - KPIs (respeitam o filtro por ano)
    # ---------------------------------------------------
    # Total de utentes admitidos no período/análise
    utentes_total = utentes_base.count()

    # Ativos = ainda sem data_saida (no período de entrada analisado)
    utentes_ativos = utentes_base.filter(data_saida__isnull=True).count()
    utentes_inativos = utentes_total - utentes_ativos

    # Admissões no período:
    #  - se tiver ano => total de utentes com entrada nesse ano
    #  - se não tiver ano => últimos 30 dias
    if ano:
        admissoes_30 = utentes_base.count()
        admissoes_label = f"Admissões no ano {ano}"
    else:
        last_30_days = today - timedelta(days=30)
        admissoes_30 = Utente.objects.filter(data_entrada__gte=last_30_days).count()
        admissoes_label = "Admissões últimos 30 dias"

    # Altas (saídas) – se houver ano, filtra por data_saida__year
    if ano:
        altas_qs = Utente.objects.filter(data_saida__year=ano)
    else:
        altas_qs = Utente.objects.filter(data_saida__isnull=False)

    altas_total = altas_qs.count()

    altas_normal = altas_qs.filter(tipo_alta=TipoAlta.SAIDA_NORMAL).count()
    altas_obito = altas_qs.filter(tipo_alta=TipoAlta.OBITO).count()
    altas_perda_vaga = altas_qs.filter(tipo_alta=TipoAlta.PERDA_VAGA).count()
    altas_transferencia = altas_qs.filter(tipo_alta=TipoAlta.TRANSFERENCIA).count()

    # ---------------------------------------------------
    # TABELA: TIPOS DE INTERNAMENTO x ALTAS + TOTAIS
    # ---------------------------------------------------
    tabela_internamento = []
    total_global = {
        "total": 0,
        "altas_normal": 0,
        "altas_transferencia": 0,
        "altas_obito": 0,
        "altas_perda_vaga": 0,
        "total_altas": 0,
    }

    for value, label in TipoInternamento.choices:
        # Utentes desta tipologia (por data de entrada)
        qs_entrada = Utente.objects.filter(tipo_internamento=value)
        if ano:
            qs_entrada = qs_entrada.filter(data_entrada__year=ano)
        total_utentes = qs_entrada.count()
        if total_utentes == 0:
            continue

        # Altas desta tipologia (por data de saída)
        qs_altas = Utente.objects.filter(tipo_internamento=value)
        if ano:
            qs_altas = qs_altas.filter(data_saida__year=ano)

        alt_normal = qs_altas.filter(tipo_alta=TipoAlta.SAIDA_NORMAL).count()
        alt_transf = qs_altas.filter(tipo_alta=TipoAlta.TRANSFERENCIA).count()
        alt_obito = qs_altas.filter(tipo_alta=TipoAlta.OBITO).count()
        alt_perda = qs_altas.filter(tipo_alta=TipoAlta.PERDA_VAGA).count()

        total_altas = alt_normal + alt_transf + alt_obito + alt_perda

        linha = {
            "label": label,
            "total": total_utentes,
            "altas_normal": alt_normal,
            "altas_transferencia": alt_transf,
            "altas_obito": alt_obito,
            "altas_perda_vaga": alt_perda,
            "total_altas": total_altas,
        }
        tabela_internamento.append(linha)

        total_global["total"] += total_utentes
        total_global["altas_normal"] += alt_normal
        total_global["altas_transferencia"] += alt_transf
        total_global["altas_obito"] += alt_obito
        total_global["altas_perda_vaga"] += alt_perda
        total_global["total_altas"] += total_altas

    # ---------------------------------------------------
    # TABELA: GÉNERO x QUANTIDADE x IDADE MÉDIA
    #   - Usa utentes_base (logo respeita o ano, se houver)
    # ---------------------------------------------------
    idades_por_genero = {}
    for u in utentes_base.exclude(data_nascimento__isnull=True):
        if not u.genero:
            continue
        idade = u.idade
        if idade is None:
            continue
        idades_por_genero.setdefault(u.genero, []).append(idade)

    tabela_genero = []
    for value, label in Genero.choices:
        utentes_genero = utentes_base.filter(genero=value)
        total = utentes_genero.count()
        if total == 0:
            continue

        idades_lista = idades_por_genero.get(value, [])
        media_idade = round(sum(idades_lista) / len(idades_lista), 1) if idades_lista else None

        tabela_genero.append({
            "label": label,
            "total": total,
            "media_idade": media_idade,
        })

    # Idade média global
    todas_idades = []
    for u in utentes_base.exclude(data_nascimento__isnull=True):
        if u.idade is not None:
            todas_idades.append(u.idade)
    idade_media_global = round(sum(todas_idades) / len(todas_idades), 1) if todas_idades else None

    # Duração média de internamento (só quem já saiu dentro da base analisada)
    duracoes = []
    for u in utentes_base.filter(data_saida__isnull=False):
        dias = u.duracao_internamento
        if dias is not None:
            duracoes.append(dias)
    duracao_media_internamento = round(sum(duracoes) / len(duracoes), 1) if duracoes else None

    # ---------------------------------------------------
    # GRÁFICO MENSAL: ADMISSÕES x ALTAS
    #   - Se tiver ano, só meses desse ano
    #   - Se não tiver ano, considera todos os anos
    # ---------------------------------------------------
    admissoes_mes_qs = (
        utentes_base
        .annotate(m=TruncMonth("data_entrada"))
        .values("m")
        .annotate(qtd=Count("id"))
        .order_by("m")
    )

    if ano:
        altas_mes_base = Utente.objects.filter(data_saida__year=ano)
    else:
        altas_mes_base = Utente.objects.exclude(data_saida__isnull=True)

    altas_mes_qs = (
        altas_mes_base
        .annotate(m=TruncMonth("data_saida"))
        .values("m")
        .annotate(qtd=Count("id"))
        .order_by("m")
    )

    adm_dict = {row["m"]: row["qtd"] for row in admissoes_mes_qs}
    alt_dict = {row["m"]: row["qtd"] for row in altas_mes_qs}

    meses = sorted(set(adm_dict.keys()) | set(alt_dict.keys()))
    meses_labels = [d.strftime("%m/%Y") for d in meses]
    admissoes_values = [adm_dict.get(d, 0) for d in meses]
    altas_values_month = [alt_dict.get(d, 0) for d in meses]

    # ---------------------------------------------------
    # GRÁFICOS: ALTAS POR TIPO & GÉNERO
    # ---------------------------------------------------
    chart_altas_labels = ["Saída normal", "Transferência", "Óbito", "Perda de vaga"]
    chart_altas_values = [
        altas_normal,
        altas_transferencia,
        altas_obito,
        altas_perda_vaga,
    ]

    chart_genero_labels = [row["label"] for row in tabela_genero]
    chart_genero_values = [row["total"] for row in tabela_genero]

    # ---------------------------------------------------
    # CONTEXTO
    # ---------------------------------------------------
    context = {
        # Filtro
        "ano": ano,
        "anos_disponiveis": anos_disponiveis,
        "admissoes_label": admissoes_label,

        # VISITAS
        "visitas_hoje": visitas_hoje,
        "visitas_semana": visitas_semana,
        "visitas_ativas": visitas_ativas,
        "visitas_por_dia": visitas_por_dia,

        # UTENTES KPIs
        "utentes_total": utentes_total,
        "utentes_ativos": utentes_ativos,
        "utentes_inativos": utentes_inativos,
        "admissoes_30": admissoes_30,
        "altas_total": altas_total,
        "altas_normal": altas_normal,
        "altas_obito": altas_obito,
        "altas_perda_vaga": altas_perda_vaga,
        "altas_transferencia": altas_transferencia,
        "idade_media_global": idade_media_global,
        "duracao_media_internamento": duracao_media_internamento,

        # Tabelas
        "tabela_internamento": tabela_internamento,
        "tabela_internamento_total": total_global,
        "tabela_genero": tabela_genero,

        # Gráficos: altas / género
        "chart_altas_labels": json.dumps(chart_altas_labels, ensure_ascii=False),
        "chart_altas_values": json.dumps(chart_altas_values),
        "chart_genero_labels": json.dumps(chart_genero_labels, ensure_ascii=False),
        "chart_genero_values": json.dumps(chart_genero_values),

        # Gráfico mensal
        "meses_labels": json.dumps(meses_labels, ensure_ascii=False),
        "admissoes_values": json.dumps(admissoes_values),
        "altas_values_month": json.dumps(altas_values_month),
    }

    return render(request, "visitas/dashboard.html", context)


@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def escolher_utente_para_visita(request):
    q = request.GET.get("q", "").strip()
    ordenar = request.GET.get("ordenar", "nome")   # nome, numero_processo, quarto
    direcao = request.GET.get("direcao", "asc")    # asc ou desc

    utentes = Utente.objects.filter(data_saida__isnull=True)

    if q:
        utentes = utentes.filter(
            Q(nome__icontains=q)
            | Q(numero_processo__icontains=q)
            | Q(quarto__codigo__icontains=q)
        )

    ordenar_map = {
        "nome": "nome",
        "numero_processo": "numero_processo",
        "quarto": "quarto__codigo",  # ajusta se for só 'quarto'
    }

    campo = ordenar_map.get(ordenar, "nome")
    if direcao == "desc":
        campo = f"-{campo}"

    utentes = utentes.order_by(campo, "nome")

    return render(request, "visitas/escolher_utente_para_visita.html", {
        "utentes": utentes,
        "q": q,
        "ordenar": ordenar,
        "direcao": direcao,
    })



@login_required
@grupos_permitidos(
    "UCCI_Rececao",
    "UCCI_Coordenacao",
)
def visitas_relatorio_pdf(request):
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    if not data_inicio or not data_fim:
        return redirect("visitas:visitas_relatorio")

    visitas = (
        Visita.objects
        .filter(data_hora_entrada__date__range=[data_inicio, data_fim])
        .select_related("utente")
        .order_by("-data_hora_entrada")
    )

    context = {
        "visitas": visitas,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }

    template = get_template("visitas/visitas_relatorio_pdf.html")
    html = template.render(context)

    # preparar resposta HTTP como PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_visitas.pdf"'

    # gerar PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        # em caso de erro, podes devolver o HTML para debug
        return HttpResponse("Erro ao gerar PDF:\n" + html)
    return response

@login_required
@grupos_permitidos(*GRUPOS_ISOLAMENTOS)
def criar_isolamento(request, utente_id):
    utente = get_object_or_404(Utente, pk=utente_id)

    # (opcional) impedir mais do que 1 isolamento ativo
    if utente.isolamentos.filter(ativo=True).exists():
        messages.warning(request, "Este utente já tem um isolamento ativo.")
        return redirect("visitas:detalhe_utente", pk=utente.pk)

    if request.method == "POST":
        form = IsolamentoForm(request.POST)
        if form.is_valid():
            iso = form.save(commit=False)
            iso.utente = utente
            iso.criado_por = request.user
            iso.save()
            messages.success(request, "Isolamento registado com sucesso.")
            return redirect("visitas:detalhe_utente", pk=utente.pk)
    else:
        form = IsolamentoForm()

    return render(request, "visitas/isolamento_form.html", {
        "form": form,
        "utente": utente,
    })

@login_required
@grupos_permitidos(*GRUPOS_ISOLAMENTOS)
def terminar_isolamento(request, isolamento_id):
    iso = get_object_or_404(Isolamento, pk=isolamento_id)

    if not iso.ativo:
        return redirect("visitas:detalhe_utente", pk=iso.utente.pk)

    if request.method == "POST":
        iso.ativo = False
        iso.data_fim = timezone.now()
        iso.terminado_por = request.user
        iso.terminado_em = timezone.now()
        iso.save()
        messages.success(request, "Isolamento terminado.")
        return redirect("visitas:detalhe_utente", pk=iso.utente.pk)

    return render(request, "visitas/isolamento_terminar_confirmar.html", {
        "isolamento": iso,
    })

@login_required
@grupos_permitidos(*GRUPOS_ISOLAMENTOS)
def isolamentos_ativos(request):
    q = (request.GET.get("q") or "").strip()

    isolamentos = (
        Isolamento.objects
        .filter(ativo=True)
        .select_related("utente", "utente__quarto")
        .order_by("-data_inicio")
    )

    if q:
        isolamentos = isolamentos.filter(
            Q(utente__nome__icontains=q) |
            Q(utente__numero_processo__icontains=q) |
            Q(utente__quarto__codigo__icontains=q)
        )

    return render(request, "visitas/isolamentos_ativos.html", {
        "isolamentos": isolamentos,
        "q": q,
    })

@login_required
@grupos_permitidos(*GRUPOS_ISOLAMENTOS)
def editar_isolamento(request, isolamento_id):
    isolamento = get_object_or_404(Isolamento, pk=isolamento_id)

    if request.method == "POST":
        form = IsolamentoForm(request.POST, instance=isolamento)
        if form.is_valid():
            form.save()
            messages.success(request, "Isolamento atualizado com sucesso.")
            return redirect("visitas:detalhe_utente", pk=isolamento.utente.pk)
    else:
        form = IsolamentoForm(instance=isolamento)

    return render(request, "visitas/isolamento_editar.html", {
        "isolamento": isolamento,
        "utente": isolamento.utente,
        "form": form,
    })

@login_required
@grupos_permitidos(*GRUPOS_FINANCEIRO)
def lista_financeira_utentes(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "ativos").strip()
    ordenar = request.GET.get("ordenar", "nome").strip()
    direcao = request.GET.get("direcao", "asc").strip()

    utentes = Utente.objects.all()

    if estado == "ativos":
        utentes = utentes.filter(data_saida__isnull=True)
    elif estado == "inativos":
        utentes = utentes.filter(data_saida__isnull=False)

    if q:
        utentes = utentes.filter(
            Q(nome__icontains=q)
            | Q(numero_processo__icontains=q)
        )

    campos_ordenacao = {
        "nome": "nome",
        "numero_processo": "numero_processo",
        "saldo": "saldo",
        "data_entrada": "data_entrada",
        "data_saida": "data_saida",
    }
    campo = campos_ordenacao.get(ordenar, "nome")
    if direcao == "desc":
        campo = f"-{campo}"
    else:
        direcao = "asc"

    utentes = utentes.order_by(campo, "nome")
    paginator = Paginator(utentes, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_sem_pagina = request.GET.copy()
    query_sem_pagina.pop("page", None)

    query_filtros = request.GET.copy()
    query_filtros.pop("page", None)
    query_filtros.pop("ordenar", None)
    query_filtros.pop("direcao", None)

    return render(
        request,
        "visitas/financeiro_lista_utentes.html",
        {
            "page_obj": page_obj,
            "q": q,
            "estado": estado,
            "ordenar": ordenar,
            "direcao": direcao,
            "query_sem_pagina": query_sem_pagina.urlencode(),
            "query_filtros": query_filtros.urlencode(),
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_FINANCEIRO)
def financeiro_utente(request, pk):

    utente = get_object_or_404(Utente, pk=pk)

    movimentos = utente.movimentos.all()
    form = MovimentoFinanceiroForm()

    if request.method == "POST":
        form = MovimentoFinanceiroForm(request.POST)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.utente = utente
            movimento.registado_por = request.user
            movimento.save()
            messages.success(request, "Movimento financeiro registado com sucesso.")
            return redirect("visitas:financeiro_utente", pk=utente.pk)

    context = {
        "utente": utente,
        "movimentos": movimentos,
        "form": form,
    }

    return render(request, "visitas/financeiro_utente.html", context)


# ============================================================
# TRANSPORTES DE UTENTES / VIATURAS / CONDUTORES
# ============================================================

def _datetime_local(valor):
    data = parse_datetime(valor) if valor else None
    if data and timezone.is_naive(data):
        data = timezone.make_aware(data)
    return data


def _adicionar_erros_validacao(form, erro):
    if hasattr(erro, "message_dict"):
        for campo, mensagens_erro in erro.message_dict.items():
            destino = campo if campo in form.fields else None
            for mensagem in mensagens_erro:
                form.add_error(destino, mensagem)
    else:
        for mensagem in erro.messages:
            form.add_error(None, mensagem)


def _guardar_com_bloqueio(transporte):
    """Evita duas marcações simultâneas da mesma viatura/condutor."""
    with transaction.atomic():
        if transporte.viatura_id:
            Viatura.objects.select_for_update().get(pk=transporte.viatura_id)
        if transporte.condutor_id:
            Condutor.objects.select_for_update().get(pk=transporte.condutor_id)
        transporte.full_clean()
        transporte.save()

@login_required
@grupos_permitidos(*GRUPOS_CRIAR_PEDIDO_TRANSPORTE)
def criar_pedido_transporte(request):
    initial = {}

    # Permite abrir o formulário com um utente já selecionado:
    # /transportes/pedidos/novo/?utente=5
    utente_id = request.GET.get("utente", "")

    if utente_id.isdigit():
        utente = Utente.objects.filter(
            pk=utente_id,
            data_saida__isnull=True,
        ).first()

        if utente:
            initial["utente"] = utente

    if request.method == "POST":
        form = PedidoTransporteForm(request.POST)

        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.pedido_por = request.user
            pedido.save()

            messages.success(
                request,
                "Pedido de transporte enviado para validação pela Receção.",
            )

            return redirect(
                "visitas:lista_pedidos_transporte"
            )
    else:
        form = PedidoTransporteForm(initial=initial)

    return render(
        request,
        "visitas/transportes/pedido_transporte_form.html",
        {
            "form": form,
        },
    )

@login_required
@grupos_permitidos(*GRUPOS_CRIAR_PEDIDO_TRANSPORTE)
def lista_pedidos_transporte(request):
    pedidos = PedidoTransporte.objects.select_related(
        "utente",
        "pedido_por",
        "validado_por",
        "viatura",
        "condutor",
        "transporte",
    )

    # Pesquisa e filtros
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    data_inicio_texto = request.GET.get(
        "data_inicio",
        "",
    ).strip()

    data_fim_texto = request.GET.get(
        "data_fim",
        "",
    ).strip()

    data_inicio = parse_date(data_inicio_texto)
    data_fim = parse_date(data_fim_texto)

    if q:
        pedidos = pedidos.filter(
            Q(utente__nome__icontains=q)
            | Q(utente__numero_processo__icontains=q)
            | Q(destino__icontains=q)
            | Q(motivo__icontains=q)
            | Q(pedido_por__username__icontains=q)
            | Q(pedido_por__first_name__icontains=q)
            | Q(pedido_por__last_name__icontains=q)
        )

    if estado:
        pedidos = pedidos.filter(
            estado=estado
        )

    if tipo:
        pedidos = pedidos.filter(
            tipo_deslocacao=tipo
        )

    if data_inicio:
        pedidos = pedidos.filter(
            criado_em__date__gte=data_inicio
        )

    if data_fim:
        pedidos = pedidos.filter(
            criado_em__date__lte=data_fim
        )

    # Ordenação permitida
    ordenar = request.GET.get(
        "ordenar",
        "criado_em",
    )

    direcao = request.GET.get(
        "direcao",
        "desc",
    )

    ordenar_map = {
        "criado_em": "criado_em",
        "utente": "utente__nome",
        "destino": "destino",
        "consulta": "data_hora_consulta",
        "pedido_por": "pedido_por__username",
        "estado": "estado",
    }

    campo_ordenacao = ordenar_map.get(
        ordenar,
        "criado_em",
    )

    if direcao == "desc":
        campo_ordenacao = f"-{campo_ordenacao}"
    else:
        direcao = "asc"

    if ordenar == "criado_em":
        pedidos = pedidos.order_by(
            campo_ordenacao
        )
    else:
        pedidos = pedidos.order_by(
            campo_ordenacao,
            "-criado_em",
        )

    # Paginação
    paginator = Paginator(pedidos, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Querystring para manter filtros na paginação
    query_sem_pagina = request.GET.copy()
    query_sem_pagina.pop("page", None)

    # Querystring para manter filtros na ordenação
    query_filtros = request.GET.copy()
    query_filtros.pop("page", None)
    query_filtros.pop("ordenar", None)
    query_filtros.pop("direcao", None)

    return render(
        request,
        "visitas/transportes/lista_pedidos_transporte.html",
        {
            "page_obj": page_obj,
            "q": q,
            "estado": estado,
            "tipo": tipo,
            "data_inicio": data_inicio_texto,
            "data_fim": data_fim_texto,
            "estados": EstadoPedidoTransporte.choices,
            "tipos_deslocacao": TipoDeslocacao.choices,
            "ordenar": ordenar,
            "direcao": direcao,
            "query_sem_pagina": query_sem_pagina.urlencode(),
            "query_filtros": query_filtros.urlencode(),
        },
    )

@login_required
@grupos_permitidos(*GRUPOS_CRIAR_PEDIDO_TRANSPORTE)
def detalhe_pedido_transporte(request, pk):
    pedido = get_object_or_404(
        PedidoTransporte.objects.select_related(
            "utente",
            "pedido_por",
            "validado_por",
            "viatura",
            "condutor",
            "transporte",
        ),
        pk=pk,
    )

    pode_validar = (
        request.user.is_superuser
        or request.user.groups.filter(
            name__in=GRUPOS_VALIDAR_PEDIDO_TRANSPORTE
        ).exists()
    )

    return render(
        request,
        "visitas/transportes/detalhe_pedido_transporte.html",
        {
            "pedido": pedido,
            "pode_validar": pode_validar,
        },
    )

@login_required
@grupos_permitidos(*GRUPOS_VALIDAR_PEDIDO_TRANSPORTE)
def validar_pedido_transporte(request, pk):
    pedido = get_object_or_404(
        PedidoTransporte.objects.select_related(
            "utente",
            "viatura",
            "condutor",
            "transporte",
        ),
        pk=pk,
    )

    estados_validaveis = {
        EstadoPedidoTransporte.POR_VALIDAR,
        EstadoPedidoTransporte.DEVOLVIDO,
    }

    if (
        pedido.estado not in estados_validaveis
        or pedido.transporte_id
    ):
        messages.warning(
            request,
            "Este pedido já não está disponível para validação.",
        )

        return redirect(
            "visitas:detalhe_pedido_transporte",
            pk=pedido.pk,
        )

    if request.method == "POST":
        with transaction.atomic():
            # Bloqueia o pedido para impedir duas validações simultâneas
            pedido = get_object_or_404(
                PedidoTransporte.objects.select_for_update(),
                pk=pk,
            )

            if (
                pedido.estado not in estados_validaveis
                or pedido.transporte_id
            ):
                messages.warning(
                    request,
                    "O pedido já foi tratado por outro utilizador.",
                )

                return redirect(
                    "visitas:detalhe_pedido_transporte",
                    pk=pedido.pk,
                )

            form = ValidarPedidoTransporteForm(
                request.POST,
                instance=pedido,
            )

            if form.is_valid():
                pedido = form.save(commit=False)

                transporte = Transporte(
                    utente=pedido.utente,
                    tipo_deslocacao=pedido.tipo_deslocacao,
                    motivo=pedido.motivo,
                    destino=pedido.destino,
                    data_hora_saida=pedido.data_hora_saida,
                    data_hora_consulta=pedido.data_hora_consulta,
                    data_hora_regresso_previsto=(
                        pedido.data_hora_regresso_previsto
                    ),
                    meio_transporte=pedido.meio_transporte,
                    viatura=pedido.viatura,
                    condutor=pedido.condutor,
                    entidade_transporte=(
                        pedido.entidade_transporte
                    ),
                    acompanhante_nome=(
                        pedido.acompanhante_nome
                    ),
                    acompanhante_contacto=(
                        pedido.acompanhante_contacto
                    ),
                    necessita_cadeira_rodas=(
                        pedido.necessita_cadeira_rodas
                    ),
                    necessita_maca=pedido.necessita_maca,
                    necessita_oxigenio=(
                        pedido.necessita_oxigenio
                    ),
                    outras_necessidades=(
                        pedido.outras_necessidades
                    ),
                    observacoes=pedido.observacoes,
                    estado=EstadoTransporte.PENDENTE,
                    criado_por=request.user,
                    atualizado_por=request.user,
                )

                try:
                    transporte.full_clean()
                except ValidationError as erro:
                    _adicionar_erros_validacao(
                        form,
                        erro,
                    )
                else:
                    transporte.save()

                    pedido.estado = (
                        EstadoPedidoTransporte.VALIDADO
                    )
                    pedido.validado_por = request.user
                    pedido.validado_em = timezone.now()
                    pedido.transporte = transporte
                    pedido.save()

                    messages.success(
                        request,
                        (
                            "Pedido validado. O transporte ficou "
                            "a aguardar confirmação."
                        ),
                    )

                    return redirect(
                        "visitas:detalhe_transporte",
                        pk=transporte.pk,
                    )
    else:
        form = ValidarPedidoTransporteForm(
            instance=pedido,
        )

    return render(
        request,
        "visitas/transportes/validar_pedido_transporte.html",
        {
            "pedido": pedido,
            "form": form,
        },
    )

@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def calendario_transportes(request):
    return render(
        request,
        "visitas/transportes/calendario.html",
        {
            "estados": EstadoTransporte.choices,
            "tipos_deslocacao": TipoDeslocacao.choices,
            "viaturas": Viatura.objects.filter(ativo=True),
            "condutores": Condutor.objects.filter(ativo=True),
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def eventos_transportes(request):
    inicio = _datetime_local(request.GET.get("start"))
    fim = _datetime_local(request.GET.get("end"))
    transportes = Transporte.objects.select_related(
        "utente", "viatura", "condutor"
    )

    if inicio:
        transportes = transportes.filter(data_hora_regresso_previsto__gt=inicio)
    if fim:
        transportes = transportes.filter(data_hora_saida__lt=fim)

    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    viatura = request.GET.get("viatura", "").strip()
    condutor = request.GET.get("condutor", "").strip()

    if estado:
        transportes = transportes.filter(estado=estado)
    if tipo:
        transportes = transportes.filter(tipo_deslocacao=tipo)
    if viatura.isdigit():
        transportes = transportes.filter(viatura_id=viatura)
    if condutor.isdigit():
        transportes = transportes.filter(condutor_id=condutor)

    eventos = []
    for transporte in transportes:
        titulo = f"{transporte.utente.nome} — {transporte.destino}"
        eventos.append(
            {
                "id": transporte.pk,
                "title": titulo,
                "start": transporte.data_hora_saida.isoformat(),
                "end": transporte.data_hora_regresso_previsto.isoformat(),
                "url": reverse(
                    "visitas:detalhe_transporte", args=[transporte.pk]
                ),
                "backgroundColor": transporte.cor_calendario,
                "borderColor": transporte.cor_calendario,
                "extendedProps": {
                    "estado": transporte.get_estado_display(),
                    "tipo": transporte.get_tipo_deslocacao_display(),
                    "viatura": str(transporte.viatura) if transporte.viatura else "",
                    "condutor": str(transporte.condutor) if transporte.condutor else "",
                },
            }
        )
    return JsonResponse(eventos, safe=False)


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def lista_transportes(request):
    transportes = Transporte.objects.select_related(
        "utente", "viatura", "condutor"
    ).order_by("data_hora_saida")
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    meio = request.GET.get("meio", "").strip()
    data_inicio = parse_date(request.GET.get("data_inicio", ""))
    data_fim = parse_date(request.GET.get("data_fim", ""))

    if q:
        transportes = transportes.filter(
            Q(utente__nome__icontains=q)
            | Q(utente__numero_processo__icontains=q)
            | Q(destino__icontains=q)
            | Q(motivo__icontains=q)
        )
    if estado:
        transportes = transportes.filter(estado=estado)
    if meio == "EXTERNO":
        transportes = transportes.exclude(
            meio_transporte=MeioTransporte.INSTITUICAO
        )
    elif meio:
        transportes = transportes.filter(meio_transporte=meio)
    if data_inicio:
        transportes = transportes.filter(data_hora_saida__date__gte=data_inicio)
    if data_fim:
        transportes = transportes.filter(data_hora_saida__date__lte=data_fim)

    return render(
        request,
        "visitas/transportes/lista_transportes.html",
        {
            "transportes": transportes,
            "estados": EstadoTransporte.choices,
            "meios_transporte": [
                ("EXTERNO", "Todos os transportes externos"),
                *MeioTransporte.choices,
            ],
            "q": q,
            "estado": estado,
            "meio": meio,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )


@login_required
@grupos_permitidos(*GRUPOS_PLANEAMENTO_TRANSPORTES)
def criar_transporte(request):
    initial = {}
    inicio = _datetime_local(request.GET.get("inicio"))
    if inicio:
        initial["data_hora_saida"] = inicio
        initial["data_hora_regresso_previsto"] = inicio + timedelta(hours=3)
    utente_id = request.GET.get("utente", "")
    if utente_id.isdigit():
        utente = Utente.objects.filter(pk=utente_id, data_saida__isnull=True).first()
        if utente:
            initial["utente"] = utente

    if request.method == "POST":
        form = TransporteForm(request.POST)
        if form.is_valid():
            transporte = form.save(commit=False)
            transporte.criado_por = request.user
            transporte.atualizado_por = request.user
            try:
                _guardar_com_bloqueio(transporte)
            except ValidationError as erro:
                _adicionar_erros_validacao(form, erro)
            else:
                messages.success(request, "Transporte marcado com sucesso.")
                return redirect("visitas:detalhe_transporte", pk=transporte.pk)
    else:
        form = TransporteForm(initial=initial)

    return render(
        request,
        "visitas/transportes/form_transporte.html",
        {"form": form, "transporte": None},
    )


@login_required
@grupos_permitidos(*GRUPOS_PLANEAMENTO_TRANSPORTES)
def editar_transporte(request, pk):
    transporte = get_object_or_404(Transporte, pk=pk)
    if transporte.estado in {EstadoTransporte.CONCLUIDO, EstadoTransporte.CANCELADO} and not request.user.is_superuser:
        messages.warning(request, "Um transporte concluído ou cancelado só pode ser alterado por um administrador.")
        return redirect("visitas:detalhe_transporte", pk=pk)

    if request.method == "POST":
        form = TransporteForm(request.POST, instance=transporte)
        if form.is_valid():
            transporte = form.save(commit=False)
            transporte.atualizado_por = request.user
            try:
                _guardar_com_bloqueio(transporte)
            except ValidationError as erro:
                _adicionar_erros_validacao(form, erro)
            else:
                messages.success(request, "Marcação atualizada com sucesso.")
                return redirect("visitas:detalhe_transporte", pk=pk)
    else:
        form = TransporteForm(instance=transporte)

    return render(
        request,
        "visitas/transportes/form_transporte.html",
        {"form": form, "transporte": transporte},
    )

def pode_confirmar_transporte(utilizador, transporte):
    if utilizador.is_superuser:
        return True

    if utilizador.groups.filter(
        name="UCCI_Coordenacao"
    ).exists():
        return True

    if transporte.meio_transporte == MeioTransporte.INSTITUICAO:
        return utilizador.groups.filter(
            name="UCCI_Transportes"
        ).exists()

    return utilizador.groups.filter(
        name="UCCI_Rececao"
    ).exists()

@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def detalhe_transporte(request, pk):
    transporte = get_object_or_404(
        Transporte.objects.select_related(
            "utente",
            "viatura",
            "condutor",
            "criado_por",
            "atualizado_por",
            "confirmado_por",
        ),
        pk=pk,
    )

    return render(
        request,
        "visitas/transportes/detalhe_transporte.html",
        {
            "transporte": transporte,
            "pode_confirmar": pode_confirmar_transporte(
                request.user,
                transporte,
            ),
            "pode_editar": (
                request.user.is_superuser
                or request.user.groups.filter(
                    name__in=GRUPOS_PLANEAMENTO_TRANSPORTES
                ).exists()
            ),
        },
    )

@require_POST
@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def acao_transporte(request, pk, acao):
    with transaction.atomic():
        transporte = get_object_or_404(
            Transporte.objects.select_for_update(),
            pk=pk,
        )

        # Confirmação conforme o meio de transporte:
        # interno -> Transportes
        # externo -> Receção
        if (
            acao == "confirmar"
            and not pode_confirmar_transporte(
                request.user,
                transporte,
            )
        ):
            raise PermissionDenied(
                "Não tem autorização para confirmar este transporte."
            )

        agora = timezone.now()

        if (
            acao == "confirmar"
            and transporte.estado == EstadoTransporte.PENDENTE
        ):
            transporte.estado = EstadoTransporte.CONFIRMADO
            transporte.confirmado_por = request.user
            transporte.confirmado_em = agora
            mensagem = "Transporte confirmado."

        elif (
            acao == "iniciar"
            and transporte.estado in {
                EstadoTransporte.PENDENTE,
                EstadoTransporte.CONFIRMADO,
            }
        ):
            transporte.estado = EstadoTransporte.EM_CURSO
            transporte.data_hora_saida_real = agora
            mensagem = "Saída efetiva registada."

        elif (
            acao == "concluir"
            and transporte.estado == EstadoTransporte.EM_CURSO
        ):
            transporte.estado = EstadoTransporte.CONCLUIDO
            transporte.data_hora_regresso_real = agora
            mensagem = "Regresso à UCCI registado."

        elif (
            acao == "cancelar"
            and transporte.estado not in {
                EstadoTransporte.CONCLUIDO,
                EstadoTransporte.CANCELADO,
            }
        ):
            transporte.estado = EstadoTransporte.CANCELADO
            mensagem = "Transporte cancelado."

        else:
            messages.error(
                request,
                "Esta alteração de estado não é permitida.",
            )

            return redirect(
                "visitas:detalhe_transporte",
                pk=pk,
            )

        transporte.atualizado_por = request.user

        try:
            transporte.full_clean()

        except ValidationError as erro:
            if hasattr(erro, "message_dict"):
                detalhes = [
                    detalhe
                    for lista in erro.message_dict.values()
                    for detalhe in lista
                ]
            else:
                detalhes = erro.messages

            messages.error(
                request,
                (
                    "Não foi possível alterar o estado: "
                    + " ".join(detalhes)
                ),
            )

            return redirect(
                "visitas:detalhe_transporte",
                pk=pk,
            )

        transporte.save()

    messages.success(
        request,
        mensagem,
    )

    return redirect(
        "visitas:detalhe_transporte",
        pk=pk,
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def relatorio_diario_transportes(request):
    dia = parse_date(request.GET.get("data", "")) or timezone.localdate()
    transportes = Transporte.objects.filter(
        data_hora_saida__date=dia
    ).select_related("utente", "utente__quarto", "viatura", "condutor")
    return render(
        request,
        "visitas/transportes/relatorio_diario.html",
        {"dia": dia, "transportes": transportes},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def lista_viaturas(request):
    return render(
        request,
        "visitas/transportes/lista_viaturas.html",
        {"viaturas": Viatura.objects.all()},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def gerir_viatura(request, pk=None):
    viatura = get_object_or_404(Viatura, pk=pk) if pk else None
    if request.method == "POST":
        form = ViaturaForm(request.POST, instance=viatura)
        if form.is_valid():
            form.save()
            messages.success(request, "Viatura guardada com sucesso.")
            return redirect("visitas:lista_viaturas")
    else:
        form = ViaturaForm(instance=viatura)
    return render(
        request,
        "visitas/transportes/form_recurso.html",
        {"form": form, "titulo": "Viatura", "voltar": "visitas:lista_viaturas"},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def lista_condutores(request):
    return render(
        request,
        "visitas/transportes/lista_condutores.html",
        {"condutores": Condutor.objects.all()},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def gerir_condutor(request, pk=None):
    condutor = get_object_or_404(Condutor, pk=pk) if pk else None
    if request.method == "POST":
        form = CondutorForm(request.POST, instance=condutor)
        if form.is_valid():
            form.save()
            messages.success(request, "Condutor guardado com sucesso.")
            return redirect("visitas:lista_condutores")
    else:
        form = CondutorForm(instance=condutor)
    return render(
        request,
        "visitas/transportes/form_recurso.html",
        {"form": form, "titulo": "Condutor", "voltar": "visitas:lista_condutores"},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def lista_indisponibilidades(request):
    indisponibilidades = Indisponibilidade.objects.select_related(
        "viatura", "condutor"
    )
    return render(
        request,
        "visitas/transportes/lista_indisponibilidades.html",
        {"indisponibilidades": indisponibilidades},
    )


@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def gerir_indisponibilidade(request, pk=None):
    indisponibilidade = get_object_or_404(Indisponibilidade, pk=pk) if pk else None
    if request.method == "POST":
        form = IndisponibilidadeForm(request.POST, instance=indisponibilidade)
        if form.is_valid():
            objeto = form.save(commit=False)
            if not objeto.pk:
                objeto.criado_por = request.user
            objeto.save()
            messages.success(request, "Indisponibilidade guardada com sucesso.")
            return redirect("visitas:lista_indisponibilidades")
    else:
        form = IndisponibilidadeForm(instance=indisponibilidade)
    return render(
        request,
        "visitas/transportes/form_recurso.html",
        {
            "form": form,
            "titulo": "Indisponibilidade",
            "voltar": "visitas:lista_indisponibilidades",
        },
    )


@require_POST
@login_required
@grupos_permitidos(*GRUPOS_TRANSPORTES)
def apagar_indisponibilidade(request, pk):
    indisponibilidade = get_object_or_404(Indisponibilidade, pk=pk)
    indisponibilidade.delete()
    messages.success(request, "Indisponibilidade eliminada.")
    return redirect("visitas:lista_indisponibilidades")
