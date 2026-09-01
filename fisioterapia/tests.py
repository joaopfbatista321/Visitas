from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config.permissoes_clinicas import (
    VisibilidadeRegisto,
)
from visitas.models import (
    Piso,
    Quarto,
    Utente,
)

from .models import (
    CategoriaIntervencaoFisioterapia,
    EstadoParticipacaoFisioterapia,
    EstadoSessaoFisioterapia,
    HistoricoParticipacaoFisioterapia,
    LocalSessaoFisioterapia,
    ParticipacaoFisioterapia,
    RegistoFisioterapia,
    SessaoFisioterapia,
    TipoIntervencaoFisioterapia,
    TipoSessaoFisioterapia,
)
from .services import alterar_estado_participacao


User = get_user_model()


class FisioterapiaBaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.grupo_fisioterapia = Group.objects.create(
            name="UCCI_Fisioterapia"
        )

        cls.grupo_enfermagem = Group.objects.create(
            name="UCCI_Enfermagem"
        )

        cls.grupo_rececao = Group.objects.create(
            name="UCCI_Rececao"
        )

        cls.fisioterapeuta_a = User.objects.create_user(
            username="fisio_a",
            password="teste",
            first_name="Ana",
            last_name="Costa",
        )

        cls.fisioterapeuta_a.groups.add(
            cls.grupo_fisioterapia
        )

        cls.fisioterapeuta_b = User.objects.create_user(
            username="fisio_b",
            password="teste",
            first_name="Bruno",
            last_name="Silva",
        )

        cls.fisioterapeuta_b.groups.add(
            cls.grupo_fisioterapia
        )

        cls.enfermeiro = User.objects.create_user(
            username="enfermeiro",
            password="teste",
            first_name="Carlos",
            last_name="Enfermeiro",
        )

        cls.enfermeiro.groups.add(
            cls.grupo_enfermagem
        )

        cls.rececionista = User.objects.create_user(
            username="rececao",
            password="teste",
            first_name="Rita",
            last_name="Receção",
        )

        cls.rececionista.groups.add(
            cls.grupo_rececao
        )

        cls.tipo_intervencao = (
            TipoIntervencaoFisioterapia.objects.create(
                categoria=(
                    CategoriaIntervencaoFisioterapia
                    .TREINO_FUNCIONAL
                ),
                nome="Treino funcional de teste",
                descricao="Intervenção utilizada nos testes.",
                ativo=True,
                ordem=1,
            )
        )

        cls.utente = Utente.objects.create(
            nome="Utente de Teste",
            numero_processo="TESTE-FISIO-001",
            data_entrada=timezone.localdate(),
        )

    def criar_sessao(
        self,
        tipo=TipoSessaoFisioterapia.INDIVIDUAL,
        profissional=None,
        criado_por=None,
        inicio=None,
        local_realizacao=(
            LocalSessaoFisioterapia.SALA_REABILITACAO
        ),
    ):
        profissional = (
            profissional
            or self.fisioterapeuta_a
        )

        criado_por = criado_por or profissional

        inicio = (
            inicio
            or timezone.now() + timedelta(days=3)
        )

        sessao = SessaoFisioterapia.objects.create(
            tipo=tipo,
            inicio=inicio,
            fim=inicio + timedelta(hours=1),
            local_realizacao=local_realizacao,
            profissional=profissional,
            criado_por=criado_por,
        )

        sessao.tipos_intervencao.add(
            self.tipo_intervencao
        )

        return sessao


class CancelamentoAltaFisioterapiaTests(
    FisioterapiaBaseTests
):
    def test_alta_cancela_marcacao_individual_futura(
        self,
    ):
        sessao = self.criar_sessao()

        participacao = (
            ParticipacaoFisioterapia.objects.create(
                sessao=sessao,
                utente=self.utente,
            )
        )

        self.utente.data_saida = timezone.localdate()

        self.utente.save(
            update_fields=["data_saida"]
        )

        participacao.refresh_from_db()
        sessao.refresh_from_db()

        self.assertEqual(
            participacao.estado,
            EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
        )

        self.assertEqual(
            sessao.estado,
            EstadoSessaoFisioterapia.CANCELADA,
        )

        self.assertTrue(
            HistoricoParticipacaoFisioterapia.objects
            .filter(
                participacao=participacao,
                estado_novo=(
                    EstadoParticipacaoFisioterapia
                    .CANCELADO_ALTA
                ),
            )
            .exists()
        )

    def test_alta_nao_cancela_restantes_utentes_do_grupo(
        self,
    ):
        outro_utente = Utente.objects.create(
            nome="Outro Utente",
            numero_processo="TESTE-FISIO-002",
            data_entrada=timezone.localdate(),
        )

        sessao = self.criar_sessao(
            tipo=TipoSessaoFisioterapia.GRUPO,
        )

        participacao_alta = (
            ParticipacaoFisioterapia.objects.create(
                sessao=sessao,
                utente=self.utente,
            )
        )

        participacao_ativa = (
            ParticipacaoFisioterapia.objects.create(
                sessao=sessao,
                utente=outro_utente,
            )
        )

        self.utente.data_saida = timezone.localdate()

        self.utente.save(
            update_fields=["data_saida"]
        )

        participacao_alta.refresh_from_db()
        participacao_ativa.refresh_from_db()
        sessao.refresh_from_db()

        self.assertEqual(
            participacao_alta.estado,
            EstadoParticipacaoFisioterapia.CANCELADO_ALTA,
        )

        self.assertEqual(
            participacao_ativa.estado,
            EstadoParticipacaoFisioterapia.AGENDADO,
        )

        self.assertEqual(
            sessao.estado,
            EstadoSessaoFisioterapia.AGENDADA,
        )


