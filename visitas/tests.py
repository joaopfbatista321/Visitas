from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clinica.models import AreaClinica
from enfermagem.models import (
    AREA_CLINICA_ENFERMAGEM,
    AusenciaUtente,
    EstadoAusenciaUtente,
    TipoAusenciaUtente,
)

from .models import Mensalidade, MovimentoFinanceiro, Piso, Quarto, Utente
from .servicos_mensalidades import (
    calcular_valores_mensalidade,
    gerar_mensalidades,
    registar_pagamento_mensalidade,
)
from .servicos_ocupacao import calcular_mapa_ocupacao


def momento(ano, mes, dia, hora=12):
    return timezone.make_aware(datetime(ano, mes, dia, hora, 0))


class MensalidadesTestCase(TestCase):
    def setUp(self):
        self.utilizador = get_user_model().objects.create_user(
            username="rececao",
            password="teste",
        )
        self.utilizador.groups.add(
            Group.objects.create(name="UCCI_Rececao")
        )
        self.quarto = Quarto.objects.create(
            codigo="101",
            piso=Piso.P1,
            capacidade=2,
        )
        self.utente = Utente.objects.create(
            nome="Utente Teste",
            numero_processo="PROC-1",
            quarto=self.quarto,
            data_entrada=date(2026, 9, 10),
            data_saida=date(2026, 9, 25),
            valor_dia=Decimal("20.00"),
            paga_dias_ausencia=False,
        )

    def criar_ausencia(self):
        return AusenciaUtente.objects.create(
            utente=self.utente,
            tipo=TipoAusenciaUtente.OUTRA,
            data_hora_inicio=momento(2026, 9, 15),
            data_hora_regresso=momento(2026, 9, 18),
            estado=EstadoAusenciaUtente.TERMINADA,
            motivo="Teste",
            criado_por=self.utilizador,
        )

    def test_entrada_conta_saida_nao_conta_e_ausencia_desconta(self):
        self.criar_ausencia()

        valores = calcular_valores_mensalidade(self.utente, 2026, 9)

        self.assertEqual(valores["dias_estadia"], 15)
        self.assertEqual(valores["dias_ausencia"], 3)
        self.assertEqual(valores["dias_faturaveis"], 12)
        self.assertEqual(valores["valor_total"], Decimal("240.00"))

    def test_ausencia_e_cobrada_quando_utente_assim_configurado(self):
        self.criar_ausencia()
        self.utente.paga_dias_ausencia = True
        self.utente.save(update_fields=["paga_dias_ausencia"])

        valores = calcular_valores_mensalidade(self.utente, 2026, 9)

        self.assertEqual(valores["dias_ausencia"], 0)
        self.assertEqual(valores["dias_faturaveis"], 15)
        self.assertEqual(valores["valor_total"], Decimal("300.00"))

    def test_pagamento_guarda_utilizador_e_data(self):
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )

        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("300.00"),
            date(2026, 9, 30),
            self.utilizador,
            observacoes="Transferência recebida",
        )
        mensalidade.refresh_from_db()

        self.assertTrue(mensalidade.pago)
        self.assertIsNotNone(mensalidade.pago_em)
        self.assertEqual(mensalidade.confirmado_por, self.utilizador)
        self.assertEqual(mensalidade.pagamentos.count(), 1)

    def test_pagamentos_parciais_ficam_registados(self):
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )

        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("100.00"),
            date(2026, 9, 20),
            self.utilizador,
            observacoes="Primeira prestação",
        )
        mensalidade.refresh_from_db()
        self.assertFalse(mensalidade.pago)
        self.assertEqual(mensalidade.valor_pago, Decimal("100.00"))
        self.assertEqual(mensalidade.valor_em_falta, Decimal("200.00"))

        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("200.00"),
            date(2026, 9, 30),
            self.utilizador,
            observacoes="Liquidação",
        )
        mensalidade.refresh_from_db()
        self.assertTrue(mensalidade.pago)
        self.assertEqual(mensalidade.valor_em_falta, Decimal("0.00"))
        self.assertEqual(mensalidade.pagamentos.count(), 2)

    def test_recepcao_regista_pagamento_parcial_na_pagina(self):
        self.client.force_login(self.utilizador)
        lista_url = reverse("visitas:mensalidades_utentes")

        resposta = self.client.get(
            lista_url,
            {"ano": 2026, "mes": 9},
        )
        self.assertEqual(resposta.status_code, 200)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )

        resposta = self.client.post(
            reverse(
                "visitas:validar_pagamento_mensalidade",
                args=[mensalidade.pk],
            ),
            {
                "valor": "100.00",
                "data_pagamento": "2026-09-20",
                "observacoes": "Primeira prestação",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        mensalidade.refresh_from_db()
        self.assertEqual(mensalidade.pagamentos.count(), 1)
        self.assertEqual(mensalidade.valor_pago, Decimal("100.00"))
        self.assertFalse(mensalidade.pago)

    def test_saida_posterior_reabre_mensalidade_paga(self):
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )
        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("300.00"),
            date(2026, 9, 30),
            self.utilizador,
        )

        self.utente.data_saida = date(2026, 9, 20)
        self.utente.save(update_fields=["data_saida"])
        resultado = gerar_mensalidades(2026, 9)
        mensalidade.refresh_from_db()

        self.assertEqual(resultado["reabertas"], 1)
        self.assertTrue(mensalidade.pago)
        self.assertTrue(mensalidade.necessita_revisao)
        self.assertEqual(mensalidade.dias_faturaveis, 10)
        self.assertEqual(mensalidade.valor_excedente, Decimal("100.00"))

    def test_pagamento_mensalidade_nao_altera_saldo_pessoal(self):
        self.utente.saldo = Decimal("75.00")
        self.utente.save(update_fields=["saldo"])
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )

        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("100.00"),
            date(2026, 9, 20),
            self.utilizador,
        )

        self.utente.refresh_from_db()
        self.assertEqual(self.utente.saldo, Decimal("75.00"))
        self.assertEqual(self.utente.movimentos.count(), 0)

    def test_movimento_pessoal_nao_altera_mensalidade(self):
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )
        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("100.00"),
            date(2026, 9, 20),
            self.utilizador,
        )

        MovimentoFinanceiro.objects.create(
            utente=self.utente,
            tipo=MovimentoFinanceiro.ENTRADA,
            valor=Decimal("25.00"),
            descricao="Dinheiro entregue ao utente",
            registado_por=self.utilizador,
        )

        self.utente.refresh_from_db()
        mensalidade.refresh_from_db()
        self.assertEqual(self.utente.saldo, Decimal("25.00"))
        self.assertEqual(mensalidade.valor_total, Decimal("300.00"))
        self.assertEqual(mensalidade.valor_pago, Decimal("100.00"))
        self.assertFalse(mensalidade.pago)
        self.assertEqual(mensalidade.pagamentos.count(), 1)

    def test_paginas_da_conta_e_mensalidade_estao_separadas(self):
        self.client.force_login(self.utilizador)

        resposta_conta = self.client.get(
            reverse("visitas:financeiro_utente", args=[self.utente.pk])
        )
        self.assertEqual(resposta_conta.status_code, 200)
        self.assertContains(resposta_conta, "Conta pessoal do utente")
        self.assertNotContains(resposta_conta, "Configuração da mensalidade")

        resposta_mensalidade = self.client.get(
            reverse(
                "visitas:configuracao_mensalidade_utente",
                args=[self.utente.pk],
            )
        )
        self.assertEqual(resposta_mensalidade.status_code, 200)
        self.assertContains(resposta_mensalidade, "Configuração da mensalidade")
        self.assertNotContains(resposta_mensalidade, "Saldo da conta pessoal")

    def test_caucao_nao_altera_saldo_nem_mensalidade(self):
        self.utente.valor_caucao = Decimal("500.00")
        self.utente.save(update_fields=["valor_caucao"])
        gerar_mensalidades(2026, 9)
        mensalidade = Mensalidade.objects.get(
            utente=self.utente,
            ano=2026,
            mes=9,
        )

        registar_pagamento_mensalidade(
            mensalidade,
            Decimal("100.00"),
            date(2026, 9, 20),
            self.utilizador,
        )
        MovimentoFinanceiro.objects.create(
            utente=self.utente,
            tipo=MovimentoFinanceiro.ENTRADA,
            valor=Decimal("25.00"),
            descricao="Dinheiro pessoal",
            registado_por=self.utilizador,
        )

        self.utente.refresh_from_db()
        mensalidade.refresh_from_db()
        self.assertEqual(self.utente.valor_caucao, Decimal("500.00"))
        self.assertEqual(self.utente.saldo, Decimal("25.00"))
        self.assertEqual(mensalidade.valor_pago, Decimal("100.00"))
        self.assertEqual(mensalidade.valor_total, Decimal("300.00"))


