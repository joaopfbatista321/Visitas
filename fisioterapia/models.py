from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from config.permissoes_clinicas import (
    VisibilidadeRegisto,
    pode_editar_registo,
    pode_ver_registo,
)


GRUPO_FISIOTERAPIA = "UCCI_Fisioterapia"
GRUPO_TERAPIA_OCUPACIONAL = "UCCI_TerapiaOcupacional"
GRUPO_TERAPIA_FALA = "UCCI_TerapiaFala"

GRUPOS_REABILITACAO = (
    GRUPO_FISIOTERAPIA,
    GRUPO_TERAPIA_OCUPACIONAL,
    GRUPO_TERAPIA_FALA,
)


class AreaReabilitacao(models.TextChoices):
    FISIOTERAPIA = "FISIOTERAPIA", "Fisioterapia"
    TERAPIA_OCUPACIONAL = (
        "TERAPIA_OCUPACIONAL",
        "Terapia Ocupacional",
    )
    TERAPIA_FALA = (
        "TERAPIA_FALA",
        "Terapia da Fala",
    )


GRUPO_POR_AREA_REABILITACAO = {
    AreaReabilitacao.FISIOTERAPIA: GRUPO_FISIOTERAPIA,
    AreaReabilitacao.TERAPIA_OCUPACIONAL: (
        GRUPO_TERAPIA_OCUPACIONAL
    ),
    AreaReabilitacao.TERAPIA_FALA: GRUPO_TERAPIA_FALA,
}


COR_POR_AREA_REABILITACAO = {
    AreaReabilitacao.FISIOTERAPIA: "#0d6efd",
    AreaReabilitacao.TERAPIA_OCUPACIONAL: "#006a4e",
    AreaReabilitacao.TERAPIA_FALA: "#dc3545",
}