class AtribuicaoProfissionalTests(
    FisioterapiaBaseTests
):
    def test_criador_pode_atribuir_outro_profissional(
        self,
    ):
        self.client.force_login(
            self.fisioterapeuta_a
        )

        inicio = timezone.localtime(
            timezone.now() + timedelta(days=2)
        ).replace(
            second=0,
            microsecond=0,
        )

        fim = inicio + timedelta(hours=1)

        resposta = self.client.post(
            reverse(
                "fisioterapia:criar_sessao"
            ),
            {
                "profissional": (
                    self.fisioterapeuta_b.pk
                ),
                "tipo": (
                    TipoSessaoFisioterapia.INDIVIDUAL
                ),
                "tipos_intervencao": [
                    self.tipo_intervencao.pk
                ],
                "utentes": [self.utente.pk],
                "inicio": inicio.strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "fim": fim.strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "local_realizacao": (
                    LocalSessaoFisioterapia
                    .SALA_REABILITACAO
                ),
                "local": "",
                "trabalho_planeado": (
                    "Treino funcional."
                ),
                "observacoes": "",
            },
        )

        self.assertEqual(
            resposta.status_code,
            302,
        )

        sessao = (
            SessaoFisioterapia.objects.get()
        )

        self.assertEqual(
            sessao.criado_por,
            self.fisioterapeuta_a,
        )

        self.assertEqual(
            sessao.profissional,
            self.fisioterapeuta_b,
        )

        self.assertTrue(
            sessao.tipos_intervencao.filter(
                pk=self.tipo_intervencao.pk
            ).exists()
        )

        self.assertTrue(
            sessao.participacoes.filter(
                utente=self.utente
            ).exists()
        )

        self.assertIn(
            self.utente.nome,
            sessao.titulo,
        )

        self.assertIn(
            self.tipo_intervencao.nome,
            sessao.titulo,
        )

        self.assertIn(
            "Bruno Silva",
            sessao.titulo_calendario,
        )

    def test_apenas_responsavel_pode_editar_sessao(
        self,
    ):
        sessao = self.criar_sessao(
            profissional=self.fisioterapeuta_b,
            criado_por=self.fisioterapeuta_a,
        )

        ParticipacaoFisioterapia.objects.create(
            sessao=sessao,
            utente=self.utente,
        )

        self.assertFalse(
            sessao.pode_editar(
                self.fisioterapeuta_a
            )
        )

        self.assertTrue(
            sessao.pode_editar(
                self.fisioterapeuta_b
            )
        )

        self.client.force_login(
            self.fisioterapeuta_a
        )

        resposta_criador = self.client.get(
            reverse(
                "fisioterapia:editar_sessao",
                args=[sessao.pk],
            )
        )

        self.assertEqual(
            resposta_criador.status_code,
            403,
        )

        self.client.force_login(
            self.fisioterapeuta_b
        )

        resposta_responsavel = self.client.get(
            reverse(
                "fisioterapia:editar_sessao",
                args=[sessao.pk],
            )
        )

        self.assertEqual(
            resposta_responsavel.status_code,
            200,
        )