class OcupacaoTestCase(TestCase):
    def setUp(self):
        self.utilizador = get_user_model().objects.create_user(
            username="enfermagem",
            password="teste",
        )
        self.quarto = Quarto.objects.create(
            codigo="201",
            piso=Piso.P2,
            capacidade=2,
        )
        self.utente = Utente.objects.create(
            nome="Utente Ocupação",
            numero_processo="PROC-2",
            quarto=self.quarto,
            data_entrada=date(2026, 9, 1),
        )

    def test_taxa_ocupacao_e_presenca_fisica(self):
        AusenciaUtente.objects.create(
            utente=self.utente,
            tipo=TipoAusenciaUtente.OUTRA,
            data_hora_inicio=momento(2026, 9, 2),
            data_hora_regresso=momento(2026, 9, 3),
            estado=EstadoAusenciaUtente.TERMINADA,
            motivo="Teste",
            criado_por=self.utilizador,
        )

        linhas, total = calcular_mapa_ocupacao(
            date(2026, 9, 1),
            date(2026, 9, 3),
            piso=Piso.P2,
        )

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["ocupacao_camas_dia"], 2)
        self.assertEqual(linhas[0]["presenca_camas_dia"], 1)
        self.assertEqual(linhas[0]["taxa_ocupacao"], 50.0)
        self.assertEqual(linhas[0]["taxa_presenca"], 25.0)
        self.assertEqual(total["taxa_ocupacao"], 50.0)


