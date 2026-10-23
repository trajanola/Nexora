import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Dispositivo, Leitura, Parametro
from .services import calcular_anomalias


class BaseTestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('carlos', password='senha-forte-123')
        self.outro_usuario = User.objects.create_user('outro', password='senha-forte-123')
        self.dispositivo = Dispositivo.objects.create(
            dono=self.usuario,
            nome='Prensa 02',
            localizacao='Galpão 1',
            limite_kwh=Decimal('100.00'),
        )


class AutenticacaoTests(BaseTestCase):
    def test_cadastro_e_login_protegidos_por_csrf_abrem_o_painel(self):
        cliente = Client(enforce_csrf_checks=True)
        resposta_cadastro = cliente.get(reverse('cadastro'))
        token_csrf = resposta_cadastro.cookies['csrftoken'].value
        resposta_cadastro = cliente.post(
            reverse('cadastro'),
            {
                'nome_usuario': 'nova-conta',
                'email_usuario': 'nova@example.com',
                'senha_usuario': 'senha-forte-123',
            },
            HTTP_X_CSRFTOKEN=token_csrf,
            follow=True,
        )
        self.assertRedirects(resposta_cadastro, reverse('login'))

        token_csrf = resposta_cadastro.cookies['csrftoken'].value
        resposta_login = cliente.post(
            reverse('login'),
            {
                'nome_usuario': 'nova-conta',
                'senha_usuario': 'senha-forte-123',
            },
            HTTP_X_CSRFTOKEN=token_csrf,
        )
        self.assertRedirects(resposta_login, reverse('painel'))
        self.assertEqual(cliente.get(reverse('painel')).status_code, 200)

    def test_cadastro_exibe_erro_para_nome_de_usuario_repetido(self):
        resposta = self.client.post(reverse('cadastro'), {
            'nome_usuario': 'carlos',
            'email_usuario': 'carlos@example.com',
            'senha_usuario': 'senha-forte-123',
        })
        self.assertEqual(resposta.status_code, 409)
        self.assertContains(resposta, 'Este nome de usuário já está em uso.', status_code=409)

    def test_login_redireciona_ao_painel(self):
        resposta = self.client.post(reverse('login'), {
            'nome_usuario': 'carlos',
            'senha_usuario': 'senha-forte-123',
        })
        self.assertRedirects(resposta, reverse('painel'))

    def test_login_preserva_destino_interno(self):
        destino = reverse('dispositivo_lista')
        resposta = self.client.post(
            f'{reverse("login")}?next={destino}',
            {
                'nome_usuario': 'carlos',
                'senha_usuario': 'senha-forte-123',
                'next': destino,
            },
        )
        self.assertRedirects(resposta, destino)

    def test_login_rejeita_destino_externo(self):
        resposta = self.client.post(
            f'{reverse("login")}?next=https://example.com',
            {
                'nome_usuario': 'carlos',
                'senha_usuario': 'senha-forte-123',
                'next': 'https://example.com',
            },
        )
        self.assertRedirects(resposta, reverse('painel'))

    def test_login_invalido_exibe_mensagem_de_erro(self):
        resposta = self.client.post(reverse('login'), {
            'nome_usuario': 'carlos',
            'senha_usuario': 'incorreta',
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'Usuário ou senha inválidos.', status_code=400)


class ExclusaoContaTests(BaseTestCase):
    def test_tela_de_exclusao_exige_login(self):
        resposta = self.client.get(reverse('excluir_conta'))
        self.assertRedirects(
            resposta,
            f'{reverse("login")}?next={reverse("excluir_conta")}',
        )

    def test_senha_incorreta_nao_exclui_conta(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(
            reverse('excluir_conta'),
            {'senha_atual': 'senha-errada'},
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'A senha informada está incorreta.', status_code=400)
        self.assertTrue(User.objects.filter(pk=self.usuario.pk).exists())

    def test_confirmar_exclusao_apaga_conta_e_dados_associados(self):
        leitura = Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('123.45'),
        )
        Parametro.objects.create(usuario=self.usuario)
        self.client.login(username='carlos', password='senha-forte-123')

        resposta = self.client.post(
            reverse('excluir_conta'),
            {'senha_atual': 'senha-forte-123'},
        )

        self.assertRedirects(resposta, reverse('login'))
        self.assertFalse(User.objects.filter(pk=self.usuario.pk).exists())
        self.assertFalse(Dispositivo.objects.filter(pk=self.dispositivo.pk).exists())
        self.assertFalse(Leitura.objects.filter(pk=leitura.pk).exists())
        self.assertFalse(Parametro.objects.filter(usuario_id=self.usuario.pk).exists())
        self.assertNotIn('_auth_user_id', self.client.session)


class US21DispositivosTests(BaseTestCase):
    def test_lista_exige_login(self):
        resposta = self.client.get(reverse('dispositivo_lista'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('login'), resposta.url)

    def test_cadastrar_dispositivo_associa_usuario_logado(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(reverse('dispositivo_novo'), {
            'nome': 'Torno 01',
            'localizacao': 'Galpão 2',
            'limite_kwh': '55.5',
        })
        self.assertRedirects(resposta, reverse('dispositivo_lista'))
        torno = Dispositivo.objects.get(nome='Torno 01')
        self.assertEqual(torno.dono, self.usuario)

    def test_formulario_recusa_nome_ausente(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(reverse('dispositivo_novo'), {
            'nome': '',
            'limite_kwh': '10',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Dispositivo.objects.count(), 1)

    def test_usuario_nao_acessa_dispositivo_de_outro(self):
        self.client.login(username='outro', password='senha-forte-123')
        resposta = self.client.get(reverse('dispositivo_lista'))
        self.assertNotContains(resposta, 'Prensa 02')
        resposta = self.client.get(reverse('dispositivo_detalhe', args=[self.dispositivo.pk]))
        self.assertEqual(resposta.status_code, 404)


class US22LeiturasTests(BaseTestCase):
    def enviar_leitura(self, corpo, token=None):
        cabecalhos = {'HTTP_X_DEVICE_TOKEN': str(token)} if token else {}
        return self.client.post(
            reverse('api_leitura'),
            data=json.dumps(corpo),
            content_type='application/json',
            **cabecalhos,
        )

    def test_api_registra_leitura_valida(self):
        resposta = self.enviar_leitura({'valor_kwh': 42.7}, self.dispositivo.token)
        self.assertEqual(resposta.status_code, 201)
        leitura = Leitura.objects.get()
        self.assertEqual(leitura.valor_kwh, Decimal('42.70'))
        self.assertEqual(leitura.dispositivo, self.dispositivo)

    def test_api_recusa_valores_negativos_ou_invalidos(self):
        for corpo in ({'valor_kwh': -1}, {'valor_kwh': 'abc'}, {}, {'valor_kwh': '1e1000'}):
            resposta = self.enviar_leitura(corpo, self.dispositivo.token)
            self.assertEqual(resposta.status_code, 400, corpo)
        self.assertEqual(Leitura.objects.count(), 0)

    def test_api_exige_token_valido(self):
        resposta_token_invalido = self.enviar_leitura({'valor_kwh': 1}, 'nao-e-um-uuid')
        resposta_sem_token = self.enviar_leitura({'valor_kwh': 1})
        self.assertEqual(resposta_token_invalido.status_code, 404)
        self.assertEqual(resposta_sem_token.status_code, 401)
        self.assertEqual(Leitura.objects.count(), 0)

    def test_api_recusa_corpo_que_nao_seja_objeto(self):
        resposta = self.client.post(
            reverse('api_leitura'),
            data='[]',
            content_type='application/json',
            HTTP_X_DEVICE_TOKEN=str(self.dispositivo.token),
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_de_dispositivo_nao_exige_cookie_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        resposta = cliente.post(
            reverse('api_leitura'),
            data=json.dumps({'valor_kwh': 42.7}),
            content_type='application/json',
            HTTP_X_DEVICE_TOKEN=str(self.dispositivo.token),
        )
        self.assertEqual(resposta.status_code, 201)

    def test_historico_mostra_leituras_mais_recentes_primeiro(self):
        agora = timezone.now()
        Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('10'),
            registrado_em=agora - timedelta(hours=2),
        )
        Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('20'),
            registrado_em=agora,
        )
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.get(reverse('dispositivo_detalhe', args=[self.dispositivo.pk]))
        valores = [leitura.valor_kwh for leitura in resposta.context['leituras']]
        self.assertEqual(valores, [Decimal('20.00'), Decimal('10.00')])


class US23AnomaliasTests(BaseTestCase):
    def test_custo_calculado_sobre_excedente(self):
        for valor in ('120', '150', '90'):
            Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal(valor))
        Parametro.objects.create(usuario=self.usuario, tarifa_kwh=Decimal('0.8500'))

        resumo = calcular_anomalias(self.usuario)
        item = resumo['com_anomalia'][0]
        self.assertEqual(item['qtd_anomalias'], 2)
        self.assertEqual(item['excedente_kwh'], Decimal('70.00'))
        self.assertEqual(item['custo'], Decimal('59.50'))
        self.assertEqual(resumo['custo_total'], Decimal('59.50'))

    def test_ignora_leituras_de_meses_anteriores(self):
        Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('500'),
            registrado_em=timezone.now() - timedelta(days=40),
        )
        self.assertEqual(calcular_anomalias(self.usuario)['com_anomalia'], [])

    def test_painel_sem_anomalias(self):
        Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal('50'))
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.get(reverse('painel'))
        self.assertContains(resposta, 'não há custos adicionais')

    def test_painel_com_anomalia_exibe_custo(self):
        Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal('200'))
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.get(reverse('painel'))
        self.assertContains(resposta, 'custo adicional estimado')

    def test_tarifa_invalida_e_rejeitada(self):
        self.client.login(username='carlos', password='senha-forte-123')
        for valor in ('0', '-1'):
            resposta = self.client.post(reverse('parametros'), {'tarifa_kwh': valor})
            self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Parametro.objects.get(usuario=self.usuario).tarifa_kwh, Decimal('0.8500'))

    def test_usuario_salva_tarifa(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(reverse('parametros'), {'tarifa_kwh': '1.2000'})
        self.assertRedirects(resposta, reverse('painel'))
        self.assertEqual(Parametro.objects.get(usuario=self.usuario).tarifa_kwh, Decimal('1.2000'))