class TipoSessaoFisioterapia(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    GRUPO = "GRUPO", "Grupo"


class EstadoSessaoFisioterapia(models.TextChoices):
    AGENDADA = "AGENDADA", "Agendada"
    REALIZADA = "REALIZADA", "Realizada"
    CANCELADA = "CANCELADA", "Cancelada"


class EstadoParticipacaoFisioterapia(models.TextChoices):
    AGENDADO = "AGENDADO", "Agendado"
    REALIZADO = "REALIZADO", "Realizou"
    FALTOU = "FALTOU", "Faltou"
    CANCELADO = "CANCELADO", "Cancelado"
    CANCELADO_ALTA = "CANCELADO_ALTA", "Cancelado por alta"
    CANCELADO_AUSENCIA = (
        "CANCELADO_AUSENCIA",
        "Cancelado por ausência",
    )


class CategoriaIntervencaoFisioterapia(models.TextChoices):
    AVALIACAO = "AVALIACAO", "Avaliação"
    FISIOTERAPIA = "FISIOTERAPIA", "Fisioterapia"
    REABILITACAO = "REABILITACAO", "Reabilitação"
    TREINO_FUNCIONAL = "TREINO_FUNCIONAL", "Treino funcional"
    OUTRO = "OUTRO", "Outro"


class LocalSessaoFisioterapia(models.TextChoices):
    SALA_REABILITACAO = (
        "SALA_REABILITACAO",
        "Sala de reabilitação",
    )
    LEITO = "LEITO", "Leito/quarto do utente"
    OUTRO = "OUTRO", "Outro local"


class TipoIntervencaoFisioterapia(models.Model):
    area = models.CharField(
        "Área de Reabilitação",
        max_length=30,
        choices=AreaReabilitacao.choices,
        default=AreaReabilitacao.FISIOTERAPIA,
        db_index=True,
    )

    categoria = models.CharField(
        "Categoria",
        max_length=20,
        choices=CategoriaIntervencaoFisioterapia.choices,
        default=CategoriaIntervencaoFisioterapia.FISIOTERAPIA,
        db_index=True,
    )

    nome = models.CharField(
        "Designação",
        max_length=150,
    )

    descricao = models.TextField(
        "Descrição",
        blank=True,
    )

    ativo = models.BooleanField(
        "Disponível para utilização",
        default=True,
        db_index=True,
    )

    ordem = models.PositiveSmallIntegerField(
        "Ordem de apresentação",
        default=0,
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "area",
            "ordem",
            "categoria",
            "nome",
        ]
        verbose_name = "Tipo de intervenção de reabilitação"
        verbose_name_plural = (
            "Tipos de intervenção de reabilitação"
        )
        constraints = [
            models.UniqueConstraint(
                fields=["area", "nome"],
                name="reab_interv_area_nome_uniq",
            ),
        ]

    def __str__(self):
        return self.nome


class SessaoFisioterapia(models.Model):
    area = models.CharField(
        "Área de Reabilitação",
        max_length=30,
        choices=AreaReabilitacao.choices,
        default=AreaReabilitacao.FISIOTERAPIA,
        db_index=True,
    )

    tipo = models.CharField(
        "Formato da sessão",
        max_length=15,
        choices=TipoSessaoFisioterapia.choices,
        default=TipoSessaoFisioterapia.INDIVIDUAL,
        db_index=True,
    )

    tipos_intervencao = models.ManyToManyField(
        TipoIntervencaoFisioterapia,
        related_name="sessoes",
        verbose_name="Tipos de intervenção",
        blank=True,
    )

    inicio = models.DateTimeField(
        "Início",
        db_index=True,
    )

    fim = models.DateTimeField(
        "Fim",
    )

    local_realizacao = models.CharField(
        "Local de realização",
        max_length=25,
        choices=LocalSessaoFisioterapia.choices,
        default=LocalSessaoFisioterapia.SALA_REABILITACAO,
        db_index=True,
    )

    local = models.CharField(
        "Especificação do local",
        max_length=150,
        blank=True,
        help_text=(
            "Preencher quando escolher outro local "
            "ou quando for necessário indicar mais detalhes."
        ),
    )

    trabalho_planeado = models.TextField(
        "Trabalho e objetivos planeados",
        blank=True,
    )

    observacoes = models.TextField(
        "Observações de organização",
        blank=True,
    )

    estado = models.CharField(
        "Estado",
        max_length=15,
        choices=EstadoSessaoFisioterapia.choices,
        default=EstadoSessaoFisioterapia.AGENDADA,
        db_index=True,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sessoes_fisioterapia",
        verbose_name="Profissional responsável",
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_fisioterapia_criadas",
        verbose_name="Criado por",
    )

    estado_atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_fisioterapia_validadas",
        verbose_name="Estado atualizado por",
    )

    estado_atualizado_em = models.DateTimeField(
        "Estado atualizado em",
        null=True,
        blank=True,
    )

    utentes = models.ManyToManyField(
        "visitas.Utente",
        through="ParticipacaoFisioterapia",
        related_name="sessoes_fisioterapia",
        verbose_name="Utentes",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["inicio"]
        verbose_name = "Sessão de Reabilitação"
        verbose_name_plural = "Sessões de Reabilitação"
        indexes = [
            models.Index(
                fields=["inicio", "estado"],
                name="fisio_sessao_inicio_estado",
            ),
            models.Index(
                fields=["profissional", "inicio"],
                name="fisio_profissional_inicio",
            ),
            models.Index(
                fields=["local_realizacao", "inicio"],
                name="fisio_local_inicio",
            ),
            models.Index(
                fields=["area", "inicio"],
                name="reab_area_inicio",
            ),
        ]

    def __str__(self):
        return (
            f"{self.titulo} — "
            f"{self.inicio:%d/%m/%Y %H:%M}"
        )

    @property
    def titulo(self):
        """
        Designação automática utilizada no calendário,
        nas listas e no detalhe da sessão.
        """
        if not self.pk:
            return "Nova sessão de Reabilitação"

        participacoes = list(
            self.participacoes
            .select_related("utente")
            .order_by("utente__nome")
        )

        if self.tipo == TipoSessaoFisioterapia.INDIVIDUAL:
            if participacoes:
                identificacao = participacoes[0].utente.nome
            else:
                identificacao = "Sessão individual"
        else:
            quantidade = len(participacoes)

            if quantidade == 1:
                identificacao = "Grupo (1 utente)"
            else:
                identificacao = (
                    f"Grupo ({quantidade} utentes)"
                )

        nomes_intervencoes = list(
            self.tipos_intervencao
            .order_by("ordem", "nome")
            .values_list("nome", flat=True)
        )

        if not nomes_intervencoes:
            intervencoes = self.get_area_display()
        elif len(nomes_intervencoes) <= 2:
            intervencoes = " + ".join(nomes_intervencoes)
        else:
            intervencoes = (
                " + ".join(nomes_intervencoes[:2])
                + f" +{len(nomes_intervencoes) - 2}"
            )

        return f"{identificacao} — {intervencoes}"

    @property
    def titulo_calendario(self):
        nome_profissional = (
            self.profissional.get_full_name().strip()
            or self.profissional.username
        )

        return f"{self.titulo} · {nome_profissional}"

    @property
    def cor_calendario(self):
        return COR_POR_AREA_REABILITACAO.get(
            self.area,
            "#6c757d",
        )

    @property
    def grupo_profissional(self):
        return GRUPO_POR_AREA_REABILITACAO.get(
            self.area,
            GRUPO_FISIOTERAPIA,
        )

    @property
    def local_exibicao(self):
        local_base = self.get_local_realizacao_display()

        if (
            self.local_realizacao
            == LocalSessaoFisioterapia.OUTRO
        ):
            return self.local or local_base

        if self.local:
            return f"{local_base} — {self.local}"

        return local_base

    @property
    def duracao_minutos(self):
        if not self.inicio or not self.fim:
            return 0

        duracao = self.fim - self.inicio
        return int(duracao.total_seconds() // 60)

    def clean(self):
        super().clean()

        erros = {}

        if (
            self.inicio
            and self.fim
            and self.fim <= self.inicio
        ):
            erros["fim"] = (
                "A hora de fim tem de ser posterior "
                "à hora de início."
            )

        if (
            self.local_realizacao
            == LocalSessaoFisioterapia.OUTRO
            and not self.local.strip()
        ):
            erros["local"] = (
                "Indique onde será realizada a sessão."
            )

        if self.profissional_id:
            grupos = self.profissional.groups.filter(
                name=self.grupo_profissional
            )

            if (
                not self.profissional.is_superuser
                and not grupos.exists()
            ):
                erros["profissional"] = (
                    "O profissional responsável tem de pertencer "
                    f"ao grupo {self.grupo_profissional}."
                )

            if not self.profissional.is_active:
                erros["profissional"] = (
                    "O profissional selecionado não está ativo."
                )

        if erros:
            raise ValidationError(erros)

    def pode_editar(self, utilizador):
        """
        Só o profissional responsável pode editar
        ou validar a sessão.
        """
        return (
            utilizador.is_authenticated
            and utilizador.pk == self.profissional_id
        )

    def pode_registar_presencas(self, utilizador):
        return self.pode_editar(utilizador)


class ParticipacaoFisioterapia(models.Model):
    sessao = models.ForeignKey(
        SessaoFisioterapia,
        on_delete=models.CASCADE,
        related_name="participacoes",
        verbose_name="Sessão",
    )

    utente = models.ForeignKey(
        "visitas.Utente",
        on_delete=models.PROTECT,
        related_name="participacoes_fisioterapia",
        verbose_name="Utente",
    )

    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=EstadoParticipacaoFisioterapia.choices,
        default=EstadoParticipacaoFisioterapia.AGENDADO,
        db_index=True,
    )

    motivo_estado = models.CharField(
        "Motivo da falta ou alteração",
        max_length=250,
        blank=True,
    )

    cancelada_por_ausencia = models.ForeignKey(
        "enfermagem.AusenciaUtente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            "participacoes_reabilitacao_canceladas"
        ),
        verbose_name="Ausência que originou o cancelamento",
    )

    estado_atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presencas_fisioterapia_validadas",
        verbose_name="Estado atualizado por",
    )

    estado_atualizado_em = models.DateTimeField(
        "Estado atualizado em",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "sessao__inicio",
            "utente__nome",
        ]
        verbose_name = "Participação em fisioterapia"
        verbose_name_plural = "Participações em fisioterapia"
        constraints = [
            models.UniqueConstraint(
                fields=["sessao", "utente"],
                name="fisio_participacao_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["utente", "estado"],
                name="fisio_utente_estado",
            ),
        ]

    def __str__(self):
        return (
            f"{self.utente.nome} — "
            f"{self.sessao.titulo}"
        )

    def clean(self):
        super().clean()

        erros = {}

        if (
            self.estado
            == EstadoParticipacaoFisioterapia.FALTOU
            and not (self.motivo_estado or "").strip()
        ):
            erros["motivo_estado"] = (
                "Indique por que motivo o utente faltou."
            )

        if (
            self.estado
            == EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA
            and not self.cancelada_por_ausencia_id
        ):
            erros["cancelada_por_ausencia"] = (
                "Indique a ausência que originou o cancelamento."
            )

        if erros:
            raise ValidationError(erros)

    def alterar_estado(
        self,
        novo_estado,
        utilizador=None,
        motivo="",
        ausencia=None,
    ):
        estados_validos = {
            valor
            for valor, _ in EstadoParticipacaoFisioterapia.choices
        }

        if novo_estado not in estados_validos:
            raise ValidationError(
                "O estado indicado não é válido."
            )

        motivo = (motivo or "").strip()

        if (
            novo_estado
            == EstadoParticipacaoFisioterapia.FALTOU
            and not motivo
        ):
            raise ValidationError({
                "motivo_estado": (
                    "Indique por que motivo o utente faltou."
                )
            })

        if (
            novo_estado
            == EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA
            and ausencia is None
        ):
            raise ValidationError({
                "cancelada_por_ausencia": (
                    "Indique a ausência que originou "
                    "o cancelamento."
                )
            })

        estado_anterior = self.estado

        if estado_anterior == novo_estado:
            return

        agora = timezone.now()

        self.estado = novo_estado
        self.motivo_estado = motivo
        self.cancelada_por_ausencia = (
            ausencia
            if novo_estado
            == EstadoParticipacaoFisioterapia.CANCELADO_AUSENCIA
            else None
        )
        self.estado_atualizado_por = utilizador
        self.estado_atualizado_em = agora

        self.save(
            update_fields=[
                "estado",
                "motivo_estado",
                "cancelada_por_ausencia",
                "estado_atualizado_por",
                "estado_atualizado_em",
            ]
        )

        HistoricoParticipacaoFisioterapia.objects.create(
            participacao=self,
            estado_anterior=estado_anterior,
            estado_novo=novo_estado,
            alterado_por=utilizador,
            motivo=motivo,
            ausencia=ausencia,
        )