class FichaUtenteEnfermagemTestCase(TestCase):
    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name="UCCI_Enfermagem")
        area, _ = AreaClinica.objects.get_or_create(
            codigo=AREA_CLINICA_ENFERMAGEM,
            defaults={
                "nome": "Enfermagem",
                "descricao": "Registos de Enfermagem",
                "ativa": True,
            },
        )
        area.grupos_responsaveis.add(grupo)

        self.utilizador = get_user_model().objects.create_user(
            username="enfermeiro_ficha",
            password="teste",
        )
        self.utilizador.groups.add(grupo)
        self.utente = Utente.objects.create(
            nome="Utente Enfermagem",
            numero_processo="PROC-ENF",
            data_entrada=date(2026, 9, 1),
        )
        self.client.force_login(self.utilizador)

    def test_ficha_permite_gerir_ausencia_e_isolamento(self):
        url = reverse("visitas:detalhe_utente", args=[self.utente.pk])
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Registar ausência")
        self.assertContains(resposta, "Registar isolamento")

        resposta_isolamentos = self.client.get(
            reverse("visitas:isolamentos_ativos")
        )
        self.assertEqual(resposta_isolamentos.status_code, 200)
        self.assertContains(resposta_isolamentos, "Enfermagem")
        self.assertContains(resposta_isolamentos, "Ausências / Transferências")

        AusenciaUtente.objects.create(
            utente=self.utente,
            tipo=TipoAusenciaUtente.OUTRA,
            data_hora_inicio=momento(2026, 9, 2),
            estado=EstadoAusenciaUtente.ATIVA,
            motivo="Consulta externa",
            criado_por=self.utilizador,
        )

        resposta = self.client.get(url)
        self.assertContains(resposta, "Ver ausência ativa")
        self.assertContains(resposta, "Registar regresso")
        self.assertContains(resposta, "Outra ausência")