class EstadoSessaoFisioterapiaTests(
    FisioterapiaBaseTests
):
    def test_sessao_realizada_quando_todos_sao_validados(
        self,
    ):
        outro_utente = Utente.objects.create(
            nome="Segundo Utente",
            numero_processo="TESTE-FISIO-003",
            data_entrada=timezone.localdate(),
        )

        sessao = self.criar_sessao(
            tipo=TipoSessaoFisioterapia.GRUPO,
            inicio=timezone.now() - timedelta(hours=2),
        )

        primeira = (
            ParticipacaoFisioterapia.objects.create(
                sessao=sessao,
                utente=self.utente,
            )
        )

        segunda = (
            ParticipacaoFisioterapia.objects.create(
                sessao=sessao,
                utente=outro_utente,
            )
        )

        alterar_estado_participacao(
            participacao=primeira,
            novo_estado=(
                EstadoParticipacaoFisioterapia.REALIZADO
            ),
            utilizador=self.fisioterapeuta_a,
        )

        sessao.refresh_from_db()

        self.assertEqual(
            sessao.estado,
            EstadoSessaoFisioterapia.AGENDADA,
        )

        alterar_estado_participacao(
            participacao=segunda,
            novo_estado=(
                EstadoParticipacaoFisioterapia.FALTOU
            ),
            utilizador=self.fisioterapeuta_a,
        )

        sessao.refresh_from_db()

        self.assertEqual(
            sessao.estado,
            EstadoSessaoFisioterapia.REALIZADA,
        )

        self.assertTrue(
            primeira.historico.filter(
                estado_novo=(
                    EstadoParticipacaoFisioterapia.REALIZADO
                )
            ).exists()
        )

        self.assertTrue(
            segunda.historico.filter(
                estado_novo=(
                    EstadoParticipacaoFisioterapia.FALTOU
                )
            ).exists()
        )

    def test_marcar_todos_como_realizados(
        self,
    ):
        outro_utente = Utente.objects.create(
            nome="Utente do Grupo",
            numero_processo="TESTE-FISIO-004",
            data_entrada=timezone.localdate(),
        )

        sessao = self.criar_sessao(
            tipo=TipoSessaoFisioterapia.GRUPO,
            inicio=timezone.now() - timedelta(hours=2),
        )

        ParticipacaoFisioterapia.objects.create(
            sessao=sessao,
            utente=self.utente,
        )

        ParticipacaoFisioterapia.objects.create(
            sessao=sessao,
            utente=outro_utente,
        )

        self.client.force_login(
            self.fisioterapeuta_a
        )

        resposta = self.client.post(
            reverse(
                "fisioterapia:marcar_todos_realizados",
                args=[sessao.pk],
            )
        )

        self.assertEqual(
            resposta.status_code,
            302,
        )

        sessao.refresh_from_db()

        self.assertEqual(
            sessao.estado,
            EstadoSessaoFisioterapia.REALIZADA,
        )

        self.assertEqual(
            sessao.estado_atualizado_por,
            self.fisioterapeuta_a,
        )

        self.assertIsNotNone(
            sessao.estado_atualizado_em
        )

        self.assertFalse(
            sessao.participacoes.exclude(
                estado=(
                    EstadoParticipacaoFisioterapia.REALIZADO
                )
            ).exists()
        )


class LocalSessaoFisioterapiaTests(
    FisioterapiaBaseTests
):
    def test_outro_local_exige_especificacao(
        self,
    ):
        inicio = (
            timezone.now() + timedelta(days=1)
        )

        sessao = SessaoFisioterapia(
            tipo=TipoSessaoFisioterapia.INDIVIDUAL,
            inicio=inicio,
            fim=inicio + timedelta(hours=1),
            local_realizacao=(
                LocalSessaoFisioterapia.OUTRO
            ),
            local="",
            profissional=self.fisioterapeuta_a,
            criado_por=self.fisioterapeuta_a,
        )

        with self.assertRaises(
            ValidationError
        ) as contexto:
            sessao.full_clean()

        self.assertIn(
            "local",
            contexto.exception.message_dict,
        )

    def test_sessao_pode_ser_realizada_no_leito(
        self,
    ):
        inicio = (
            timezone.now() + timedelta(days=1)
        )

        sessao = SessaoFisioterapia(
            tipo=TipoSessaoFisioterapia.INDIVIDUAL,
            inicio=inicio,
            fim=inicio + timedelta(hours=1),
            local_realizacao=(
                LocalSessaoFisioterapia.LEITO
            ),
            local="Quarto 12, cama A",
            profissional=self.fisioterapeuta_a,
            criado_por=self.fisioterapeuta_a,
        )

        sessao.full_clean()
        sessao.save()

        self.assertEqual(
            sessao.local_exibicao,
            (
                "Leito/quarto do utente — "
                "Quarto 12, cama A"
            ),
        )


