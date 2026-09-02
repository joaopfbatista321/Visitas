from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from django.conf import settings
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


User = get_user_model()

# ============================================================
#  QUARTOS / PISOS
# ============================================================

class Piso(models.TextChoices):
    RC = "RC", "Rés-do-chão"
    P1 = "1", "1.º Piso"
    P2 = "2", "2.º Piso"
    P3 = "3", "3.º Piso"


class Quarto(models.Model):
    codigo = models.CharField("Código do quarto", max_length=10)
    piso = models.CharField("Piso", max_length=2, choices=Piso.choices)
    descricao = models.CharField("Descrição", max_length=100, blank=True, null=True)
    capacidade = models.PositiveSmallIntegerField(
        "Número de camas",
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Número de camas disponíveis neste quarto.",
    )

    class Meta:
        verbose_name = "Quarto"
        verbose_name_plural = "Quartos"
        ordering = ["piso", "codigo"]
        unique_together = ("codigo", "piso")

    def __str__(self):
        return f"{self.codigo} ({self.get_piso_display()})"


# ============================================================
#  ENUMS
# ============================================================

class Genero(models.TextChoices):
    MASCULINO = "M", "Masculino"
    FEMININO = "F", "Feminino"
    OUTRO = "O", "Outro / Não especificado"


class TipoInternamento(models.TextChoices):
    UC = "UC", "Convalescença (U.C.)"
    UMDR = "UMDR", "UMDR"
    ULDM = "ULDM", "ULDM"
    ULDM_DC = "ULDM-DC", "ULDM-DC"


class TipoAlta(models.TextChoices):
    SAIDA_NORMAL = "NORMAL", "Saída normal"
    OBITO = "OBITO", "Óbito"
    PERDA_VAGA = "PERDA_VAGA", "Perda de vaga"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência"


# ============================================================
#  UTENTE
# ============================================================

class Utente(models.Model):
    nome = models.CharField("Nome completo", max_length=200)
    data_nascimento = models.DateField("Data de nascimento", blank=True, null=True)
    numero_processo = models.CharField("N.º processo", max_length=50, unique=True)

    numero_utente_sns = models.CharField(
        "N.º Utente SNS", max_length=20, blank=True, null=True
    )

    genero = models.CharField(
        "Género", max_length=1, choices=Genero.choices, blank=True, null=True
    )

    tipo_internamento = models.CharField(
        "Tipo de internamento",
        max_length=15,
        choices=TipoInternamento.choices,
        blank=True,
        null=True,
    )

    quarto = models.ForeignKey(
        Quarto,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="utentes",
        verbose_name="Quarto",
    )

    data_entrada = models.DateField("Data de entrada")
    data_prevista_saida = models.DateField("Data prevista de saída", blank=True, null=True)
    data_saida = models.DateField("Data de saída", blank=True, null=True)

    tipo_alta = models.CharField(
        "Tipo de alta",
        max_length=20,
        choices=TipoAlta.choices,
        blank=True,
        null=True,
    )

    transferido_para = models.CharField(
        "Transferido para",
        max_length=200,
        blank=True,
        null=True,
        help_text="Indicar local/unidade para onde foi transferido.",
    )

    observacoes = models.TextField("Observações", blank=True, null=True)

    visitas_restritas = models.BooleanField("Visitas restritas", default=False)
    alerta_visitas = models.TextField("Alerta para visitas", blank=True, null=True)

    registado_entrada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="utentes_registados_entrada",
    )

    registado_saida_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="utentes_registados_saida",
    )

    saldo = models.DecimalField(
        "Saldo disponível",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    valor_caucao = models.DecimalField(
        "Valor da caução",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=(
            "Valor administrativo da caução. Não altera o saldo pessoal "
            "nem o cálculo das mensalidades."
        ),
    )

    valor_dia = models.DecimalField(
        "Valor diário",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Valor cobrado por cada dia faturável de internamento.",
    )

    paga_dias_ausencia = models.BooleanField(
        "Paga durante as ausências",
        default=True,
        help_text=(
            "Desative para descontar da mensalidade os dias em que o "
            "utente está ausente."
        ),
    )

    contacto_emergencia1_nome = models.CharField(max_length=100, blank=True)
    contacto_emergencia1_telefone = models.CharField(max_length=30, blank=True)
    contacto_emergencia1_parentesco = models.CharField(max_length=50, blank=True)

    contacto_emergencia2_nome = models.CharField(max_length=100, blank=True)
    contacto_emergencia2_telefone = models.CharField(max_length=30, blank=True)
    contacto_emergencia2_parentesco = models.CharField(max_length=50, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Utente"
        verbose_name_plural = "Utentes"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.numero_processo})"

    @property
    def ativo(self):
        return self.data_saida is None

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def duracao_internamento(self):
        if not self.data_entrada:
            return None
        fim = self.data_saida or date.today()
        return (fim - self.data_entrada).days

    @property
    def atraso_previsto(self):
        if not self.data_prevista_saida:
            return None
        fim = self.data_saida or date.today()
        return (fim - self.data_prevista_saida).days

    @property
    def isolamento_ativo(self):
        return self.isolamentos.filter(ativo=True).order_by("-data_inicio").first()
    


    # ----------------------- PROPRIEDADES -----------------------

    @property
    def ativo(self):
        return self.data_saida is None

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def duracao_internamento(self):
        if not self.data_entrada:
            return None
        fim = self.data_saida or date.today()
        return (fim - self.data_entrada).days

    @property
    def atraso_previsto(self):
        if not self.data_prevista_saida:
            return None
        fim = self.data_saida or date.today()
        return (fim - self.data_prevista_saida).days


