from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CategoriaProdutoCozinha(models.TextChoices):
    AGUA = "AGUA", "Água"
    BEBIDA = "BEBIDA", "Outra bebida"
    BOLACHA = "BOLACHA", "Bolacha"
    LACTICINIO = "LACTICINIO", "Laticínio"
    PAPA_FARINHA = "PAPA_FARINHA", "Papa/farinha"
    PAO_SANDES = "PAO_SANDES", "Pão/sandes"
    SOPA_SOBREMESA = "SOPA_SOBREMESA", "Sopa/sobremesa"
    CONSUMIVEL = "CONSUMIVEL", "Consumível"
    OUTRO = "OUTRO", "Outro"


class UnidadeMedidaCozinha(models.TextChoices):
    UNIDADE = "UN", "Unidade"
    EMBALAGEM = "EMB", "Embalagem"
    PACOTE = "PCT", "Pacote"
    GARRAFA = "GAR", "Garrafa"
    LITRO = "L", "Litro"
    PORCAO = "POR", "Porção"
    OUTRA = "OUTRA", "Outra"


class EstadoPedidoCozinha(models.TextChoices):
    RASCUNHO = "RASCUNHO", "Rascunho"
    ENVIADO = "ENVIADO", "Enviado"
    REABERTO = "REABERTO", "Reaberto para correção"
    EM_PREPARACAO = "EM_PREPARACAO", "Em preparação"
    ENTREGUE = "ENTREGUE", "Entregue"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    DIVERGENCIA = "DIVERGENCIA", "Com divergência"
    CANCELADO = "CANCELADO", "Cancelado"


class TipoPedidoCozinha(models.TextChoices):
    REFEICOES = "REFEICOES", "Pedido de refeições"
    SUPLEMENTOS = "SUPLEMENTOS", "Pedido de suplementos"


class AcaoHistoricoCozinha(models.TextChoices):
    CRIADO = "CRIADO", "Criado"
    ALTERADO = "ALTERADO", "Quantidades alteradas"
    ENVIADO = "ENVIADO", "Enviado à Cozinha"
    REABERTO = "REABERTO", "Reaberto para correção"
    EM_PREPARACAO = "EM_PREPARACAO", "Iniciada a preparação"
    ENTREGUE = "ENTREGUE", "Entrega registada"
    CONFIRMADO = "CONFIRMADO", "Receção confirmada"
    DIVERGENCIA = "DIVERGENCIA", "Divergência registada"
    CONSUMO = "CONSUMO", "Consumo registado"
    CANCELADO = "CANCELADO", "Cancelado"


