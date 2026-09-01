from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone

from clinica.models import VisibilidadeRegistoClinico
from visitas.models import Utente


AREA_CLINICA_ENFERMAGEM = "enfermagem"


class TurnoEnfermagem(models.TextChoices):
    MANHA = "MANHA", "Manhã"
    TARDE = "TARDE", "Tarde"
    NOITE = "NOITE", "Noite"
    OUTRO = "OUTRO", "Outro"


class TipoAusenciaUtente(models.TextChoices):
    AGUDIZACAO = "AGUDIZACAO", "Agudização"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência"
    OUTRA = "OUTRA", "Outra ausência"


class EstadoAusenciaUtente(models.TextChoices):
    ATIVA = "ATIVA", "Ausente"
    TERMINADA = "TERMINADA", "Regressou"
    CANCELADA = "CANCELADA", "Registo cancelado"


class AcaoHistoricoAusencia(models.TextChoices):
    CRIADA = "CRIADA", "Ausência registada"
    ALTERADA = "ALTERADA", "Período alterado"
    TERMINADA = "TERMINADA", "Regresso registado"
    CANCELADA = "CANCELADA", "Registo cancelado"


class TipoRegistoEnfermagem(models.Model):
    codigo = models.SlugField(
        "Código",
        max_length=50,
        unique=True,
    )

    nome = models.CharField(
        "Nome",
        max_length=100,
        unique=True,
    )

    descricao = models.TextField(
        "Descrição",
        blank=True,
    )

    ativo = models.BooleanField(
        "Ativo",
        default=True,
    )

    ordem = models.PositiveSmallIntegerField(
        "Ordem",
        default=0,
    )

    class Meta:
        verbose_name = "Tipo de registo de Enfermagem"
        verbose_name_plural = (
            "Tipos de registo de Enfermagem"
        )
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class RegistoEnfermagem(models.Model):
    AREA_CLINICA_CODIGO = AREA_CLINICA_ENFERMAGEM

    utente = models.ForeignKey(
        Utente,
        on_delete=models.PROTECT,
        related_name="registos_enfermagem",
        verbose_name="Utente",
    )

    data_registo = models.DateTimeField(
        "Data e hora do registo",
    )

    turno = models.CharField(
        "Turno",
        max_length=20,
        choices=TurnoEnfermagem.choices,
        blank=True,
    )

    tipo_registo = models.ForeignKey(
        TipoRegistoEnfermagem,
        on_delete=models.PROTECT,
        related_name="registos",
        verbose_name="Tipo de registo",
    )

    observacao = models.TextField(
        "Observação e evolução",
    )

    cuidados_realizados = models.TextField(
        "Cuidados e intervenções realizadas",
        blank=True,
    )

    resposta_utente = models.TextField(
        "Resposta do utente",
        blank=True,
    )

    plano_cuidados = models.TextField(
        "Plano e recomendações seguintes",
        blank=True,
    )

    visibilidade = models.CharField(
        "Visibilidade",
        max_length=20,
        choices=VisibilidadeRegistoClinico.choices,
        default=VisibilidadeRegistoClinico.TODOS,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registos_enfermagem_criados",
        verbose_name="Profissional",
    )

    criado_em = models.DateTimeField(
        "Criado em",
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        "Atualizado em",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Registo de Enfermagem"
        verbose_name_plural = "Registos de Enfermagem"
        ordering = [
            "-data_registo",
            "-criado_em",
        ]
        indexes = [
            models.Index(
                fields=["utente", "data_registo"],
                name="enf_reg_utente_data",
            ),
            models.Index(
                fields=["profissional", "data_registo"],
                name="enf_reg_prof_data",
            ),
            models.Index(
                fields=["visibilidade"],
                name="enf_reg_visibilidade",
            ),
        ]

    def __str__(self):
        return (
            f"{self.tipo_registo.nome} — "
            f"{self.utente.nome} — "
            f"{self.data_registo:%d/%m/%Y %H:%M}"
        )

    def clean(self):
        super().clean()

        if (
            self.data_registo
            and self.data_registo > timezone.now()
        ):
            raise ValidationError(
                {
                    "data_registo": (
                        "A data e hora do registo não pode "
                        "estar no futuro."
                    )
                }
            )

    @property
    def tem_registo_queda(self):
        return hasattr(self, "queda")

    def dados_para_historico(self):
        return {
            "utente_id": self.utente_id,
            "data_registo": (
                self.data_registo.isoformat()
                if self.data_registo
                else None
            ),
            "turno": self.turno,
            "tipo_registo_id": self.tipo_registo_id,
            "observacao": self.observacao,
            "cuidados_realizados": (
                self.cuidados_realizados
            ),
            "resposta_utente": self.resposta_utente,
            "plano_cuidados": self.plano_cuidados,
            "visibilidade": self.visibilidade,
            "profissional_id": self.profissional_id,
        }


class AusenciaUtente(models.Model):
    utente = models.ForeignKey(
        Utente,
        on_delete=models.PROTECT,
        related_name="ausencias_enfermagem",
        verbose_name="Utente",
    )

    tipo = models.CharField(
        "Tipo de ausência",
        max_length=20,
        choices=TipoAusenciaUtente.choices,
        default=TipoAusenciaUtente.AGUDIZACAO,
        db_index=True,
    )

    data_hora_inicio = models.DateTimeField(
        "Data e hora da saída",
        default=timezone.now,
        db_index=True,
    )

    data_hora_fim_prevista = models.DateTimeField(
        "Regresso previsto",
        null=True,
        blank=True,
        db_index=True,
    )

    data_hora_regresso = models.DateTimeField(
        "Data e hora do regresso",
        null=True,
        blank=True,
        db_index=True,
    )

    destino = models.CharField(
        "Destino",
        max_length=200,
        blank=True,
        help_text=(
            "Ex.: Serviço de Urgência, hospital ou outra unidade."
        ),
    )

    motivo = models.TextField(
        "Motivo da ausência",
    )

    observacoes = models.TextField(
        "Observações",
        blank=True,
    )

    estado = models.CharField(
        "Estado",
        max_length=15,
        choices=EstadoAusenciaUtente.choices,
        default=EstadoAusenciaUtente.ATIVA,
        db_index=True,
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ausencias_utentes_criadas",
        verbose_name="Registado por",
    )

    estado_atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ausencias_utentes_atualizadas",
        verbose_name="Estado atualizado por",
    )

    estado_atualizado_em = models.DateTimeField(
        "Estado atualizado em",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(
        "Criado em",
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        "Atualizado em",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Agudização/transferência"
        verbose_name_plural = "Agudizações/transferências"
        ordering = [
            "-data_hora_inicio",
            "-criado_em",
        ]
        indexes = [
            models.Index(
                fields=["utente", "estado"],
                name="enf_aus_utente_estado",
            ),
            models.Index(
                fields=["estado", "data_hora_inicio"],
                name="enf_aus_estado_inicio",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["utente"],
                condition=Q(
                    estado=EstadoAusenciaUtente.ATIVA
                ),
                name="enf_ausencia_ativa_unica",
            ),
        ]

    def __str__(self):
        return (
            f"{self.utente.nome} — "
            f"{self.get_tipo_display()} — "
            f"{self.data_hora_inicio:%d/%m/%Y %H:%M}"
        )

    @property
    def esta_ausente(self):
        agora = timezone.now()

        return (
            self.estado == EstadoAusenciaUtente.ATIVA
            and self.data_hora_inicio <= agora
            and self.data_hora_regresso is None
        )

    @property
    def fim_para_planeamento(self):
        return (
            self.data_hora_regresso
            or self.data_hora_fim_prevista
        )

    def clean(self):
        super().clean()

        erros = {}

        if (
            self.data_hora_fim_prevista
            and self.data_hora_inicio
            and self.data_hora_fim_prevista
            <= self.data_hora_inicio
        ):
            erros["data_hora_fim_prevista"] = (
                "O regresso previsto tem de ser posterior "
                "à saída."
            )

        if (
            self.data_hora_regresso
            and self.data_hora_inicio
            and self.data_hora_regresso
            < self.data_hora_inicio
        ):
            erros["data_hora_regresso"] = (
                "O regresso não pode ser anterior à saída."
            )

        if (
            self.estado == EstadoAusenciaUtente.ATIVA
            and self.data_hora_regresso
        ):
            erros["estado"] = (
                "Uma ausência ativa não pode ter o regresso "
                "registado."
            )

        if (
            self.estado == EstadoAusenciaUtente.TERMINADA
            and not self.data_hora_regresso
        ):
            erros["data_hora_regresso"] = (
                "Indique quando o utente regressou."
            )

        if (
            self.estado == EstadoAusenciaUtente.ATIVA
            and self.utente_id
            and self.utente.data_saida
        ):
            erros["utente"] = (
                "Não é possível registar uma ausência ativa "
                "para um utente com alta."
            )

        if not (self.motivo or "").strip():
            erros["motivo"] = (
                "Indique o motivo da ausência."
            )

        if erros:
            raise ValidationError(erros)

    def terminar(self, utilizador, momento=None):
        if self.estado != EstadoAusenciaUtente.ATIVA:
            raise ValidationError(
                "Apenas uma ausência ativa pode ser terminada."
            )

        momento = momento or timezone.now()

        self.estado = EstadoAusenciaUtente.TERMINADA
        self.data_hora_regresso = momento
        self.estado_atualizado_por = utilizador
        self.estado_atualizado_em = timezone.now()
        self.full_clean()
        self.save(
            update_fields=[
                "estado",
                "data_hora_regresso",
                "estado_atualizado_por",
                "estado_atualizado_em",
                "atualizado_em",
            ]
        )

        HistoricoAusenciaUtente.objects.create(
            ausencia=self,
            acao=AcaoHistoricoAusencia.TERMINADA,
            dados=self.dados_para_historico(),
            profissional=utilizador,
        )

    def cancelar(self, utilizador):
        if self.estado != EstadoAusenciaUtente.ATIVA:
            raise ValidationError(
                "Apenas uma ausência ativa pode ser cancelada."
            )

        self.estado = EstadoAusenciaUtente.CANCELADA
        self.data_hora_regresso = None
        self.estado_atualizado_por = utilizador
        self.estado_atualizado_em = timezone.now()
        self.full_clean()
        self.save(
            update_fields=[
                "estado",
                "data_hora_regresso",
                "estado_atualizado_por",
                "estado_atualizado_em",
                "atualizado_em",
            ]
        )

        HistoricoAusenciaUtente.objects.create(
            ausencia=self,
            acao=AcaoHistoricoAusencia.CANCELADA,
            dados=self.dados_para_historico(),
            profissional=utilizador,
        )

    def dados_para_historico(self):
        return {
            "utente_id": self.utente_id,
            "tipo": self.tipo,
            "data_hora_inicio": (
                self.data_hora_inicio.isoformat()
                if self.data_hora_inicio
                else None
            ),
            "data_hora_fim_prevista": (
                self.data_hora_fim_prevista.isoformat()
                if self.data_hora_fim_prevista
                else None
            ),
            "data_hora_regresso": (
                self.data_hora_regresso.isoformat()
                if self.data_hora_regresso
                else None
            ),
            "destino": self.destino,
            "motivo": self.motivo,
            "observacoes": self.observacoes,
            "estado": self.estado,
            "criado_por_id": self.criado_por_id,
            "estado_atualizado_por_id": (
                self.estado_atualizado_por_id
            ),
        }


class HistoricoAusenciaUtente(models.Model):
    ausencia = models.ForeignKey(
        AusenciaUtente,
        on_delete=models.PROTECT,
        related_name="historico",
        verbose_name="Ausência",
    )

    acao = models.CharField(
        "Ação",
        max_length=20,
        choices=AcaoHistoricoAusencia.choices,
    )

    dados = models.JSONField(
        "Dados guardados",
        default=dict,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historico_ausencias_registado",
        verbose_name="Profissional",
    )

    criado_em = models.DateTimeField(
        "Data da alteração",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Histórico de ausência"
        verbose_name_plural = "Histórico das ausências"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(
                fields=["ausencia", "criado_em"],
                name="enf_hist_aus_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_acao_display()} — "
            f"{self.ausencia.utente.nome}"
        )


class LocalQueda(models.TextChoices):
    QUARTO_CAMA = "QUARTO_CAMA", "Quarto/cama"
    CASA_BANHO = "CASA_BANHO", "Casa de banho"
    CORREDOR = "CORREDOR", "Corredor"
    EXTERIOR = "EXTERIOR", "Exterior"
    OUTRO = "OUTRO", "Outro"


class TipoQueda(models.TextChoices):
    ACIDENTAL = (
        "ACIDENTAL",
        "Acidental — fatores ambientais",
    )
    FISIOLOGICA = (
        "FISIOLOGICA",
        "Fisiológica — doença ou medicação",
    )
    COMPORTAMENTAL = (
        "COMPORTAMENTAL",
        "Comportamental — incumprimento",
    )
    NAO_DETERMINADA = (
        "NAO_DETERMINADA",
        "Não determinada",
    )


class GravidadeQueda(models.TextChoices):
    SEM_LESAO = "SEM_LESAO", "Sem lesão"
    MINOR = (
        "MINOR",
        "Lesão minor — equimose ou abrasão",
    )
    MODERADA = "MODERADA", "Lesão moderada"
    MAJOR = "MAJOR", "Lesão major"
    MORTE = "MORTE", "Morte"


class LesaoIdentificada(models.TextChoices):
    NENHUMA = "NENHUMA", "Nenhuma"
    LACERACAO = "LACERACAO", "Laceração"
    FRATURA = "FRATURA", "Fratura"
    TCE = "TCE", "TCE"
    HEMATOMA = "HEMATOMA", "Hematoma"
    LUXACAO = "LUXACAO", "Luxação"
    OUTRA = "OUTRA", "Outra"


class LocalizacaoLesao(models.TextChoices):
    CABECA_FACE = "CABECA_FACE", "Cabeça/face"
    MEMBROS_SUPERIORES = (
        "MEMBROS_SUPERIORES",
        "Membros superiores",
    )
    MEMBROS_INFERIORES = (
        "MEMBROS_INFERIORES",
        "Membros inferiores",
    )
    TRONCO = "TRONCO", "Tronco"
    OUTRA = "OUTRA", "Outra"


class AcompanhamentoQueda(models.TextChoices):
    SOZINHO = "SOZINHO", "Sozinho"
    ACOMPANHANTE = (
        "ACOMPANHANTE",
        "Com acompanhante",
    )
    PROFISSIONAL_SAUDE = (
        "PROFISSIONAL_SAUDE",
        "Com profissional de saúde",
    )
    NAO_DETERMINADO = (
        "NAO_DETERMINADO",
        "Não determinado",
    )


class AtividadeQueda(models.TextChoices):
    LEVANTE_CAMA = (
        "LEVANTE_CAMA",
        "Levante da cama",
    )
    DEAMBULACAO = "DEAMBULACAO", "Deambulação"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência"
    USO_WC = (
        "USO_WC",
        "Uso de WC ou arrastadeira",
    )
    BANHO = "BANHO", "Banho"
    OUTRA = "OUTRA", "Outra"


class FatorContribuinteQueda(models.TextChoices):
    CONFUSAO = (
        "CONFUSAO",
        "Confusão/desorientação",
    )
    HIPOTENSAO = (
        "HIPOTENSAO",
        "Hipotensão ortostática",
    )
    DEFICE_MOTOR = (
        "DEFICE_MOTOR",
        "Défice motor/equilíbrio",
    )
    URGENCIA_MICCIONAL = (
        "URGENCIA_MICCIONAL",
        "Urgência miccional",
    )
    DEFICE_VISUAL = (
        "DEFICE_VISUAL",
        "Défice visual",
    )
    PISO_ESCORREGADIO = (
        "PISO_ESCORREGADIO",
        "Piso escorregadio",
    )
    ILUMINACAO = (
        "ILUMINACAO",
        "Iluminação insuficiente",
    )
    CALCADO_VESTUARIO = (
        "CALCADO_VESTUARIO",
        "Calçado/vestuário inadequado",
    )
    OUTRO = "OUTRO", "Outro"


class EstadoGradesLaterais(models.TextChoices):
    LEVANTADAS = "LEVANTADAS", "Levantadas"
    BAIXADAS = "BAIXADAS", "Baixadas"
    NAO_APLICAVEL = (
        "NAO_APLICAVEL",
        "Não aplicável",
    )
    DESCONHECIDO = "DESCONHECIDO", "Desconhecido"


class DispositivoAuxilio(models.TextChoices):
    NENHUM = "NENHUM", "Nenhum"
    ANDARILHO = "ANDARILHO", "Andarilho"
    CANADIANAS = "CANADIANAS", "Canadiana(s)"
    BENGALA = "BENGALA", "Bengala"
    CADEIRA_RODAS = (
        "CADEIRA_RODAS",
        "Cadeira de rodas",
    )
    OUTRO = "OUTRO", "Outro"


class OpcaoSimNao(models.TextChoices):
    SIM = "SIM", "Sim"
    NAO = "NAO", "Não"


class NivelRiscoMorse(models.TextChoices):
    BAIXO = "BAIXO", "Baixo risco — inferior a 25"
    MODERADO = (
        "MODERADO",
        "Risco moderado — 25 a 50",
    )
    ALTO = "ALTO", "Alto risco — 51 ou superior"
    NAO_AVALIADO = (
        "NAO_AVALIADO",
        "Não avaliado",
    )


class EstadoMedidasPreventivas(models.TextChoices):
    SIM = "SIM", "Sim"
    NAO = "NAO", "Não"
    PARCIALMENTE = "PARCIALMENTE", "Parcialmente"


class IntervencaoQueda(models.TextChoices):
    AVALIACAO_CLINICA = (
        "AVALIACAO_CLINICA",
        "Avaliação clínica imediata",
    )
    EXAME_NEUROLOGICO = (
        "EXAME_NEUROLOGICO",
        "Exame neurológico",
    )
    SINAIS_VITAIS = (
        "SINAIS_VITAIS",
        "Controlo de sinais vitais",
    )
    PENSO_SUTURA = (
        "PENSO_SUTURA",
        "Penso/sutura",
    )
    IMOBILIZACAO = "IMOBILIZACAO", "Imobilização"
    IMAGEM = "IMAGEM", "Imagem — Rx/TAC"
    TRANSFERENCIA_URGENCIA = (
        "TRANSFERENCIA_URGENCIA",
        "Transferência para Serviço de Urgência",
    )
    OUTRA = "OUTRA", "Outra"


class EstadoNotificacaoFamiliar(models.TextChoices):
    SIM = "SIM", "Sim"
    NAO = "NAO", "Não"
    NAO_APLICAVEL = (
        "NAO_APLICAVEL",
        "Não aplicável",
    )


class EstadoReavaliacaoMorse(models.TextChoices):
    REALIZADA = "REALIZADA", "Realizada"
    PENDENTE = "PENDENTE", "Pendente"
    NAO_APLICAVEL = (
        "NAO_APLICAVEL",
        "Não aplicável",
    )


class MedidaCorretivaQueda(models.TextChoices):
    REVISAO_MEDICACAO = (
        "REVISAO_MEDICACAO",
        "Revisão da medicação",
    )
    CAMA_BAIXA = (
        "CAMA_BAIXA",
        "Cama em posição baixa",
    )
    CAMPAINHA = (
        "CAMPAINHA",
        "Campainha ao alcance",
    )
    SINALETICA_RISCO = (
        "SINALETICA_RISCO",
        "Sinalética de risco",
    )
    VIGILANCIA_REFORCADA = (
        "VIGILANCIA_REFORCADA",
        "Vigilância reforçada",
    )
    FISIOTERAPIA = "FISIOTERAPIA", "Fisioterapia"
    EDUCACAO = (
        "EDUCACAO",
        "Educação ao utente/família",
    )
    OUTRA = "OUTRA", "Outra"


class EstadoNotificacaoInstitucional(models.TextChoices):
    SIM = "SIM", "Sim"
    NAO = "NAO", "Não"
    PENDENTE = "PENDENTE", "Pendente"


class RegistoQueda(models.Model):
    AREA_CLINICA_CODIGO = AREA_CLINICA_ENFERMAGEM

    registo_enfermagem = models.OneToOneField(
        RegistoEnfermagem,
        on_delete=models.PROTECT,
        related_name="queda",
        verbose_name="Registo de Enfermagem",
    )

    # Identificação guardada no momento da notificação
    identificacao_utente = models.JSONField(
        "Identificação do utente",
        default=dict,
        blank=True,
    )

    servico_unidade = models.CharField(
        "Serviço/unidade",
        max_length=150,
        blank=True,
    )

    diagnostico_principal = models.TextField(
        "Diagnóstico principal",
        blank=True,
    )

    medico_assistente = models.CharField(
        "Médico assistente",
        max_length=200,
        blank=True,
    )

    # Dados da ocorrência
    data_hora_queda = models.DateTimeField(
        "Data e hora da queda",
    )

    local_queda = models.CharField(
        "Local exato",
        max_length=30,
        choices=LocalQueda.choices,
    )

    local_detalhe = models.CharField(
        "Outro local",
        max_length=200,
        blank=True,
    )

    # Classificação
    tipo_queda = models.CharField(
        "Tipo de queda",
        max_length=30,
        choices=TipoQueda.choices,
    )

    gravidade = models.CharField(
        "Grau de lesão",
        max_length=20,
        choices=GravidadeQueda.choices,
        default=GravidadeQueda.SEM_LESAO,
    )

    lesoes_identificadas = models.JSONField(
        "Lesões identificadas",
        default=list,
        blank=True,
    )

    lesao_outra = models.CharField(
        "Outra lesão",
        max_length=200,
        blank=True,
    )

    localizacoes_lesao = models.JSONField(
        "Localização das lesões",
        default=list,
        blank=True,
    )

    localizacao_outra = models.CharField(
        "Outra localização",
        max_length=200,
        blank=True,
    )

    # Circunstâncias
    doente_estava = models.CharField(
        "O utente estava",
        max_length=30,
        choices=AcompanhamentoQueda.choices,
        blank=True,
    )

    atividade_no_momento = models.CharField(
        "Atividade no momento",
        max_length=30,
        choices=AtividadeQueda.choices,
        blank=True,
    )

    atividade_outra = models.CharField(
        "Outra atividade",
        max_length=200,
        blank=True,
    )

    fatores_contribuintes = models.JSONField(
        "Fatores contribuintes",
        default=list,
        blank=True,
    )

    fator_contribuinte_outro = models.CharField(
        "Outro fator contribuinte",
        max_length=200,
        blank=True,
    )

    grades_laterais = models.CharField(
        "Grades laterais da cama",
        max_length=30,
        choices=EstadoGradesLaterais.choices,
        blank=True,
    )

    dispositivo_auxilio = models.CharField(
        "Dispositivo de auxílio",
        max_length=30,
        choices=DispositivoAuxilio.choices,
        blank=True,
    )

    dispositivo_auxilio_outro = models.CharField(
        "Outro dispositivo de auxílio",
        max_length=200,
        blank=True,
    )

    # Avaliação Morse anterior
    morse_aplicada = models.CharField(
        "Escala de Morse aplicada antes da queda",
        max_length=10,
        choices=OpcaoSimNao.choices,
        blank=True,
    )

    score_morse_previo = models.PositiveSmallIntegerField(
        "Score Morse anterior",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(125),
        ],
    )

    nivel_risco_previo = models.CharField(
        "Nível de risco anterior",
        max_length=20,
        choices=NivelRiscoMorse.choices,
        default=NivelRiscoMorse.NAO_AVALIADO,
    )

    medidas_preventivas_implementadas = models.CharField(
        "Medidas preventivas implementadas",
        max_length=20,
        choices=EstadoMedidasPreventivas.choices,
        blank=True,
    )

    # Resposta imediata
    intervencoes_realizadas = models.JSONField(
        "Intervenções efetuadas",
        default=list,
        blank=True,
    )

    intervencao_outra = models.CharField(
        "Outra intervenção",
        max_length=250,
        blank=True,
    )

    medico_notificado = models.CharField(
        "Médico notificado",
        max_length=10,
        choices=OpcaoSimNao.choices,
        blank=True,
    )

    medico_notificado_em = models.DateTimeField(
        "Data e hora da notificação ao médico",
        null=True,
        blank=True,
    )

    medico_nao_notificado_justificacao = models.TextField(
        "Justificação para médico não notificado",
        blank=True,
    )

    familiar_notificado = models.CharField(
        "Familiar/representante notificado",
        max_length=20,
        choices=EstadoNotificacaoFamiliar.choices,
        blank=True,
    )

    familiar_notificado_em = models.DateTimeField(
        "Data e hora da notificação ao familiar",
        null=True,
        blank=True,
    )

    descricao_ocorrencia = models.TextField(
        "Descrição da queda",
    )

    # Medidas corretivas e seguimento
    reavaliacao_morse_estado = models.CharField(
        "Reavaliação Morse pós-queda",
        max_length=20,
        choices=EstadoReavaliacaoMorse.choices,
        blank=True,
    )

    score_morse_pos = models.PositiveSmallIntegerField(
        "Novo score Morse",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(125),
        ],
    )

    medidas_corretivas = models.JSONField(
        "Medidas corretivas implementadas",
        default=list,
        blank=True,
    )

    medida_corretiva_outra = models.CharField(
        "Outra medida corretiva",
        max_length=250,
        blank=True,
    )

    observacoes = models.TextField(
        "Observações/seguimento",
        blank=True,
    )

    # Notificação institucional
    notificacao_institucional_estado = models.CharField(
        "Introduzido no sistema de notificação",
        max_length=20,
        choices=EstadoNotificacaoInstitucional.choices,
        default=EstadoNotificacaoInstitucional.PENDENTE,
    )

    data_notificacao_institucional = models.DateField(
        "Data da notificação institucional",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(
        "Criado em",
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        "Atualizado em",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Ficha de notificação de queda"
        verbose_name_plural = (
            "Fichas de notificação de quedas"
        )
        ordering = [
            "-data_hora_queda",
            "-criado_em",
        ]
        indexes = [
            models.Index(
                fields=["data_hora_queda"],
                name="enf_queda_data",
            ),
            models.Index(
                fields=["gravidade"],
                name="enf_queda_gravidade",
            ),
            models.Index(
                fields=["notificacao_institucional_estado"],
                name="enf_queda_notificacao",
            ),
        ]

    def __str__(self):
        return (
            f"Queda de {self.utente.nome} "
            f"em {self.data_hora_queda:%d/%m/%Y %H:%M}"
        )

    @property
    def utente(self):
        return self.registo_enfermagem.utente

    @property
    def profissional(self):
        return self.registo_enfermagem.profissional

    @property
    def profissional_id(self):
        return self.registo_enfermagem.profissional_id

    @property
    def visibilidade(self):
        return self.registo_enfermagem.visibilidade

    @property
    def prazo_limite_notificacao(self):
        if not self.data_hora_queda:
            return None

        return self.data_hora_queda + timedelta(
            hours=24
        )

    @property
    def notificacao_fora_prazo(self):
        if not self.data_hora_queda:
            return False

        momento_notificacao = (
            self.criado_em
            if self.criado_em
            else timezone.now()
        )

        return (
            momento_notificacao
            > self.prazo_limite_notificacao
        )

    def preencher_identificacao_utente(self):
        utente = self.utente

        data_nascimento = utente.data_nascimento
        idade = None

        if data_nascimento and self.data_hora_queda:
            data_referencia = (
                self.data_hora_queda.date()
            )

            idade = (
                data_referencia.year
                - data_nascimento.year
                - (
                    (
                        data_referencia.month,
                        data_referencia.day,
                    )
                    < (
                        data_nascimento.month,
                        data_nascimento.day,
                    )
                )
            )

        quarto = ""
        piso = ""

        if utente.quarto:
            quarto = str(utente.quarto)

            if hasattr(
                utente.quarto,
                "get_piso_display",
            ):
                piso = (
                    utente.quarto.get_piso_display()
                )

        genero = ""

        if hasattr(utente, "get_genero_display"):
            genero = utente.get_genero_display() or ""

        tipo_internamento = ""

        if hasattr(
            utente,
            "get_tipo_internamento_display",
        ):
            tipo_internamento = (
                utente.get_tipo_internamento_display()
                or ""
            )

        if not self.servico_unidade:
            self.servico_unidade = (
                tipo_internamento
            )

        self.identificacao_utente = {
            "nome": utente.nome,
            "numero_processo": (
                utente.numero_processo
            ),
            "data_nascimento": (
                data_nascimento.isoformat()
                if data_nascimento
                else None
            ),
            "idade": idade,
            "genero": genero,
            "servico_unidade": self.servico_unidade,
            "quarto": quarto,
            "piso": piso,
            "data_admissao": (
                utente.data_entrada.isoformat()
                if utente.data_entrada
                else None
            ),
            "diagnostico_principal": (
                self.diagnostico_principal
            ),
            "medico_assistente": (
                self.medico_assistente
            ),
        }

    def clean(self):
        super().clean()

        erros = {}

        agora = timezone.now()

        if (
            self.data_hora_queda
            and self.data_hora_queda > agora
        ):
            erros["data_hora_queda"] = (
                "A data e hora da queda não pode "
                "estar no futuro."
            )

        listas_escolhas = [
            (
                "lesoes_identificadas",
                self.lesoes_identificadas,
                LesaoIdentificada.choices,
            ),
            (
                "localizacoes_lesao",
                self.localizacoes_lesao,
                LocalizacaoLesao.choices,
            ),
            (
                "fatores_contribuintes",
                self.fatores_contribuintes,
                FatorContribuinteQueda.choices,
            ),
            (
                "intervencoes_realizadas",
                self.intervencoes_realizadas,
                IntervencaoQueda.choices,
            ),
            (
                "medidas_corretivas",
                self.medidas_corretivas,
                MedidaCorretivaQueda.choices,
            ),
        ]

        for campo, valores, escolhas in listas_escolhas:
            if not isinstance(valores, list):
                erros[campo] = (
                    "O valor deve ser uma lista "
                    "de opções."
                )
                continue

            valores_permitidos = {
                valor
                for valor, nome in escolhas
            }

            invalidos = set(valores) - valores_permitidos

            if invalidos:
                erros[campo] = (
                    "Foram selecionadas opções inválidas."
                )

        lesoes = self.lesoes_identificadas or []

        if (
            LesaoIdentificada.NENHUMA in lesoes
            and len(lesoes) > 1
        ):
            erros["lesoes_identificadas"] = (
                "A opção 'Nenhuma' não pode ser "
                "selecionada com outras lesões."
            )

        if (
            self.gravidade == GravidadeQueda.SEM_LESAO
            and lesoes
            and LesaoIdentificada.NENHUMA not in lesoes
        ):
            erros["lesoes_identificadas"] = (
                "Uma queda sem lesão não pode ter "
                "lesões identificadas."
            )

        if (
            self.gravidade != GravidadeQueda.SEM_LESAO
            and (
                not lesoes
                or LesaoIdentificada.NENHUMA in lesoes
            )
        ):
            erros["lesoes_identificadas"] = (
                "Selecione pelo menos uma lesão."
            )

        if (
            LesaoIdentificada.OUTRA in lesoes
            and not self.lesao_outra.strip()
        ):
            erros["lesao_outra"] = (
                "Indique qual foi a outra lesão."
            )

        localizacoes = (
            self.localizacoes_lesao or []
        )

        if (
            LesaoIdentificada.NENHUMA not in lesoes
            and lesoes
            and not localizacoes
        ):
            erros["localizacoes_lesao"] = (
                "Selecione a localização da lesão."
            )

        if (
            LocalizacaoLesao.OUTRA in localizacoes
            and not self.localizacao_outra.strip()
        ):
            erros["localizacao_outra"] = (
                "Indique a outra localização."
            )

        if (
            self.local_queda == LocalQueda.OUTRO
            and not self.local_detalhe.strip()
        ):
            erros["local_detalhe"] = (
                "Indique o outro local da queda."
            )

        if (
            self.atividade_no_momento
            == AtividadeQueda.OUTRA
            and not self.atividade_outra.strip()
        ):
            erros["atividade_outra"] = (
                "Indique a outra atividade."
            )

        if (
            FatorContribuinteQueda.OUTRO
            in (self.fatores_contribuintes or [])
            and not self.fator_contribuinte_outro.strip()
        ):
            erros["fator_contribuinte_outro"] = (
                "Indique o outro fator contribuinte."
            )

        if (
            self.dispositivo_auxilio
            == DispositivoAuxilio.OUTRO
            and not self.dispositivo_auxilio_outro.strip()
        ):
            erros["dispositivo_auxilio_outro"] = (
                "Indique o outro dispositivo."
            )

        if self.morse_aplicada == OpcaoSimNao.SIM:
            if self.score_morse_previo is None:
                erros["score_morse_previo"] = (
                    "Indique o score Morse anterior."
                )
            elif self.score_morse_previo < 25:
                self.nivel_risco_previo = (
                    NivelRiscoMorse.BAIXO
                )
            elif self.score_morse_previo <= 50:
                self.nivel_risco_previo = (
                    NivelRiscoMorse.MODERADO
                )
            else:
                self.nivel_risco_previo = (
                    NivelRiscoMorse.ALTO
                )
        else:
            self.score_morse_previo = None
            self.nivel_risco_previo = (
                NivelRiscoMorse.NAO_AVALIADO
            )

        if (
            IntervencaoQueda.OUTRA
            in (self.intervencoes_realizadas or [])
            and not self.intervencao_outra.strip()
        ):
            erros["intervencao_outra"] = (
                "Indique a outra intervenção."
            )

        if self.medico_notificado == OpcaoSimNao.SIM:
            if not self.medico_notificado_em:
                erros["medico_notificado_em"] = (
                    "Indique quando o médico foi notificado."
                )
        elif self.medico_notificado == OpcaoSimNao.NAO:
            if not (
                self.medico_nao_notificado_justificacao
                or ""
            ).strip():
                erros[
                    "medico_nao_notificado_justificacao"
                ] = (
                    "Justifique por que motivo o médico "
                    "não foi notificado."
                )

        if (
            self.familiar_notificado
            == EstadoNotificacaoFamiliar.SIM
            and not self.familiar_notificado_em
        ):
            erros["familiar_notificado_em"] = (
                "Indique quando o familiar foi notificado."
            )

        if (
            self.reavaliacao_morse_estado
            == EstadoReavaliacaoMorse.REALIZADA
            and self.score_morse_pos is None
        ):
            erros["score_morse_pos"] = (
                "Indique o novo score Morse."
            )

        if (
            MedidaCorretivaQueda.OUTRA
            in (self.medidas_corretivas or [])
            and not self.medida_corretiva_outra.strip()
        ):
            erros["medida_corretiva_outra"] = (
                "Indique a outra medida corretiva."
            )

        if (
            self.notificacao_institucional_estado
            == EstadoNotificacaoInstitucional.SIM
            and not self.data_notificacao_institucional
        ):
            erros["data_notificacao_institucional"] = (
                "Indique a data da notificação."
            )

        if erros:
            raise ValidationError(erros)

    def dados_para_historico(self):
        campos = [
            "identificacao_utente",
            "servico_unidade",
            "diagnostico_principal",
            "medico_assistente",
            "data_hora_queda",
            "local_queda",
            "local_detalhe",
            "tipo_queda",
            "gravidade",
            "lesoes_identificadas",
            "lesao_outra",
            "localizacoes_lesao",
            "localizacao_outra",
            "doente_estava",
            "atividade_no_momento",
            "atividade_outra",
            "fatores_contribuintes",
            "fator_contribuinte_outro",
            "grades_laterais",
            "dispositivo_auxilio",
            "dispositivo_auxilio_outro",
            "morse_aplicada",
            "score_morse_previo",
            "nivel_risco_previo",
            "medidas_preventivas_implementadas",
            "intervencoes_realizadas",
            "intervencao_outra",
            "medico_notificado",
            "medico_notificado_em",
            "medico_nao_notificado_justificacao",
            "familiar_notificado",
            "familiar_notificado_em",
            "descricao_ocorrencia",
            "reavaliacao_morse_estado",
            "score_morse_pos",
            "medidas_corretivas",
            "medida_corretiva_outra",
            "observacoes",
            "notificacao_institucional_estado",
            "data_notificacao_institucional",
        ]

        dados = {
            "registo_enfermagem_id": (
                self.registo_enfermagem_id
            )
        }

        for campo in campos:
            valor = getattr(self, campo)

            if hasattr(valor, "isoformat"):
                valor = valor.isoformat()

            dados[campo] = valor

        return dados


class AcaoHistoricoClinico(models.TextChoices):
    CRIADO = "CRIADO", "Registo criado"
    ALTERADO = "ALTERADO", "Registo alterado"


class HistoricoRegistoEnfermagem(models.Model):
    registo = models.ForeignKey(
        RegistoEnfermagem,
        on_delete=models.PROTECT,
        related_name="historico",
    )

    acao = models.CharField(
        "Ação",
        max_length=20,
        choices=AcaoHistoricoClinico.choices,
    )

    dados = models.JSONField(
        "Dados guardados",
        default=dict,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historico_enfermagem_registado",
    )

    criado_em = models.DateTimeField(
        "Data da alteração",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = (
            "Histórico de registo de Enfermagem"
        )
        verbose_name_plural = (
            "Histórico dos registos de Enfermagem"
        )
        ordering = ["-criado_em"]
        indexes = [
            models.Index(
                fields=["registo", "criado_em"],
                name="enf_hist_reg_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_acao_display()} — "
            f"{self.registo.utente.nome}"
        )


class HistoricoRegistoQueda(models.Model):
    registo = models.ForeignKey(
        RegistoQueda,
        on_delete=models.PROTECT,
        related_name="historico",
    )

    acao = models.CharField(
        "Ação",
        max_length=20,
        choices=AcaoHistoricoClinico.choices,
    )

    dados = models.JSONField(
        "Dados guardados",
        default=dict,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historico_quedas_registado",
    )

    criado_em = models.DateTimeField(
        "Data da alteração",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Histórico de registo de queda"
        verbose_name_plural = (
            "Histórico dos registos de quedas"
        )
        ordering = ["-criado_em"]
        indexes = [
            models.Index(
                fields=["registo", "criado_em"],
                name="enf_hist_queda_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_acao_display()} — "
            f"{self.registo.utente.nome}"
        )