# ============================================================
#  VISITA
# ============================================================

class TipoVisitante(models.TextChoices):
    FAMILIAR = "FAM", "Familiar / Amigo"
    VOLUNTARIO = "VOL", "Voluntário"
    OUTRO = "OUT", "Outro"


class Visita(models.Model):
    utente = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="visitas",
    )

    tipo_visitante = models.CharField(
        "Tipo de visitante",
        max_length=4,
        choices=TipoVisitante.choices,
        default=TipoVisitante.FAMILIAR,
    )

    nome_visitante = models.CharField("Nome do visitante", max_length=200)
    documento_identificacao = models.CharField(
        "Documento identificação", max_length=100, blank=True, null=True
    )
    telefone = models.CharField("Telefone", max_length=20, blank=True, null=True)
    parentesco = models.CharField("Parentesco", max_length=100, blank=True, null=True)

    data_hora_entrada = models.DateTimeField("Entrada", default=timezone.now)
    data_hora_saida = models.DateTimeField("Saída", blank=True, null=True)

    motivo = models.CharField("Motivo", max_length=200, blank=True, null=True)
    observacoes = models.TextField("Observações", blank=True, null=True)

    registado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="visitas_registadas",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_hora_entrada"]

    def __str__(self):
        return f"Visita de {self.nome_visitante} a {self.utente.nome}"

    @property
    def em_curso(self):
        return self.data_hora_saida is None

    @property
    def duracao(self):
        if self.data_hora_saida:
            return self.data_hora_saida - self.data_hora_entrada
        return None

    @property
    def duracao_horas_minutos(self):
        if not self.data_hora_saida:
            return None
        delta = self.data_hora_saida - self.data_hora_entrada
        total = int(delta.total_seconds())
        horas = total // 3600
        minutos = (total % 3600) // 60
        return f"{horas}h {minutos}m"


# ============================================================
#  EXTERNO
# ============================================================

class TipoExterno(models.TextChoices):
    SERVICO = "SERV", "Prestador de serviços"
    TECNICO = "TEC", "Técnico / Manutenção"
    FORNECEDOR = "FORN", "Fornecedor"
    OUTRO = "OUT", "Outro"


