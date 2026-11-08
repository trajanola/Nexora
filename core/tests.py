import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.core import mail
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    ConviteEmpresa,
    Dispositivo,
    Leitura,
    MensagemContato,
    OrdemServico,
    Parametro,
    PerfilEmpresa,
)
from .services import calcular_anomalias


class BaseTestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('carlos', password='senha-forte-123')
        self.outro_usuario = User.objects.create_user(
            'outro',
            email='outro@example.com',
            password='senha-forte-123',
        )
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
                'confirmar_senha': 'senha-forte-123',
                'nome_empresa': 'Empresa Nova',
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
            'confirmar_senha': 'senha-forte-123',
            'nome_empresa': 'Empresa repetida',
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'Este nome de usuário já está em uso.', status_code=400)

    def test_cadastro_recusa_senhas_diferentes_e_nao_cria_conta(self):
        resposta = self.client.post(reverse('cadastro'), {
            'nome_usuario': 'sem-conta',
            'email_usuario': 'sem-conta@example.com',
            'senha_usuario': 'senha-forte-123',
            'confirmar_senha': 'outra-senha-123',
            'nome_empresa': 'Empresa Teste',
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'As senhas não coincidem.', status_code=400)
        self.assertFalse(User.objects.filter(username='sem-conta').exists())

    def test_cadastro_recusa_senha_fraca(self):
        resposta = self.client.post(reverse('cadastro'), {
            'nome_usuario': 'senha-fraca',
            'email_usuario': 'senha-fraca@example.com',
            'senha_usuario': '12345678',
            'confirmar_senha': '12345678',
            'nome_empresa': 'Empresa Teste',
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'Esta senha é inteiramente numérica.', status_code=400)
        self.assertFalse(User.objects.filter(username='senha-fraca').exists())

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


class US13ContatoTests(TestCase):
    def test_mensagem_valida_e_salva_e_confirmada(self):
        resposta = self.client.post(reverse('contato'), {
            'nome': 'Marcos',
            'email': 'marcos@example.com',
            'mensagem': 'Gostaria de conhecer a Nexora.',
        }, follow=True)

        self.assertRedirects(resposta, reverse('contato'))
        self.assertEqual(MensagemContato.objects.count(), 1)
        self.assertContains(resposta, 'Mensagem enviada com sucesso.')

    def test_mensagem_invalida_nao_e_salva(self):
        for dados in (
            {'nome': '', 'email': 'ana@example.com', 'mensagem': 'Mensagem'},
            {'nome': 'Ana', 'email': 'invalido', 'mensagem': 'Mensagem'},
            {'nome': 'Ana', 'email': 'ana@example.com', 'mensagem': ''},
        ):
            resposta = self.client.post(reverse('contato'), dados)
            self.assertEqual(resposta.status_code, 200)
        self.assertEqual(MensagemContato.objects.count(), 0)

    def test_admin_lista_mensagens_de_contato(self):
        self.assertIn(MensagemContato, admin.site._registry)
        administrador = User.objects.create_superuser(
            username='administrador',
            email='admin@example.com',
            password='senha-forte-123',
        )
        self.assertTrue(administrador.is_superuser)
        MensagemContato.objects.create(
            nome='Carlos',
            email='carlos@example.com',
            mensagem='Solicitação de demonstração.',
        )
        self.client.force_login(administrador)
        resposta = self.client.get('/admin/core/mensagemcontato/')
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Carlos')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class US15EmpresaTests(BaseTestCase):
    def test_proprietario_convida_novo_membro_e_email_contem_link(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(reverse('convites_empresa'), {
            'email': 'membro@example.com',
            'papel': PerfilEmpresa.Papel.MANUTENCAO,
        })

        convite = ConviteEmpresa.objects.get()
        self.assertRedirects(resposta, reverse('convites_empresa'))
        self.assertEqual(convite.empresa, self.usuario.perfil.empresa)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(convite.token), mail.outbox[0].body)

    def test_novo_membro_aceita_convite_e_recebe_perfil_e_empresa(self):
        convite = ConviteEmpresa.objects.create(
            empresa=self.usuario.perfil.empresa,
            email='membro@example.com',
            papel=PerfilEmpresa.Papel.MANUTENCAO,
            convidado_por=self.usuario,
        )
        resposta = self.client.post(reverse('convite_aceitar', args=[convite.token]), {
            'nome_usuario': 'membro',
            'senha_usuario': 'senha-segura-123',
            'confirmar_senha': 'senha-segura-123',
        })

        membro = User.objects.get(username='membro')
        convite.refresh_from_db()
        self.assertRedirects(resposta, reverse('login'))
        self.assertEqual(membro.email, convite.email)
        self.assertEqual(membro.perfil.empresa, self.usuario.perfil.empresa)
        self.assertEqual(membro.perfil.papel, PerfilEmpresa.Papel.MANUTENCAO)
        self.assertIsNotNone(convite.aceita_em)

    def test_usuario_existente_aceita_convite_e_migra_dados_da_empresa_individual(self):
        empresa_antiga = self.outro_usuario.perfil.empresa
        dispositivo = Dispositivo.objects.create(
            dono=self.outro_usuario,
            nome='Motor do outro usuário',
            limite_kwh=Decimal('25.00'),
        )
        Parametro.objects.create(empresa=empresa_antiga, tarifa_kwh=Decimal('1.1000'))
        convite = ConviteEmpresa.objects.create(
            empresa=self.usuario.perfil.empresa,
            email=self.outro_usuario.email,
            papel=PerfilEmpresa.Papel.FINANCEIRO,
            convidado_por=self.usuario,
        )
        self.client.login(username='outro', password='senha-forte-123')

        resposta = self.client.post(reverse('convite_aceitar', args=[convite.token]))

        convite.refresh_from_db()
        dispositivo.refresh_from_db()
        self.assertRedirects(resposta, reverse('painel'))
        perfil_atualizado = User.objects.get(pk=self.outro_usuario.pk).perfil
        self.assertEqual(perfil_atualizado.empresa, self.usuario.perfil.empresa)
        self.assertEqual(dispositivo.empresa, self.usuario.perfil.empresa)
        self.assertEqual(
            Parametro.objects.get(empresa=self.usuario.perfil.empresa).tarifa_kwh,
            Decimal('1.1000'),
        )
        self.assertIsNotNone(convite.aceita_em)
        self.assertFalse(type(empresa_antiga).objects.filter(pk=empresa_antiga.pk).exists())

    def test_membros_da_mesma_empresa_compartilham_dispositivos(self):
        membro = User.objects.create_user('membro', password='senha-segura-123')
        perfil = membro.perfil
        empresa_individual = perfil.empresa
        perfil.empresa = self.usuario.perfil.empresa
        perfil.papel = PerfilEmpresa.Papel.MANUTENCAO
        perfil.save()
        empresa_individual.delete()
        self.client.login(username='membro', password='senha-segura-123')

        resposta = self.client.get(reverse('dispositivo_lista'))

        self.assertContains(resposta, 'Prensa 02')
        self.assertEqual(
            self.client.get(reverse('dispositivo_detalhe', args=[self.dispositivo.pk])).status_code,
            200,
        )

    def test_usuario_de_outra_empresa_nao_acessa_dispositivo(self):
        self.client.login(username='outro', password='senha-forte-123')
        resposta = self.client.get(reverse('dispositivo_detalhe', args=[self.dispositivo.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_gerente_de_manutencao_nao_acessa_parametros_financeiros(self):
        perfil = self.usuario.perfil
        perfil.papel = PerfilEmpresa.Papel.MANUTENCAO
        perfil.save()
        self.client.login(username='carlos', password='senha-forte-123')

        self.assertEqual(self.client.get(reverse('parametros')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('painel')), 'Tarifa</a>')

    def test_perfil_nao_proprietario_nao_pode_convidar_membros(self):
        perfil = self.usuario.perfil
        perfil.papel = PerfilEmpresa.Papel.FINANCEIRO
        perfil.save()
        self.client.login(username='carlos', password='senha-forte-123')
        self.assertEqual(self.client.get(reverse('convites_empresa')).status_code, 403)


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
        empresa_id = self.usuario.perfil.empresa_id
        Parametro.objects.create(empresa_id=empresa_id)
        self.client.login(username='carlos', password='senha-forte-123')

        resposta = self.client.post(
            reverse('excluir_conta'),
            {'senha_atual': 'senha-forte-123'},
        )

        self.assertRedirects(resposta, reverse('login'))
        self.assertFalse(User.objects.filter(pk=self.usuario.pk).exists())
        self.assertFalse(Dispositivo.objects.filter(pk=self.dispositivo.pk).exists())
        self.assertFalse(Leitura.objects.filter(pk=leitura.pk).exists())
        self.assertFalse(Parametro.objects.filter(empresa_id=empresa_id).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_excluir_proprietario_transfere_empresa_e_preserva_dispositivos_para_membros(self):
        empresa = self.usuario.perfil.empresa
        perfil_membro = self.outro_usuario.perfil
        empresa_individual = perfil_membro.empresa
        perfil_membro.empresa = empresa
        perfil_membro.papel = PerfilEmpresa.Papel.MANUTENCAO
        perfil_membro.save()
        empresa_individual.delete()
        leitura = Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('123.45'),
        )
        Parametro.objects.create(empresa=empresa)
        self.client.login(username='carlos', password='senha-forte-123')

        resposta = self.client.post(
            reverse('excluir_conta'),
            {'senha_atual': 'senha-forte-123'},
            follow=True,
        )

        self.dispositivo.refresh_from_db()
        perfil_membro.refresh_from_db()
        self.assertRedirects(resposta, reverse('login'))
        self.assertFalse(User.objects.filter(pk=self.usuario.pk).exists())
        self.assertEqual(perfil_membro.papel, PerfilEmpresa.Papel.PROPRIETARIO)
        self.assertEqual(self.dispositivo.empresa, empresa)
        self.assertIsNone(self.dispositivo.dono)
        self.assertTrue(Leitura.objects.filter(pk=leitura.pk).exists())
        self.assertTrue(Parametro.objects.filter(empresa=empresa).exists())
        self.assertContains(resposta, 'a propriedade da empresa passou para outro')


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

    def test_api_registra_leituras_em_lote_e_rejeita_item_invalido(self):
        resposta = self.enviar_leitura({
            'leituras': [
                {'id_externo': 'sensor-1', 'valor_kwh': 42.7},
                {'id_externo': 'sensor-2', 'valor_kwh': -1},
                {'id_externo': 'sensor-3', 'valor_kwh': 12.5},
            ],
        }, self.dispositivo.token)

        self.assertEqual(resposta.status_code, 207)
        corpo = resposta.json()
        self.assertEqual(corpo['criadas'], 2)
        self.assertEqual(len(corpo['erros']), 1)
        self.assertEqual(Leitura.objects.count(), 2)

    def test_api_nao_duplica_leitura_com_id_externo_repetido(self):
        corpo = {
            'leituras': [
                {'id_externo': 'sensor-1', 'valor_kwh': 42.7},
            ],
        }
        primeira = self.enviar_leitura(corpo, self.dispositivo.token)
        segunda = self.enviar_leitura(corpo, self.dispositivo.token)

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(segunda.json()['duplicadas'], 1)
        self.assertEqual(Leitura.objects.count(), 1)

    def test_api_aceita_data_iso_na_leitura_em_lote(self):
        resposta = self.enviar_leitura({
            'leituras': [{
                'id_externo': 'sensor-1',
                'valor_kwh': 15,
                'registrado_em': '2026-11-08T12:00:00-03:00',
            }],
        }, self.dispositivo.token)

        self.assertEqual(resposta.status_code, 201)
        leitura = Leitura.objects.get()
        self.assertEqual(leitura.registrado_em.utcoffset(), timedelta(0))

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


class US18OrdensServicoTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='carlos', password='senha-forte-123')
        self.url_detalhe_dispositivo = reverse(
            'dispositivo_detalhe',
            args=[self.dispositivo.pk],
        )

    def criar_rascunho(self, resumo='Revisar prensa'):
        return self.client.post(
            reverse('ordem_servico_nova', args=[self.dispositivo.pk]),
            {'resumo': resumo, 'descricao': 'Verificar vibração anormal.'},
        )

    def test_cria_ordem_como_rascunho_e_exibe_no_historico_da_maquina(self):
        resposta = self.criar_rascunho()
        ordem = OrdemServico.objects.get()

        self.assertRedirects(
            resposta,
            reverse('ordem_servico_detalhe', args=[ordem.pk]),
        )
        self.assertEqual(ordem.status, OrdemServico.Status.RASCUNHO)
        historico = self.client.get(self.url_detalhe_dispositivo)
        self.assertContains(historico, 'Revisar prensa')
        self.assertContains(historico, 'Rascunho')

    def test_nao_cria_os_para_dispositivo_de_outro_usuario(self):
        self.client.login(username='outro', password='senha-forte-123')
        resposta = self.client.get(
            reverse('ordem_servico_nova', args=[self.dispositivo.pk]),
        )
        self.assertEqual(resposta.status_code, 404)

    def test_aprovar_registra_data_e_responsavel(self):
        self.criar_rascunho()
        ordem = OrdemServico.objects.get()

        resposta = self.client.post(
            reverse('ordem_servico_acao', args=[ordem.pk]),
            {'acao': 'aprovar'},
        )

        ordem.refresh_from_db()
        self.assertRedirects(resposta, reverse('ordem_servico_detalhe', args=[ordem.pk]))
        self.assertEqual(ordem.status, OrdemServico.Status.APROVADA)
        self.assertIsNotNone(ordem.aprovada_em)
        self.assertEqual(ordem.aprovada_por, self.usuario)

    def test_nao_permite_aprovar_uma_os_mais_de_uma_vez(self):
        self.criar_rascunho()
        ordem = OrdemServico.objects.get()
        url_acao = reverse('ordem_servico_acao', args=[ordem.pk])
        self.client.post(url_acao, {'acao': 'aprovar'})
        self.client.post(url_acao, {'acao': 'aprovar'})

        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.Status.APROVADA)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_nao_conclui_sem_dados_obrigatorios(self):
        self.criar_rascunho()
        ordem = OrdemServico.objects.get()
        ordem.status = OrdemServico.Status.EM_EXECUCAO
        ordem.save(update_fields=['status'])

        resposta = self.client.post(
            reverse('ordem_servico_acao', args=[ordem.pk]),
            {
                'acao': 'concluir',
                'causa_confirmada': '',
                'acao_realizada': '',
                'tempo_parada_minutos': '',
            },
        )

        ordem.refresh_from_db()
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(ordem.status, OrdemServico.Status.EM_EXECUCAO)
        self.assertIsNone(ordem.concluida_em)

    def test_fluxo_completo_registra_intervencao_e_responsavel(self):
        self.criar_rascunho()
        ordem = OrdemServico.objects.get()
        url_acao = reverse('ordem_servico_acao', args=[ordem.pk])

        self.client.post(url_acao, {'acao': 'aprovar'})
        self.client.post(url_acao, {'acao': 'iniciar'})
        resposta = self.client.post(
            url_acao,
            {
                'acao': 'concluir',
                'causa_confirmada': 'Rolamento desgastado',
                'acao_realizada': 'Rolamento substituído e equipamento testado.',
                'tempo_parada_minutos': '45',
            },
        )

        ordem.refresh_from_db()
        self.assertRedirects(resposta, reverse('ordem_servico_detalhe', args=[ordem.pk]))
        self.assertEqual(ordem.status, OrdemServico.Status.CONCLUIDA)
        self.assertEqual(ordem.causa_confirmada, 'Rolamento desgastado')
        self.assertEqual(ordem.acao_realizada, 'Rolamento substituído e equipamento testado.')
        self.assertEqual(ordem.tempo_parada_minutos, 45)
        self.assertIsNotNone(ordem.concluida_em)
        self.assertEqual(ordem.concluida_por, self.usuario)

    def test_historico_da_maquina_e_exibido_em_ordem_cronologica(self):
        mais_antiga = OrdemServico.objects.create(
            dispositivo=self.dispositivo,
            resumo='Primeira intervenção',
        )
        mais_recente = OrdemServico.objects.create(
            dispositivo=self.dispositivo,
            resumo='Segunda intervenção',
        )

        resposta = self.client.get(self.url_detalhe_dispositivo)

        ordens = list(resposta.context['ordens_servico'])
        self.assertEqual([ordem.pk for ordem in ordens], [mais_antiga.pk, mais_recente.pk])

    def test_usuario_nao_visualiza_ou_altera_os_de_outro(self):
        ordem = OrdemServico.objects.create(
            dispositivo=self.dispositivo,
            resumo='OS privada',
        )
        self.client.login(username='outro', password='senha-forte-123')

        resposta_detalhe = self.client.get(
            reverse('ordem_servico_detalhe', args=[ordem.pk]),
        )
        resposta_acao = self.client.post(
            reverse('ordem_servico_acao', args=[ordem.pk]),
            {'acao': 'aprovar'},
        )

        self.assertEqual(resposta_detalhe.status_code, 404)
        self.assertEqual(resposta_acao.status_code, 404)
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.Status.RASCUNHO)


class US23AnomaliasTests(BaseTestCase):
    def test_custo_calculado_sobre_excedente(self):
        for valor in ('120', '150', '90'):
            Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal(valor))
        Parametro.objects.create(empresa=self.usuario.perfil.empresa, tarifa_kwh=Decimal('0.8500'))

        resumo = calcular_anomalias(self.usuario)
        item = resumo['com_anomalia'][0]
        self.assertEqual(item['qtd_anomalias'], 2)
        self.assertEqual(item['excedente_kwh'], Decimal('70.00'))
        self.assertEqual(item['custo'], Decimal('59.50'))
        self.assertEqual(resumo['custo_total'], Decimal('59.50'))

    def test_payback_divide_custo_de_reparo_pelo_custo_mensal(self):
        self.dispositivo.custo_reparo = Decimal('100.00')
        self.dispositivo.save(update_fields=['custo_reparo'])
        Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal('200.00'))

        resumo = calcular_anomalias(self.usuario)

        self.assertEqual(resumo['com_anomalia'][0]['custo'], Decimal('85.00'))
        self.assertEqual(resumo['com_anomalia'][0]['payback_meses'], Decimal('1.18'))

    def test_payback_so_aparece_com_custo_de_reparo_e_anomalia(self):
        Leitura.objects.create(dispositivo=self.dispositivo, valor_kwh=Decimal('200.00'))
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.get(reverse('painel'))
        self.assertNotContains(resposta, 'Payback estimado')

        self.dispositivo.custo_reparo = Decimal('50.00')
        self.dispositivo.save(update_fields=['custo_reparo'])
        resposta = self.client.get(reverse('painel'))
        self.assertContains(resposta, 'Payback estimado do reparo preventivo')

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
        self.assertEqual(
            Parametro.objects.get(empresa=self.usuario.perfil.empresa).tarifa_kwh,
            Decimal('0.8500'),
        )

    def test_usuario_salva_tarifa(self):
        self.client.login(username='carlos', password='senha-forte-123')
        resposta = self.client.post(reverse('parametros'), {'tarifa_kwh': '1.2000'})
        self.assertRedirects(resposta, reverse('painel'))
        self.assertEqual(
            Parametro.objects.get(empresa=self.usuario.perfil.empresa).tarifa_kwh,
            Decimal('1.2000'),
        )
