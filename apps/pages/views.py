from django.shortcuts import render
from apps.pages.models import Product
from django.core import serializers
from django.contrib.auth.decorators import login_required
from .models import *
import json
from datetime import timedelta
from django.utils import timezone
from visitas.models import Utente, Visita

# apps/pages/views.py

import json
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from visitas.models import Utente, Visita


@login_required
def index(request):
    hoje = timezone.localdate()

    total_utentes_ativos = Utente.objects.filter(data_saida__isnull=True).count()

    visitas_hoje = Visita.objects.filter(
        data_hora_entrada__date=hoje
    ).count()

    visitas_em_curso_qs = Visita.objects.filter(
        data_hora_saida__isnull=True
    ).select_related("utente")
    visitas_em_curso = visitas_em_curso_qs.count()

    fim_janela = hoje + timedelta(days=5)
    proximas_altas = Utente.objects.filter(
        data_prevista_saida__isnull=False,
        data_prevista_saida__range=(hoje, fim_janela),
        data_saida__isnull=True,
    ).order_by("data_prevista_saida", "nome")[:10]

    dias = []
    entradas = []
    saidas = []

    for i in range(29, -1, -1):
        dia = hoje - timedelta(days=i)
        dias.append(dia.strftime("%d/%m"))
        entradas.append(Utente.objects.filter(data_entrada=dia).count())
        saidas.append(Utente.objects.filter(data_saida=dia).count())

    context = {
        "total_utentes_ativos": total_utentes_ativos,
        "visitas_hoje": visitas_hoje,
        "visitas_em_curso": visitas_em_curso,
        "lista_visitas_em_curso": visitas_em_curso_qs,
        "proximas_altas": proximas_altas,
        "grafico_dias": json.dumps(dias),
        "grafico_entradas": json.dumps(entradas),
        "grafico_saidas": json.dumps(saidas),
    }


    return render(request, "pages/index.html", context)


# Components
def color(request):
  context = {
    'segment': 'color'
  }
  return render(request, "pages/color.html", context)

def typography(request):
  context = {
    'segment': 'typography'
  }
  return render(request, "pages/typography.html", context)

def icon_feather(request):
  context = {
    'segment': 'feather_icon'
  }
  return render(request, "pages/icon-feather.html", context)

def sample_page(request):
  context = {
    'segment': 'sample_page',
  }
  return render(request, 'pages/sample-page.html', context)