class Externo(models.Model):
    tipo_externo = models.CharField(
        max_length=5, choices=TipoExterno.choices, default=TipoExterno.SERVICO
    )
    nome = models.CharField(max_length=200)
    empresa = models.CharField(max_length=150, blank=True, null=True)
    documento_identificacao = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    destino = models.CharField(max_length=150, blank=True, null=True)

    data_hora_entrada = models.DateTimeField(default=timezone.now)
    data_hora_saida = models.DateTimeField(blank=True, null=True)

    motivo = models.CharField(max_length=200, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)

    registado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="externos_registados"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_hora_entrada"]

    def __str__(self):
        return f"{self.nome} ({self.empresa or 'sem empresa'})"

    @property
    def em_curso(self):
        return self.data_hora_saida is None

    @property
    def duracao(self):
        if self.data_hora_saida:
            return self.data_hora_saida - self.data_hora_entrada
        return None

class TipoIsolamento(models.TextChoices):
    CONTACTO = "CONTACTO", "Isolamento de contacto"
    GOTICULAS = "GOTICULAS", "Isolamento por gotículas"
    VIA_AEREA = "VIA_AEREA", "Isolamento por via aérea"


class Isolamento(models.Model):
    utente = models.ForeignKey(
        "Utente",
        on_delete=models.CASCADE,
        related_name="isolamentos"
    )

    tipo = models.CharField(max_length=20, choices=TipoIsolamento.choices)
    ativo = models.BooleanField(default=True)

    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField(null=True, blank=True)

    motivo = models.CharField(max_length=255, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="isolamentos_criados"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    terminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="isolamentos_terminados"
    )
    terminado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ativo", "-data_inicio"]

    def __str__(self):
        return f"{self.utente} - {self.get_tipo_display()} ({'Ativo' if self.ativo else 'Terminado'})"
    
@property
def isolamento_ativo(self):
    return self.isolamentos.filter(ativo=True).order_by("-data_inicio").first()


class MovimentoFinanceiro(models.Model):
    """Movimento da conta pessoal do utente, sem relação com mensalidades."""

    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"

    TIPO_CHOICES = [
        (ENTRADA, "Entrada"),
        (SAIDA, "Saída"),
    ]

    utente = models.ForeignKey(
        Utente,
        on_delete=models.CASCADE,
        related_name="movimentos"
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255)

    data = models.DateTimeField(auto_now_add=True)
    registado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        ordering = ("-data",)


