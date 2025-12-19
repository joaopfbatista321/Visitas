from datetime import timedelta, date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import localdate
from django.db.models import Q
from django.core.paginator import Paginator

from .forms import UtenteForm, VisitaForm, ExternoForm, UtenteSaidaForm, IsolamentoForm, MovimentoFinanceiroForm

import json
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Visita, Utente, TipoAlta, TipoInternamento, Genero, Externo, Isolamento, MovimentoFinanceiro
from django.contrib import messages



# ============================================================
# UTENTES
# ============================================================

@login_required
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
def detalhe_utente(request, pk):
    utente = get_object_or_404(Utente, pk=pk)

    visitas = (
        Visita.objects
        .filter(utente=utente)
        .order_by("-data_hora_entrada")
    )

    is_financeiro = request.user.groups.filter(name="Financeiro").exists()

    context = {
        "utente": utente,
        "visitas": visitas,
        "is_financeiro": is_financeiro,
    }

    return render(request, "visitas/detalhe_utente.html", context)


@login_required
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
def lista_externos(request):
    externos = Externo.objects.all().order_by("-data_hora_entrada")
    return render(request, "visitas/lista_externos.html", {
        "externos": externos,
    })


@login_required
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

def is_financeiro(user):
    return user.groups.filter(name="Financeiro").exists()

@login_required
@user_passes_test(is_financeiro)
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
            return redirect("visitas:financeiro_utente", pk=utente.pk)

    context = {
        "utente": utente,
        "movimentos": movimentos,
        "form": form,
    }

    return render(request, "visitas/financeiro_utente.html", context)