class HistoricoParticipacaoFisioterapia(models.Model):
    participacao = models.ForeignKey(
        ParticipacaoFisioterapia,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Participação",
    )

    estado_anterior = models.CharField(
        "Estado anterior",
        max_length=20,
        choices=EstadoParticipacaoFisioterapia.choices,
        blank=True,
    )

    estado_novo = models.CharField(
        "Novo estado",
        max_length=20,
        choices=EstadoParticipacaoFisioterapia.choices,
    )

    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alteracoes_fisioterapia",
        verbose_name="Alterado por",
    )

    alterado_em = models.DateTimeField(
        auto_now_add=True,
    )

    motivo = models.CharField(
        "Motivo",
        max_length=250,
        blank=True,
    )

    ausencia = models.ForeignKey(
        "enfermagem.AusenciaUtente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            "historico_participacoes_reabilitacao"
        ),
        verbose_name="Ausência relacionada",
    )

    class Meta:
        ordering = ["-alterado_em"]
        verbose_name = "Histórico da participação"
        verbose_name_plural = "Histórico das participações"

    def __str__(self):
        return (
            f"{self.participacao} — "
            f"{self.get_estado_novo_display()}"
        )


class RegistoFisioterapia(models.Model):
    utente = models.ForeignKey(
        "visitas.Utente",
        on_delete=models.PROTECT,
        related_name="registos_fisioterapia",
        verbose_name="Utente",
    )

    area = models.CharField(
        "Área de Reabilitação",
        max_length=30,
        choices=AreaReabilitacao.choices,
        default=AreaReabilitacao.FISIOTERAPIA,
        db_index=True,
    )

    participacao = models.ForeignKey(
        ParticipacaoFisioterapia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_clinicos",
        verbose_name="Participação",
    )

    tipos_intervencao = models.ManyToManyField(
        TipoIntervencaoFisioterapia,
        related_name="registos",
        verbose_name="Tipos de intervenção realizados",
        blank=True,
    )

    data_registo = models.DateTimeField(
        "Data do atendimento",
        default=timezone.now,
        db_index=True,
    )

    tipo_trabalho = models.CharField(
        "Descrição complementar da intervenção",
        max_length=180,
        blank=True,
    )

    trabalho_realizado = models.TextField(
        "Trabalho realizado",
    )

    resposta_utente = models.TextField(
        "Resposta/evolução do utente",
        blank=True,
    )

    plano_seguinte = models.TextField(
        "Plano para a próxima sessão",
        blank=True,
    )

    visibilidade = models.CharField(
        "Visibilidade",
        max_length=15,
        choices=VisibilidadeRegisto.choices,
        default=VisibilidadeRegisto.TODOS,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registos_fisioterapia",
        verbose_name="Profissional de Reabilitação",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-data_registo"]
        verbose_name = "Registo de Reabilitação"
        verbose_name_plural = "Registos de Reabilitação"
        indexes = [
            models.Index(
                fields=["utente", "data_registo"],
                name="fisio_registo_utente_data",
            ),
            models.Index(
                fields=["area", "data_registo"],
                name="reab_reg_area_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.utente.nome} — "
            f"{self.data_registo:%d/%m/%Y %H:%M}"
        )

    @property
    def intervencoes_exibicao(self):
        nomes = list(
            self.tipos_intervencao
            .order_by("ordem", "nome")
            .values_list("nome", flat=True)
        )

        if nomes:
            return ", ".join(nomes)

        return (
            self.tipo_trabalho
            or self.get_area_display()
        )

    @property
    def grupo_profissional(self):
        return GRUPO_POR_AREA_REABILITACAO.get(
            self.area,
            GRUPO_FISIOTERAPIA,
        )

    def clean(self):
        super().clean()

        erros = {}

        if (
            self.participacao_id
            and self.utente_id
            and self.participacao.utente_id
            != self.utente_id
        ):
            erros["participacao"] = (
                "A participação selecionada pertence "
                "a outro utente."
            )

        if (
            self.participacao_id
            and self.area
            != self.participacao.sessao.area
        ):
            erros["area"] = (
                "A área do registo tem de ser igual "
                "à área da sessão."
            )

        if erros:
            raise ValidationError(erros)

    def pode_ver(self, utilizador):
        return pode_ver_registo(
            utilizador=utilizador,
            autor_id=self.profissional_id,
            visibilidade=self.visibilidade,
            grupo_profissional=self.grupo_profissional,
        )

    def pode_editar(self, utilizador):
        return pode_editar_registo(
            utilizador=utilizador,
            autor_id=self.profissional_id,
        )
