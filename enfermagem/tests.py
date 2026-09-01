from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clinica.models import (
    AreaClinica,
    VisibilidadeRegistoClinico,
)
from visitas.models import Utente

from .models import (
    AREA_CLINICA_ENFERMAGEM,
    AcompanhamentoQueda,
    AcaoHistoricoClinico,
    AtividadeQueda,
    DispositivoAuxilio,
    EstadoGradesLaterais,
    EstadoMedidasPreventivas,
    EstadoNotificacaoFamiliar,
    EstadoNotificacaoInstitucional,
    EstadoReavaliacaoMorse,
    GravidadeQueda,
    HistoricoRegistoEnfermagem,
    IntervencaoQueda,
    LesaoIdentificada,
    LocalQueda,
    OpcaoSimNao,
    RegistoEnfermagem,
    RegistoQueda,
    TipoQueda,
    TipoRegistoEnfermagem,
    TurnoEnfermagem,
)


User = get_user_model()


class PermissoesRegistosEnfermagemTests(TestCase):
    def setUp(self):
        self.grupo_enfermagem = (
            Group.objects.get_or_create(
                name="UCCI_Enfermagem",
            )[0]
        )

        self.grupo_medicos = (
            Group.objects.get_or_create(
                name="UCCI_Medicos",
            )[0]
        )

        self.area, _ = AreaClinica.objects.get_or_create(
            codigo=AREA_CLINICA_ENFERMAGEM,
            defaults={
                "nome": "Enfermagem",
                "descricao": "Registos de Enfermagem",
                "ativa": True,
            },
        )

        self.area.grupos_responsaveis.set([
            self.grupo_enfermagem,
        ])

        self.area.grupos_partilha_geral.set([
            self.grupo_enfermagem,
            self.grupo_medicos,
        ])

        self.enfermeiro = User.objects.create_user(
            username="enfermeiro_teste",
            password="teste",
            first_name="Enfermeiro",
            last_name="Autor",
        )
        self.enfermeiro.groups.add(
            self.grupo_enfermagem,
        )

        self.outro_enfermeiro = User.objects.create_user(
            username="outro_enfermeiro",
            password="teste",
            first_name="Outro",
            last_name="Enfermeiro",
        )
        self.outro_enfermeiro.groups.add(
            self.grupo_enfermagem,
        )

        self.medico = User.objects.create_user(
            username="medico_teste",
            password="teste",
            first_name="Médico",
            last_name="Teste",
        )
        self.medico.groups.add(
            self.grupo_medicos,
        )

        self.superutilizador = (
            User.objects.create_superuser(
                username="administrador_teste",
                password="teste",
                email="admin@example.com",
            )
        )

        self.utente = Utente.objects.create(
            nome="Utente de Teste",
            numero_processo="ENF-TESTE-001",
            data_entrada=timezone.localdate(),
        )

        self.outro_utente = Utente.objects.create(
            nome="Outro Utente",
            numero_processo="ENF-TESTE-002",
            data_entrada=timezone.localdate(),
        )

        self.tipo_registo, _ = (
            TipoRegistoEnfermagem.objects.get_or_create(
                codigo="observacao-teste",
                defaults={
                    "nome": "Observação de teste",
                    "ativo": True,
                    "ordem": 100,
                },
            )
        )

    def criar_registo(
        self,
        profissional=None,
        utente=None,
        visibilidade=VisibilidadeRegistoClinico.TODOS,
        observacao="Registo clínico de teste",
    ):
        return RegistoEnfermagem.objects.create(
            utente=utente or self.utente,
            data_registo=timezone.now(),
            turno=TurnoEnfermagem.MANHA,
            tipo_registo=self.tipo_registo,
            observacao=observacao,
            cuidados_realizados="Cuidados realizados.",
            resposta_utente="Resposta do utente.",
            plano_cuidados="Plano seguinte.",
            visibilidade=visibilidade,
            profissional=(
                profissional or self.enfermeiro
            ),
        )

    def criar_queda(
        self,
        profissional=None,
        utente=None,
        visibilidade=VisibilidadeRegistoClinico.TODOS,
    ):
        registo = self.criar_registo(
            profissional=profissional,
            utente=utente,
            visibilidade=visibilidade,
            observacao="Notificação de queda.",
        )

        return RegistoQueda.objects.create(
            registo_enfermagem=registo,
            data_hora_queda=timezone.now(),
            local_queda=LocalQueda.QUARTO_CAMA,
            tipo_queda=TipoQueda.ACIDENTAL,
            gravidade=GravidadeQueda.SEM_LESAO,
            lesoes_identificadas=[
                LesaoIdentificada.NENHUMA,
            ],
            doente_estava=AcompanhamentoQueda.SOZINHO,
            atividade_no_momento=(
                AtividadeQueda.DEAMBULACAO
            ),
            grades_laterais=(
                EstadoGradesLaterais.NAO_APLICAVEL
            ),
            dispositivo_auxilio=(
                DispositivoAuxilio.NENHUM
            ),
            morse_aplicada=OpcaoSimNao.NAO,
            medidas_preventivas_implementadas=(
                EstadoMedidasPreventivas.NAO
            ),
            intervencoes_realizadas=[
                IntervencaoQueda.AVALIACAO_CLINICA,
            ],
            medico_notificado=OpcaoSimNao.NAO,
            familiar_notificado=(
                EstadoNotificacaoFamiliar.NAO_APLICAVEL
            ),
            descricao_ocorrencia=(
                "Descrição da ocorrência de teste."
            ),
            reavaliacao_morse_estado=(
                EstadoReavaliacaoMorse.PENDENTE
            ),
            notificacao_institucional_estado=(
                EstadoNotificacaoInstitucional.PENDENTE
            ),
        )

    def test_enfermeiro_consegue_criar_registo(self):
        self.client.force_login(self.enfermeiro)

        data_registo = (
            timezone.localtime()
            .replace(second=0, microsecond=0)
            .strftime("%Y-%m-%dT%H:%M")
        )

        resposta = self.client.post(
            reverse(
                "enfermagem:criar_registo",
                args=[self.utente.pk],
            ),
            {
                "data_registo": data_registo,
                "turno": TurnoEnfermagem.MANHA,
                "tipo_registo": self.tipo_registo.pk,
                "observacao": "Utente estável.",
                "cuidados_realizados": "Vigilância.",
                "resposta_utente": "Sem alterações.",
                "plano_cuidados": "Manter vigilância.",
                "visibilidade": (
                    VisibilidadeRegistoClinico.TODOS
                ),
            },
        )

        self.assertEqual(resposta.status_code, 302)

        registo = RegistoEnfermagem.objects.get(
            observacao="Utente estável.",
        )

        self.assertEqual(
            registo.profissional,
            self.enfermeiro,
        )

        self.assertTrue(
            HistoricoRegistoEnfermagem.objects.filter(
                registo=registo,
                acao=AcaoHistoricoClinico.CRIADO,
                profissional=self.enfermeiro,
            ).exists()
        )

    def test_enfermeiro_ve_registos_de_grupo_e_gerais(self):
        registo_geral = self.criar_registo(
            observacao="REGISTO GERAL",
        )

        registo_grupo = self.criar_registo(
            visibilidade=(
                VisibilidadeRegistoClinico.GRUPO
            ),
            observacao="REGISTO DO GRUPO",
        )

        registo_confidencial = self.criar_registo(
            visibilidade=(
                VisibilidadeRegistoClinico.CONFIDENCIAL
            ),
            observacao="REGISTO CONFIDENCIAL",
        )

        self.client.force_login(
            self.outro_enfermeiro,
        )

        resposta = self.client.get(
            reverse(
                "enfermagem:registos_utente",
                args=[self.utente.pk],
            )
        )

        self.assertEqual(resposta.status_code, 200)

        registos = list(
            resposta.context["registos"]
        )

        self.assertIn(registo_geral, registos)
        self.assertIn(registo_grupo, registos)
        self.assertNotIn(
            registo_confidencial,
            registos,
        )

    def test_medico_ve_apenas_registo_geral(self):
        registo_geral = self.criar_registo(
            observacao="PARTILHADO COM MÉDICOS",
        )

        registo_grupo = self.criar_registo(
            visibilidade=(
                VisibilidadeRegistoClinico.GRUPO
            ),
            observacao="APENAS ENFERMAGEM",
        )

        registo_confidencial = self.criar_registo(
            visibilidade=(
                VisibilidadeRegistoClinico.CONFIDENCIAL
            ),
            observacao="APENAS AUTOR",
        )

        self.client.force_login(self.medico)

        resposta = self.client.get(
            reverse(
                "enfermagem:registos_utente",
                args=[self.utente.pk],
            )
        )

        self.assertEqual(resposta.status_code, 200)

        registos = list(
            resposta.context["registos"]
        )

        self.assertIn(registo_geral, registos)
        self.assertNotIn(registo_grupo, registos)
        self.assertNotIn(
            registo_confidencial,
            registos,
        )

    def test_apenas_autor_pode_editar(self):
        registo = self.criar_registo()

        self.client.force_login(
            self.outro_enfermeiro,
        )

        resposta = self.client.get(
            reverse(
                "enfermagem:editar_registo",
                args=[registo.pk],
            )
        )

        self.assertEqual(resposta.status_code, 403)

        self.client.force_login(self.enfermeiro)

        resposta = self.client.get(
            reverse(
                "enfermagem:editar_registo",
                args=[registo.pk],
            )
        )

        self.assertEqual(resposta.status_code, 200)

    def test_alta_impede_novo_registo(self):
        self.utente.data_saida = (
            timezone.localdate()
        )
        self.utente.save(
            update_fields=["data_saida"]
        )

        self.client.force_login(self.enfermeiro)

        resposta = self.client.get(
            reverse(
                "enfermagem:criar_registo",
                args=[self.utente.pk],
            )
        )

        self.assertEqual(resposta.status_code, 403)

    def test_superutilizador_sem_grupo_nao_tem_acesso(self):
        self.client.force_login(
            self.superutilizador,
        )

        resposta = self.client.get(
            reverse(
                "enfermagem:registos_utente",
                args=[self.utente.pk],
            )
        )

        self.assertEqual(resposta.status_code, 403)

    def test_lista_quedas_respeita_confidencialidade(self):
        queda_geral = self.criar_queda(
            utente=self.utente,
        )

        queda_confidencial = self.criar_queda(
            utente=self.outro_utente,
            visibilidade=(
                VisibilidadeRegistoClinico.CONFIDENCIAL
            ),
        )

        self.client.force_login(self.medico)

        resposta = self.client.get(
            reverse(
                "enfermagem:lista_quedas",
            )
        )

        self.assertEqual(resposta.status_code, 200)

        quedas = list(
            resposta.context["quedas"]
        )

        self.assertIn(queda_geral, quedas)
        self.assertNotIn(
            queda_confidencial,
            quedas,
        )

    def test_autor_consegue_consultar_queda(self):
        queda = self.criar_queda(
            visibilidade=(
                VisibilidadeRegistoClinico.CONFIDENCIAL
            ),
        )

        self.client.force_login(self.enfermeiro)

        resposta = self.client.get(
            reverse(
                "enfermagem:detalhe_queda",
                args=[queda.pk],
            )
        )

        self.assertEqual(resposta.status_code, 200)