class VisibilidadeRegistosTests(
    FisioterapiaBaseTests
):
    def criar_registo(self, visibilidade):
        registo = RegistoFisioterapia.objects.create(
            utente=self.utente,
            data_registo=timezone.now(),
            trabalho_realizado=(
                "Trabalho de fisioterapia realizado."
            ),
            visibilidade=visibilidade,
            profissional=self.fisioterapeuta_a,
        )

        registo.tipos_intervencao.add(
            self.tipo_intervencao
        )

        return registo

    def test_visibilidade_confidencial(
        self,
    ):
        registo = self.criar_registo(
            VisibilidadeRegisto.CONFIDENCIAL
        )

        self.assertTrue(
            registo.pode_ver(
                self.fisioterapeuta_a
            )
        )

        self.assertFalse(
            registo.pode_ver(
                self.fisioterapeuta_b
            )
        )

        self.assertFalse(
            registo.pode_ver(
                self.enfermeiro
            )
        )

    def test_visibilidade_grupo_profissional(
        self,
    ):
        registo = self.criar_registo(
            VisibilidadeRegisto.GRUPO
        )

        self.assertTrue(
            registo.pode_ver(
                self.fisioterapeuta_b
            )
        )

        self.assertFalse(
            registo.pode_ver(
                self.enfermeiro
            )
        )

        self.assertFalse(
            registo.pode_editar(
                self.fisioterapeuta_b
            )
        )

        self.assertTrue(
            registo.pode_editar(
                self.fisioterapeuta_a
            )
        )

    def test_visibilidade_todos_grupos_clinicos(
        self,
    ):
        registo = self.criar_registo(
            VisibilidadeRegisto.TODOS
        )

        self.enfermeiro.groups.add(
            self.grupo_rececao
        )

        self.assertTrue(
            registo.pode_ver(
                self.enfermeiro
            )
        )

        self.assertFalse(
            registo.pode_ver(
                self.rececionista
            )
        )

        self.client.force_login(
            self.enfermeiro
        )

        resposta_permitida = self.client.get(
            reverse(
                "fisioterapia:detalhe_registo",
                args=[registo.pk],
            )
        )

        self.assertEqual(
            resposta_permitida.status_code,
            200,
        )

        registo_grupo = self.criar_registo(
            VisibilidadeRegisto.GRUPO
        )

        resposta_negada = self.client.get(
            reverse(
                "fisioterapia:detalhe_registo",
                args=[registo_grupo.pk],
            )
        )

        self.assertEqual(
            resposta_negada.status_code,
            403,
        )


class FiltroPisoFisioterapiaTests(
    FisioterapiaBaseTests
):
    def test_lista_e_calendario_filtram_por_piso(
        self,
    ):
        quarto_piso_1 = Quarto.objects.create(
            codigo="101",
            piso=Piso.P1,
        )

        quarto_piso_2 = Quarto.objects.create(
            codigo="201",
            piso=Piso.P2,
        )

        utente_piso_1 = Utente.objects.create(
            nome="Utente Piso Um",
            numero_processo="TESTE-PISO-001",
            quarto=quarto_piso_1,
            data_entrada=timezone.localdate(),
        )

        utente_piso_2 = Utente.objects.create(
            nome="Utente Piso Dois",
            numero_processo="TESTE-PISO-002",
            quarto=quarto_piso_2,
            data_entrada=timezone.localdate(),
        )

        sessao_piso_1 = self.criar_sessao(
            inicio=timezone.now() + timedelta(days=4),
        )

        sessao_piso_2 = self.criar_sessao(
            inicio=timezone.now() + timedelta(days=5),
        )

        ParticipacaoFisioterapia.objects.create(
            sessao=sessao_piso_1,
            utente=utente_piso_1,
        )

        ParticipacaoFisioterapia.objects.create(
            sessao=sessao_piso_2,
            utente=utente_piso_2,
        )

        self.client.force_login(
            self.fisioterapeuta_a
        )

        resposta_lista = self.client.get(
            reverse(
                "fisioterapia:lista_sessoes"
            ),
            {
                "piso": Piso.P1,
            },
        )

        self.assertEqual(
            resposta_lista.status_code,
            200,
        )

        ids_lista = {
            sessao.pk
            for sessao
            in resposta_lista.context["sessoes"]
        }

        self.assertIn(
            sessao_piso_1.pk,
            ids_lista,
        )

        self.assertNotIn(
            sessao_piso_2.pk,
            ids_lista,
        )

        resposta_calendario = self.client.get(
            reverse(
                "fisioterapia:eventos"
            ),
            {
                "piso": Piso.P2,
            },
        )

        self.assertEqual(
            resposta_calendario.status_code,
            200,
        )

        eventos = resposta_calendario.json()

        self.assertEqual(
            len(eventos),
            1,
        )

        self.assertEqual(
            eventos[0]["id"],
            sessao_piso_2.pk,
        )

        self.assertIn(
            "2.º Piso",
            eventos[0]["extendedProps"][
                "localizacoes_utentes"
            ][0],
        )