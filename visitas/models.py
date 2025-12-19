from django.db import models
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

    # Contacto de emergência 1
    contacto_emergencia1_nome = models.CharField(max_length=100, blank=True)
    contacto_emergencia1_telefone = models.CharField(max_length=30, blank=True)
    contacto_emergencia1_parentesco = models.CharField(max_length=50, blank=True)

    # Contacto de emergência 2
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


@receiver(post_save, sender=MovimentoFinanceiro)
def atualizar_saldo(sender, instance, created, **kwargs):
    if not created:
        return

    utente = instance.utente

    if instance.tipo == MovimentoFinanceiro.ENTRADA:
        utente.saldo += instance.valor
    else:
        utente.saldo -= instance.valor

    utente.save(update_fields=["saldo"])