class UnidadeCozinha(models.Model):
    codigo = models.SlugField(
        "Código",
        max_length=40,
        unique=True,
    )

    nome = models.CharField(
        "Unidade/piso",
        max_length=120,
        unique=True,
    )

    # Mantido temporariamente por compatibilidade com o admin e
    # com as migrações existentes. As permissões deixam de usar
    # esta relação: o acesso é feito pelo grupo UCCI_Enfermagem.
    enfermeiros = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="unidades_cozinha_atribuidas",
        verbose_name="Profissionais de Enfermagem",
    )

    ativa = models.BooleanField(
        "Ativa",
        default=True,
    )

    ordem = models.PositiveSmallIntegerField(
        "Ordem",
        default=0,
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
        verbose_name = "Unidade/piso da Cozinha"
        verbose_name_plural = "Unidades/pisos da Cozinha"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class ProdutoCozinha(models.Model):
    codigo = models.SlugField(
        "Código",
        max_length=80,
        unique=True,
    )

    nome = models.CharField(
        "Produto",
        max_length=150,
        unique=True,
    )

    categoria = models.CharField(
        "Categoria",
        max_length=30,
        choices=CategoriaProdutoCozinha.choices,
        default=CategoriaProdutoCozinha.OUTRO,
    )

    unidade_medida = models.CharField(
        "Unidade de medida",
        max_length=10,
        choices=UnidadeMedidaCozinha.choices,
        default=UnidadeMedidaCozinha.UNIDADE,
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

    criado_em = models.DateTimeField(
        "Criado em",
        auto_now_add=True,
    )

    atualizado_em = models.DateTimeField(
        "Atualizado em",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Produto da Cozinha"
        verbose_name_plural = "Produtos da Cozinha"
        ordering = ["ordem", "nome"]
        indexes = [
            models.Index(
                fields=["ativo", "ordem"],
                name="coz_prod_ativo_ordem",
            ),
        ]

    def __str__(self):
        return self.nome


class TipoRefeicao(models.Model):
    codigo = models.SlugField(
        "Código",
        max_length=60,
        unique=True,
    )

    nome = models.CharField(
        "Tipo de refeição",
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
        verbose_name = "Tipo de refeição"
        verbose_name_plural = "Tipos de refeição"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class TipoDieta(models.Model):
    codigo = models.SlugField(
        "Código",
        max_length=60,
        unique=True,
    )

    nome = models.CharField(
        "Tipo de dieta",
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
        verbose_name = "Tipo de dieta"
        verbose_name_plural = "Tipos de dieta"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class PedidoCozinha(models.Model):
    HORA_LIMITE_EDICAO = time(hour=12)

    unidade = models.ForeignKey(
        UnidadeCozinha,
        on_delete=models.PROTECT,
        related_name="pedidos",
        verbose_name="Unidade/piso",
    )

    tipo = models.CharField(
        "Tipo de pedido",
        max_length=20,
        choices=TipoPedidoCozinha.choices,
        default=TipoPedidoCozinha.SUPLEMENTOS,
        db_index=True,
    )

    data_servico = models.DateField(
        "Data do pedido/serviço",
        db_index=True,
    )

    estado = models.CharField(
        "Estado",
        max_length=25,
        choices=EstadoPedidoCozinha.choices,
        default=EstadoPedidoCozinha.RASCUNHO,
        db_index=True,
    )

    observacoes_enfermagem = models.TextField(
        "Observações da Enfermagem",
        blank=True,
    )

    observacoes_cozinha = models.TextField(
        "Observações da Cozinha",
        blank=True,
    )

    observacoes_confirmacao = models.TextField(
        "Observações da confirmação",
        blank=True,
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_criados",
        verbose_name="Criado por",
    )

    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_enviados",
        verbose_name="Enviado por",
        null=True,
        blank=True,
    )

    enviado_em = models.DateTimeField(
        "Enviado em",
        null=True,
        blank=True,
    )

    preparacao_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_em_preparacao",
        verbose_name="Preparação iniciada por",
        null=True,
        blank=True,
    )

    preparacao_em = models.DateTimeField(
        "Preparação iniciada em",
        null=True,
        blank=True,
    )

    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_entregues",
        verbose_name="Entrega registada por",
        null=True,
        blank=True,
    )

    entregue_em = models.DateTimeField(
        "Entregue em",
        null=True,
        blank=True,
    )

    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_confirmados",
        verbose_name="Confirmado por",
        null=True,
        blank=True,
    )

    confirmado_em = models.DateTimeField(
        "Confirmado em",
        null=True,
        blank=True,
    )

    reaberto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cozinha_reabertos",
        verbose_name="Reaberto por",
        null=True,
        blank=True,
    )

    reaberto_em = models.DateTimeField(
        "Reaberto em",
        null=True,
        blank=True,
    )

    motivo_reabertura = models.TextField(
        "Motivo da reabertura",
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
        verbose_name = "Pedido à Cozinha"
        verbose_name_plural = "Pedidos à Cozinha"
        ordering = [
            "-data_servico",
            "unidade_id",
            "tipo",
            "-criado_em",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "unidade",
                    "data_servico",
                ],
                condition=(
                    models.Q(
                        tipo=TipoPedidoCozinha.REFEICOES,
                    )
                    & ~models.Q(
                        estado=EstadoPedidoCozinha.CANCELADO,
                    )
                ),
                name="coz_refeicao_unidade_data_ativa",
            ),
            models.UniqueConstraint(
                fields=["unidade"],
                condition=models.Q(
                    tipo=TipoPedidoCozinha.SUPLEMENTOS,
                    estado__in=[
                        EstadoPedidoCozinha.RASCUNHO,
                        EstadoPedidoCozinha.ENVIADO,
                        EstadoPedidoCozinha.REABERTO,
                        EstadoPedidoCozinha.EM_PREPARACAO,
                    ],
                ),
                name="coz_suplemento_aberto_unidade",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "tipo",
                    "data_servico",
                    "estado",
                ],
                name="coz_pedido_tipo_data_estado",
            ),
            models.Index(
                fields=["unidade", "data_servico"],
                name="coz_pedido_unidade_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} — "
            f"{self.unidade.nome} — "
            f"{self.data_servico:%d/%m/%Y}"
        )

    @property
    def prazo_edicao(self):
        limite = datetime.combine(
            self.data_servico,
            self.HORA_LIMITE_EDICAO,
        )

        if settings.USE_TZ:
            return timezone.make_aware(
                limite,
                timezone.get_current_timezone(),
            )

        return limite

    @property
    def dentro_prazo_edicao(self):
        return timezone.now() < self.prazo_edicao

    @property
    def pode_editar_quantidades(self):
        if self.estado == EstadoPedidoCozinha.REABERTO:
            return True

        if self.tipo == TipoPedidoCozinha.REFEICOES:
            return (
                self.estado
                in {
                    EstadoPedidoCozinha.RASCUNHO,
                    EstadoPedidoCozinha.ENVIADO,
                }
                and self.dentro_prazo_edicao
            )

        return self.estado in {
            EstadoPedidoCozinha.RASCUNHO,
            EstadoPedidoCozinha.ENVIADO,
        }

    @property
    def pode_iniciar_preparacao(self):
        # A Cozinha pode começar imediatamente qualquer pedido
        # enviado, sem esperar pelas 12:00.
        return self.estado == EstadoPedidoCozinha.ENVIADO

    @property
    def tem_divergencias(self):
        if self.tipo != TipoPedidoCozinha.SUPLEMENTOS:
            return False

        return any(
            linha.tem_divergencia
            for linha in self.linhas_produtos.all()
        )

    def clean(self):
        super().clean()

        if (
            not self.pk
            and self.data_servico
            and self.data_servico < timezone.localdate()
        ):
            raise ValidationError(
                {
                    "data_servico": (
                        "Não é possível criar um pedido "
                        "para uma data anterior."
                    )
                }
            )

        if (
            self.estado == EstadoPedidoCozinha.REABERTO
            and not self.motivo_reabertura.strip()
        ):
            raise ValidationError(
                {
                    "motivo_reabertura": (
                        "Indique o motivo da reabertura."
                    )
                }
            )

        estados_confirmacao_enfermagem = {
            EstadoPedidoCozinha.CONFIRMADO,
            EstadoPedidoCozinha.DIVERGENCIA,
        }

        if (
            self.tipo == TipoPedidoCozinha.REFEICOES
            and self.estado in estados_confirmacao_enfermagem
        ):
            raise ValidationError(
                {
                    "estado": (
                        "Os pedidos de refeições podem ser "
                        "preparados e entregues pela Cozinha, "
                        "mas não necessitam de confirmação "
                        "pela Enfermagem."
                    )
                }
            )

    def dados_para_historico(self):
        dados = {
            "unidade_id": self.unidade_id,
            "tipo": self.tipo,
            "data_servico": (
                self.data_servico.isoformat()
                if self.data_servico
                else None
            ),
            "estado": self.estado,
            "observacoes_enfermagem": self.observacoes_enfermagem,
            "observacoes_cozinha": self.observacoes_cozinha,
            "observacoes_confirmacao": self.observacoes_confirmacao,
            "criado_por_id": self.criado_por_id,
            "enviado_por_id": self.enviado_por_id,
            "preparacao_por_id": self.preparacao_por_id,
            "entregue_por_id": self.entregue_por_id,
            "confirmado_por_id": self.confirmado_por_id,
            "produtos": [],
            "refeicoes": [],
        }

        if self.pk:
            dados["produtos"] = [
                linha.dados_para_historico()
                for linha in self.linhas_produtos.select_related(
                    "produto"
                )
            ]
            dados["refeicoes"] = [
                linha.dados_para_historico()
                for linha in self.linhas_refeicoes.select_related(
                    "tipo_refeicao",
                    "tipo_dieta",
                )
            ]

        return dados