class Mensalidade(models.Model):
    """Cobrança administrativa independente do saldo pessoal do utente."""

    utente = models.ForeignKey(
        Utente,
        on_delete=models.PROTECT,
        related_name="mensalidades",
        verbose_name="Utente",
    )
    ano = models.PositiveSmallIntegerField("Ano")
    mes = models.PositiveSmallIntegerField(
        "Mês",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    valor_dia = models.DecimalField(
        "Valor diário aplicado",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    dias_estadia = models.PositiveSmallIntegerField(
        "Dias de estadia no mês",
        default=0,
    )
    dias_ausencia = models.PositiveSmallIntegerField(
        "Dias de ausência descontados",
        default=0,
    )
    dias_faturaveis = models.PositiveSmallIntegerField(
        "Dias faturáveis",
        default=0,
    )
    valor_total = models.DecimalField(
        "Valor total",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    pago = models.BooleanField(
        "Pago",
        default=False,
        db_index=True,
    )
    pago_em = models.DateTimeField(
        "Pago em",
        blank=True,
        null=True,
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="mensalidades_confirmadas",
        editable=False,
        verbose_name="Confirmado por",
    )
    necessita_revisao = models.BooleanField(
        "Necessita de revisão",
        default=False,
        db_index=True,
        help_text=(
            "Indica que uma mensalidade já paga foi recalculada devido a "
            "uma alteração de datas, ausências ou valor diário."
        ),
    )
    observacoes = models.TextField("Observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mensalidade do utente"
        verbose_name_plural = "Mensalidades dos utentes"
        ordering = ["-ano", "-mes", "utente__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["utente", "ano", "mes"],
                name="mensalidade_unica_por_utente_mes",
            ),
        ]
        indexes = [
            models.Index(
                fields=["ano", "mes", "pago"],
                name="vis_mens_ano_mes_pago",
            ),
        ]

    def __str__(self):
        return f"{self.utente} — {self.mes:02d}/{self.ano}"

    @property
    def valor_pago(self):
        if hasattr(self, "valor_recebido"):
            total = self.valor_recebido or Decimal("0.00")
        elif self.pk:
            total = self.pagamentos.aggregate(
                total=models.Sum("valor")
            )["total"] or Decimal("0.00")
        else:
            total = Decimal("0.00")

        # Compatibilidade com pagamentos confirmados antes da criação
        # do histórico de pagamentos parciais.
        if total == 0 and self.pago:
            return self.valor_total
        return total

    @property
    def valor_em_falta(self):
        return max(
            self.valor_total - self.valor_pago,
            Decimal("0.00"),
        )

    @property
    def valor_excedente(self):
        return max(
            self.valor_pago - self.valor_total,
            Decimal("0.00"),
        )

    @property
    def estado_pagamento(self):
        if self.necessita_revisao:
            return "REVISAO"
        if self.valor_total > 0 and self.valor_em_falta == 0:
            return "PAGO"
        if self.valor_pago > 0:
            return "PARCIAL"
        return "PENDENTE"

    def clean(self):
        super().clean()
        erros = {}

        if self.dias_ausencia > self.dias_estadia:
            erros["dias_ausencia"] = (
                "Os dias de ausência não podem exceder os dias de estadia."
            )

        if self.dias_faturaveis != self.dias_estadia - self.dias_ausencia:
            erros["dias_faturaveis"] = (
                "Os dias faturáveis devem corresponder à estadia menos as ausências."
            )

        if erros:
            raise ValidationError(erros)


class PagamentoMensalidade(models.Model):
    mensalidade = models.ForeignKey(
        Mensalidade,
        on_delete=models.PROTECT,
        related_name="pagamentos",
        verbose_name="Mensalidade",
    )
    valor = models.DecimalField(
        "Valor recebido",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    data_pagamento = models.DateField(
        "Data do pagamento",
        default=timezone.localdate,
    )
    observacoes = models.CharField(
        "Observações",
        max_length=250,
        blank=True,
    )
    registado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pagamentos_mensalidades_registados",
        verbose_name="Registado por",
    )
    criado_em = models.DateTimeField("Registado em", auto_now_add=True)

    class Meta:
        verbose_name = "Pagamento de mensalidade"
        verbose_name_plural = "Pagamentos de mensalidades"
        ordering = ["-data_pagamento", "-criado_em"]
        indexes = [
            models.Index(
                fields=["mensalidade", "data_pagamento"],
                name="vis_pag_mens_data",
            ),
        ]

    def __str__(self):
        return f"{self.mensalidade} — {self.valor:.2f} €"
@receiver(post_save, sender=MovimentoFinanceiro)
def atualizar_saldo(sender, instance, created, **kwargs):
    # Só os movimentos da conta pessoal podem alterar o saldo do utente.
    # Pagamentos de mensalidades são registados noutro modelo e não passam
    # por este sinal.
    if not created:
        return

    utente = instance.utente

    if instance.tipo == MovimentoFinanceiro.ENTRADA:
        utente.saldo += instance.valor
    else:
        utente.saldo -= instance.valor

    utente.save(update_fields=["saldo"])


# ============================================================
# TRANSPORTES DE UTENTES / VIATURAS / CONDUTORES
# ============================================================

class TipoViatura(models.TextChoices):
    LIGEIRA = "LIGEIRA", "Ligeira"
    ADAPTADA = "ADAPTADA", "Adaptada"
    AMBULANCIA = "AMBULANCIA", "Ambulância"
    OUTRA = "OUTRA", "Outra"


class Viatura(models.Model):
    matricula = models.CharField("Matrícula", max_length=15, unique=True)
    designacao = models.CharField("Designação", max_length=120)
    tipo = models.CharField(
        "Tipo de viatura",
        max_length=15,
        choices=TipoViatura.choices,
        default=TipoViatura.LIGEIRA,
    )
    marca = models.CharField("Marca", max_length=80, blank=True)
    modelo = models.CharField("Modelo", max_length=80, blank=True)
    numero_lugares = models.PositiveSmallIntegerField("N.º de lugares", default=5)
    adaptada_cadeira_rodas = models.BooleanField(
        "Preparada para cadeira de rodas", default=False
    )
    permite_maca = models.BooleanField("Permite transporte em maca", default=False)
    validade_seguro = models.DateField("Validade do seguro", blank=True, null=True)
    validade_inspecao = models.DateField("Validade da inspeção", blank=True, null=True)
    ativo = models.BooleanField("Disponível para marcação", default=True)
    observacoes = models.TextField("Observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["matricula"]
        verbose_name = "Viatura"
        verbose_name_plural = "Viaturas"

    def __str__(self):
        return f"{self.matricula} — {self.designacao}"

    @property
    def documentos_validos(self):
        hoje = timezone.localdate()
        return not (
            (self.validade_seguro and self.validade_seguro < hoje)
            or (self.validade_inspecao and self.validade_inspecao < hoje)
        )


class Condutor(models.Model):
    nome = models.CharField("Nome", max_length=180)
    numero_mecanografico = models.CharField(
        "N.º mecanográfico", max_length=30, blank=True, null=True, unique=True
    )
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    categoria_carta = models.CharField("Categoria da carta", max_length=30, blank=True)
    numero_carta = models.CharField("N.º da carta", max_length=50, blank=True)
    validade_carta = models.DateField("Validade da carta", blank=True, null=True)
    ativo = models.BooleanField("Disponível para marcação", default=True)
    observacoes = models.TextField("Observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Condutor"
        verbose_name_plural = "Condutores"

    def __str__(self):
        if self.numero_mecanografico:
            return f"{self.nome} ({self.numero_mecanografico})"
        return self.nome

    @property
    def carta_valida(self):
        return not self.validade_carta or self.validade_carta >= timezone.localdate()


class TipoDeslocacao(models.TextChoices):
    CONSULTA = "CONSULTA", "Consulta"
    EXAME = "EXAME", "Exame"
    TRATAMENTO = "TRATAMENTO", "Tratamento"
    URGENCIA = "URGENCIA", "Urgência"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência temporária"
    OUTRO = "OUTRO", "Outro"


class MeioTransporte(models.TextChoices):
    INSTITUICAO = "INSTITUICAO", "Viatura da instituição"
    AMBULANCIA = "AMBULANCIA", "Ambulância externa"
    TAXI = "TAXI", "Táxi / TVDE"
    FAMILIA = "FAMILIA", "Família"
    OUTRO = "OUTRO", "Outro"


class EstadoTransporte(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    EM_CURSO = "EM_CURSO", "Em curso"
    CONCLUIDO = "CONCLUIDO", "Concluído"
    CANCELADO = "CANCELADO", "Cancelado"

class EstadoPedidoTransporte(models.TextChoices):
    POR_VALIDAR = "POR_VALIDAR", "A validar pela Receção"
    DEVOLVIDO = "DEVOLVIDO", "Devolvido para correção"
    VALIDADO = "VALIDADO", "Validado"
    REJEITADO = "REJEITADO", "Rejeitado"
    CANCELADO = "CANCELADO", "Cancelado"


class PedidoTransporte(models.Model):
    utente = models.ForeignKey(
        "Utente",
        on_delete=models.PROTECT,
        related_name="pedidos_transporte",
        verbose_name="Utente",
    )

    tipo_deslocacao = models.CharField(
        "Tipo de deslocação",
        max_length=20,
        choices=TipoDeslocacao.choices,
        default=TipoDeslocacao.CONSULTA,
    )

    motivo = models.CharField(
        "Motivo",
        max_length=250,
        blank=True,
    )

    destino = models.CharField(
        "Destino",
        max_length=250,
        blank=True,
    )

    # Datas conhecidas pelo profissional
    data_hora_consulta = models.DateTimeField(
        "Hora da consulta/exame",
        blank=True,
        null=True,
    )

    data_hora_saida = models.DateTimeField(
        "Saída prevista da UCCI",
        blank=True,
        null=True,
    )

    data_hora_regresso_previsto = models.DateTimeField(
        "Regresso previsto à UCCI",
        blank=True,
        null=True,
    )

    # Informação logística opcional no pedido
    meio_transporte = models.CharField(
        "Meio de transporte",
        max_length=20,
        choices=MeioTransporte.choices,
        blank=True,
        default="",
    )

    viatura = models.ForeignKey(
        Viatura,
        on_delete=models.PROTECT,
        related_name="pedidos_transporte",
        verbose_name="Viatura",
        blank=True,
        null=True,
    )

    condutor = models.ForeignKey(
        Condutor,
        on_delete=models.PROTECT,
        related_name="pedidos_transporte",
        verbose_name="Condutor",
        blank=True,
        null=True,
    )

    entidade_transporte = models.CharField(
        "Entidade/pessoa responsável pelo transporte",
        max_length=180,
        blank=True,
        help_text="Ex.: Bombeiros, táxi ou familiar.",
    )

    # Acompanhamento e necessidades clínicas
    acompanhante_nome = models.CharField(
        "Acompanhante",
        max_length=180,
        blank=True,
    )

    acompanhante_contacto = models.CharField(
        "Contacto do acompanhante",
        max_length=30,
        blank=True,
    )

    necessita_cadeira_rodas = models.BooleanField(
        "Cadeira de rodas",
        default=False,
    )

    necessita_maca = models.BooleanField(
        "Maca",
        default=False,
    )

    necessita_oxigenio = models.BooleanField(
        "Oxigénio",
        default=False,
    )

    outras_necessidades = models.CharField(
        "Outras necessidades",
        max_length=250,
        blank=True,
    )

    observacoes = models.TextField(
        "Observações do pedido",
        blank=True,
    )

    # Validação pela Receção
    estado = models.CharField(
        "Estado do pedido",
        max_length=15,
        choices=EstadoPedidoTransporte.choices,
        default=EstadoPedidoTransporte.POR_VALIDAR,
    )

    observacoes_recepcao = models.TextField(
        "Observações da Receção",
        blank=True,
    )

    pedido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_transporte_criados",
        editable=False,
        verbose_name="Pedido por",
    )

    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_transporte_validados",
        editable=False,
        verbose_name="Validado por",
    )

    validado_em = models.DateTimeField(
        "Validado em",
        blank=True,
        null=True,
        editable=False,
    )

    # Transporte criado depois da validação
    transporte = models.OneToOneField(
        "Transporte",
        on_delete=models.SET_NULL,
        related_name="pedido_origem",
        blank=True,
        null=True,
        editable=False,
        verbose_name="Transporte criado",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Pedido de transporte"
        verbose_name_plural = "Pedidos de transporte"
        indexes = [
            models.Index(fields=["estado", "criado_em"]),
        ]

    def __str__(self):
        return f"Pedido #{self.pk} — {self.utente}"


class Transporte(models.Model):
    utente = models.ForeignKey(
        "Utente",
        on_delete=models.PROTECT,
        related_name="transportes",
        verbose_name="Utente",
    )
    tipo_deslocacao = models.CharField(
        "Tipo de deslocação",
        max_length=20,
        choices=TipoDeslocacao.choices,
        default=TipoDeslocacao.CONSULTA,
    )
    motivo = models.CharField("Motivo", max_length=250)
    destino = models.CharField("Destino", max_length=250)

    data_hora_saida = models.DateTimeField("Saída prevista da UCCI")
    data_hora_consulta = models.DateTimeField(
        "Hora da consulta/exame", blank=True, null=True
    )
    data_hora_regresso_previsto = models.DateTimeField("Regresso previsto à UCCI")
    data_hora_saida_real = models.DateTimeField(
        "Saída efetiva", blank=True, null=True, editable=False
    )
    data_hora_regresso_real = models.DateTimeField(
        "Regresso efetivo", blank=True, null=True, editable=False
    )

    meio_transporte = models.CharField(
        "Meio de transporte",
        max_length=20,
        choices=MeioTransporte.choices,
        default=MeioTransporte.INSTITUICAO,
    )
    viatura = models.ForeignKey(
        Viatura,
        on_delete=models.PROTECT,
        related_name="transportes",
        verbose_name="Viatura",
        blank=True,
        null=True,
    )
    condutor = models.ForeignKey(
        Condutor,
        on_delete=models.PROTECT,
        related_name="transportes",
        verbose_name="Condutor",
        blank=True,
        null=True,
    )
    entidade_transporte = models.CharField(
        "Entidade/pessoa responsável pelo transporte",
        max_length=180,
        blank=True,
        help_text="Ex.: Bombeiros, táxi ou familiar.",
    )

    acompanhante_nome = models.CharField("Acompanhante", max_length=180, blank=True)
    acompanhante_contacto = models.CharField(
        "Contacto do acompanhante", max_length=30, blank=True
    )
    necessita_cadeira_rodas = models.BooleanField("Cadeira de rodas", default=False)
    necessita_maca = models.BooleanField("Maca", default=False)
    necessita_oxigenio = models.BooleanField("Oxigénio", default=False)
    outras_necessidades = models.CharField(
        "Outras necessidades", max_length=250, blank=True
    )

    estado = models.CharField(
        "Estado",
        max_length=15,
        choices=EstadoTransporte.choices,
        default=EstadoTransporte.PENDENTE,
    )
    observacoes = models.TextField("Observações", blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transportes_criados",
        editable=False,
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transportes_atualizados",
        editable=False,
    )

    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transportes_confirmados",
        editable=False,
        verbose_name="Confirmado por",
    )

    confirmado_em = models.DateTimeField(
        "Confirmado em",
        blank=True,
        null=True,
        editable=False,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["data_hora_saida"]
        verbose_name = "Transporte de utente"
        verbose_name_plural = "Transportes de utentes"
        indexes = [
            models.Index(fields=["data_hora_saida", "data_hora_regresso_previsto"]),
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        return f"{self.utente} — {self.data_hora_saida:%d/%m/%Y %H:%M}"

    @property
    def cor_calendario(self):
        return {
            EstadoTransporte.PENDENTE: "#f59e0b",
            EstadoTransporte.CONFIRMADO: "#2563eb",
            EstadoTransporte.EM_CURSO: "#7c3aed",
            EstadoTransporte.CONCLUIDO: "#16a34a",
            EstadoTransporte.CANCELADO: "#6b7280",
        }.get(self.estado, "#2563eb")

    def _transportes_sobrepostos(self):
        if not self.data_hora_saida or not self.data_hora_regresso_previsto:
            return Transporte.objects.none()
        return Transporte.objects.exclude(pk=self.pk).exclude(
            estado=EstadoTransporte.CANCELADO
        ).filter(
            data_hora_saida__lt=self.data_hora_regresso_previsto,
            data_hora_regresso_previsto__gt=self.data_hora_saida,
        )

    def clean(self):
        super().clean()
        erros = {}

        if (
            self.data_hora_saida
            and self.data_hora_regresso_previsto
            and self.data_hora_regresso_previsto <= self.data_hora_saida
        ):
            erros["data_hora_regresso_previsto"] = (
                "O regresso previsto tem de ser posterior à saída."
            )

        if self.data_hora_consulta and self.data_hora_saida:
            if self.data_hora_consulta < self.data_hora_saida:
                erros["data_hora_consulta"] = (
                    "A consulta/exame não pode ser anterior à saída prevista."
                )
            elif (
                self.data_hora_regresso_previsto
                and self.data_hora_consulta > self.data_hora_regresso_previsto
            ):
                erros["data_hora_consulta"] = (
                    "A consulta/exame não pode ser posterior ao regresso previsto."
                )

        if self.data_hora_saida_real and self.data_hora_regresso_real:
            if self.data_hora_regresso_real <= self.data_hora_saida_real:
                erros["data_hora_regresso_real"] = (
                    "O regresso efetivo tem de ser posterior à saída efetiva."
                )

        if self.estado != EstadoTransporte.CANCELADO:
            if self.meio_transporte == MeioTransporte.INSTITUICAO:
                if not self.viatura_id:
                    erros["viatura"] = "Selecione uma viatura da instituição."
                if not self.condutor_id:
                    erros["condutor"] = "Selecione um condutor."
            elif not (self.entidade_transporte or "").strip():
                erros["entidade_transporte"] = (
                    "Indique a entidade ou pessoa responsável pelo transporte."
                )

        if self.estado != EstadoTransporte.CANCELADO and self.data_hora_saida:
            dia_saida = (
                timezone.localtime(self.data_hora_saida).date()
                if timezone.is_aware(self.data_hora_saida)
                else self.data_hora_saida.date()
            )

            if self.viatura_id:
                if not self.viatura.ativo:
                    erros["viatura"] = "A viatura selecionada está indisponível."
                elif self.viatura.validade_seguro and self.viatura.validade_seguro < dia_saida:
                    erros["viatura"] = "O seguro da viatura estará expirado nesta data."
                elif self.viatura.validade_inspecao and self.viatura.validade_inspecao < dia_saida:
                    erros["viatura"] = "A inspeção da viatura estará expirada nesta data."
                elif self.necessita_cadeira_rodas and not self.viatura.adaptada_cadeira_rodas:
                    erros["viatura"] = "Selecione uma viatura preparada para cadeira de rodas."
                elif self.necessita_maca and not self.viatura.permite_maca:
                    erros["viatura"] = "Selecione uma viatura que permita transporte em maca."

            if self.condutor_id:
                if not self.condutor.ativo:
                    erros["condutor"] = "O condutor selecionado está indisponível."
                elif self.condutor.validade_carta and self.condutor.validade_carta < dia_saida:
                    erros["condutor"] = "A carta do condutor estará expirada nesta data."

            if self.data_hora_regresso_previsto:
                sobrepostos = self._transportes_sobrepostos()
                if self.viatura_id and sobrepostos.filter(viatura_id=self.viatura_id).exists():
                    erros["viatura"] = "Esta viatura já está atribuída a outro transporte nesse horário."
                if self.condutor_id and sobrepostos.filter(condutor_id=self.condutor_id).exists():
                    erros["condutor"] = "Este condutor já está atribuído a outro transporte nesse horário."

                indisponibilidades = Indisponibilidade.objects.filter(
                    inicio__lt=self.data_hora_regresso_previsto,
                    fim__gt=self.data_hora_saida,
                )
                if self.viatura_id and indisponibilidades.filter(viatura_id=self.viatura_id).exists():
                    erros["viatura"] = "A viatura tem uma indisponibilidade registada nesse horário."
                if self.condutor_id and indisponibilidades.filter(condutor_id=self.condutor_id).exists():
                    erros["condutor"] = "O condutor tem uma indisponibilidade registada nesse horário."

        if erros:
            raise ValidationError(erros)


class Indisponibilidade(models.Model):
    viatura = models.ForeignKey(
        Viatura,
        on_delete=models.CASCADE,
        related_name="indisponibilidades",
        blank=True,
        null=True,
    )
    condutor = models.ForeignKey(
        Condutor,
        on_delete=models.CASCADE,
        related_name="indisponibilidades",
        blank=True,
        null=True,
    )
    inicio = models.DateTimeField("Início")
    fim = models.DateTimeField("Fim")
    motivo = models.CharField("Motivo", max_length=250)
    observacoes = models.TextField("Observações", blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="indisponibilidades_transporte_criadas",
        editable=False,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Indisponibilidade"
        verbose_name_plural = "Indisponibilidades"

    def __str__(self):
        recurso = self.viatura or self.condutor
        return f"{recurso} — {self.inicio:%d/%m/%Y %H:%M}"

    def clean(self):
        super().clean()
        erros = {}
        if bool(self.viatura_id) == bool(self.condutor_id):
            raise ValidationError("Selecione exatamente uma viatura ou um condutor.")
        if self.inicio and self.fim and self.fim <= self.inicio:
            erros["fim"] = "O fim tem de ser posterior ao início."

        if self.inicio and self.fim:
            transportes = Transporte.objects.exclude(
                estado=EstadoTransporte.CANCELADO
            ).filter(
                data_hora_saida__lt=self.fim,
                data_hora_regresso_previsto__gt=self.inicio,
            )
            if self.viatura_id and transportes.filter(viatura_id=self.viatura_id).exists():
                erros["viatura"] = "A viatura já tem transportes marcados neste período."
            if self.condutor_id and transportes.filter(condutor_id=self.condutor_id).exists():
                erros["condutor"] = "O condutor já tem transportes marcados neste período."
        if erros:
            raise ValidationError(erros)
