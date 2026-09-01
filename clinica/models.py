from django.contrib.auth.models import Group
from django.db import models


class VisibilidadeRegistoClinico(models.TextChoices):
    CONFIDENCIAL = (
        "CONFIDENCIAL",
        "Apenas eu",
    )
    GRUPO = (
        "GRUPO",
        "Grupo profissional",
    )
    TODOS = (
        "TODOS",
        "Equipas clínicas autorizadas",
    )


class AreaClinica(models.Model):
    codigo = models.SlugField(
        "Código da área",
        max_length=50,
        unique=True,
        help_text=(
            "Identificador interno da área. "
            "Exemplo: enfermagem ou fisioterapia."
        ),
    )

    nome = models.CharField(
        "Nome da área",
        max_length=100,
        unique=True,
    )

    descricao = models.TextField(
        "Descrição",
        blank=True,
    )

    grupos_responsaveis = models.ManyToManyField(
        Group,
        blank=True,
        related_name="areas_clinicas_responsaveis",
        verbose_name="Equipas responsáveis",
        help_text=(
            "Estas equipas podem criar registos nesta área "
            "e consultar os registos com visibilidade "
            "'Grupo profissional'."
        ),
    )

    grupos_partilha_geral = models.ManyToManyField(
        Group,
        blank=True,
        related_name="areas_clinicas_partilhadas",
        verbose_name="Equipas com acesso geral",
        help_text=(
            "Estas equipas podem consultar os registos "
            "com visibilidade 'Equipas clínicas autorizadas'."
        ),
    )

    ativa = models.BooleanField(
        "Área ativa",
        default=True,
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
        verbose_name = "Configuração de área clínica"
        verbose_name_plural = (
            "Configurações das áreas clínicas"
        )
        ordering = ["nome"]
        indexes = [
            models.Index(
                fields=["codigo", "ativa"],
                name="clinica_area_codigo_ativa",
            ),
        ]

    def __str__(self):
        return self.nome

    def utilizador_e_responsavel(self, utilizador):
        if not utilizador or not utilizador.is_authenticated:
            return False

        grupos_utilizador = utilizador.groups.values_list(
            "pk",
            flat=True,
        )

        return self.grupos_responsaveis.filter(
            pk__in=grupos_utilizador,
        ).exists()

    def utilizador_tem_acesso_geral(self, utilizador):
        if not utilizador or not utilizador.is_authenticated:
            return False

        grupos_utilizador = utilizador.groups.values_list(
            "pk",
            flat=True,
        )

        return self.grupos_partilha_geral.filter(
            pk__in=grupos_utilizador,
        ).exists()

    def utilizador_pode_ver(
        self,
        utilizador,
        visibilidade,
        autor_id,
    ):
        if not utilizador or not utilizador.is_authenticated:
            return False

        if utilizador.pk == autor_id:
            return True

        if (
            visibilidade
            == VisibilidadeRegistoClinico.CONFIDENCIAL
        ):
            return False

        if (
            visibilidade
            == VisibilidadeRegistoClinico.GRUPO
        ):
            return self.utilizador_e_responsavel(
                utilizador
            )

        if (
            visibilidade
            == VisibilidadeRegistoClinico.TODOS
        ):
            return self.utilizador_tem_acesso_geral(
                utilizador
            )

        return False