class LinhaProdutoPedido(models.Model):
    VALIDADOR_QUANTIDADE = [
        MinValueValidator(0),
    ]

    pedido = models.ForeignKey(
        PedidoCozinha,
        on_delete=models.CASCADE,
        related_name="linhas_produtos",
        verbose_name="Pedido",
    )

    produto = models.ForeignKey(
        ProdutoCozinha,
        on_delete=models.PROTECT,
        related_name="linhas_pedido",
        verbose_name="Produto",
    )

    quantidade_solicitada = models.DecimalField(
        "Quantidade solicitada",
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=VALIDADOR_QUANTIDADE,
    )

    quantidade_preparada = models.DecimalField(
        "Quantidade preparada",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=VALIDADOR_QUANTIDADE,
    )

    quantidade_entregue = models.DecimalField(
        "Quantidade entregue",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=VALIDADOR_QUANTIDADE,
    )

    quantidade_recebida = models.DecimalField(
        "Quantidade recebida",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=VALIDADOR_QUANTIDADE,
    )

    quantidade_consumida = models.DecimalField(
        "Quantidade consumida",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=VALIDADOR_QUANTIDADE,
    )

    observacao_enfermagem = models.CharField(
        "Observação da Enfermagem",
        max_length=250,
        blank=True,
    )

    observacao_cozinha = models.CharField(
        "Observação da Cozinha",
        max_length=250,
        blank=True,
    )

    observacao_confirmacao = models.CharField(
        "Observação da confirmação",
        max_length=250,
        blank=True,
    )

    class Meta:
        verbose_name = "Produto do pedido"
        verbose_name_plural = "Produtos do pedido"
        ordering = ["produto__ordem", "produto__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "produto"],
                name="coz_linha_produto_unica",
            ),
        ]

    def __str__(self):
        return f"{self.pedido} — {self.produto.nome}"

    @property
    def tem_divergencia(self):
        return (
            self.quantidade_entregue is not None
            and self.quantidade_recebida is not None
            and self.quantidade_entregue
            != self.quantidade_recebida
        )

    def dados_para_historico(self):
        return {
            "produto_id": self.produto_id,
            "produto": self.produto.nome,
            "solicitada": str(self.quantidade_solicitada),
            "preparada": (
                str(self.quantidade_preparada)
                if self.quantidade_preparada is not None
                else None
            ),
            "entregue": (
                str(self.quantidade_entregue)
                if self.quantidade_entregue is not None
                else None
            ),
            "recebida": (
                str(self.quantidade_recebida)
                if self.quantidade_recebida is not None
                else None
            ),
            "consumida": (
                str(self.quantidade_consumida)
                if self.quantidade_consumida is not None
                else None
            ),
        }


class LinhaRefeicaoPedido(models.Model):
    pedido = models.ForeignKey(
        PedidoCozinha,
        on_delete=models.CASCADE,
        related_name="linhas_refeicoes",
        verbose_name="Pedido",
    )

    tipo_refeicao = models.ForeignKey(
        TipoRefeicao,
        on_delete=models.PROTECT,
        related_name="linhas_pedido",
        verbose_name="Tipo de refeição",
    )

    tipo_dieta = models.ForeignKey(
        TipoDieta,
        on_delete=models.PROTECT,
        related_name="linhas_pedido",
        verbose_name="Tipo de dieta",
    )

    quantidade_solicitada = models.PositiveIntegerField(
        "Quantidade solicitada",
        default=0,
    )

    quantidade_preparada = models.PositiveIntegerField(
        "Quantidade preparada",
        null=True,
        blank=True,
    )

    quantidade_entregue = models.PositiveIntegerField(
        "Quantidade entregue",
        null=True,
        blank=True,
    )

    quantidade_recebida = models.PositiveIntegerField(
        "Quantidade recebida",
        null=True,
        blank=True,
    )

    quantidade_consumida = models.PositiveIntegerField(
        "Quantidade consumida",
        null=True,
        blank=True,
    )

    observacao_enfermagem = models.CharField(
        "Observação da Enfermagem",
        max_length=250,
        blank=True,
    )

    observacao_cozinha = models.CharField(
        "Observação da Cozinha",
        max_length=250,
        blank=True,
    )

    observacao_confirmacao = models.CharField(
        "Observação da confirmação",
        max_length=250,
        blank=True,
    )

    class Meta:
        verbose_name = "Refeição do pedido"
        verbose_name_plural = "Refeições do pedido"
        ordering = [
            "tipo_refeicao__ordem",
            "tipo_dieta__ordem",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "pedido",
                    "tipo_refeicao",
                    "tipo_dieta",
                ],
                name="coz_linha_refeicao_unica",
            ),
        ]

    def __str__(self):
        return (
            f"{self.pedido} — "
            f"{self.tipo_refeicao.nome} — "
            f"{self.tipo_dieta.nome}"
        )

    @property
    def tem_divergencia(self):
        return (
            self.quantidade_entregue is not None
            and self.quantidade_recebida is not None
            and self.quantidade_entregue
            != self.quantidade_recebida
        )

    def dados_para_historico(self):
        return {
            "tipo_refeicao_id": self.tipo_refeicao_id,
            "tipo_refeicao": self.tipo_refeicao.nome,
            "tipo_dieta_id": self.tipo_dieta_id,
            "tipo_dieta": self.tipo_dieta.nome,
            "solicitada": self.quantidade_solicitada,
            "preparada": self.quantidade_preparada,
            "entregue": self.quantidade_entregue,
            "recebida": self.quantidade_recebida,
            "consumida": self.quantidade_consumida,
        }


class HistoricoPedidoCozinha(models.Model):
    pedido = models.ForeignKey(
        PedidoCozinha,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Pedido",
    )

    acao = models.CharField(
        "Ação",
        max_length=25,
        choices=AcaoHistoricoCozinha.choices,
    )

    estado_anterior = models.CharField(
        "Estado anterior",
        max_length=25,
        choices=EstadoPedidoCozinha.choices,
        blank=True,
    )

    estado_novo = models.CharField(
        "Novo estado",
        max_length=25,
        choices=EstadoPedidoCozinha.choices,
        blank=True,
    )

    dados = models.JSONField(
        "Dados do pedido",
        default=dict,
        blank=True,
    )

    observacao = models.TextField(
        "Observação",
        blank=True,
    )

    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historico_pedidos_cozinha",
        verbose_name="Profissional",
    )

    criado_em = models.DateTimeField(
        "Criado em",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Histórico do pedido da Cozinha"
        verbose_name_plural = "Histórico dos pedidos da Cozinha"
        ordering = ["-criado_em", "-pk"]
        indexes = [
            models.Index(
                fields=["pedido", "criado_em"],
                name="coz_hist_pedido_data",
            ),
        ]

    def __str__(self):
        return (
            f"{self.pedido} — "
            f"{self.get_acao_display()}"
        )
