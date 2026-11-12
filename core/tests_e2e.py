import json
import os
from decimal import Decimal
from urllib.parse import urljoin

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import Dispositivo


class NexoraBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        if os.getenv('SELENIUM_HEADLESS', '1').lower() in {'1', 'true', 'yes'}:
            options.add_argument('--headless=new')
        options.add_argument('--window-size=1440,1000')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        cls.browser = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.browser, 10)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'browser'):
            cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        self.addCleanup(self.browser.delete_all_cookies)

    def url(self, route_name):
        return urljoin(self.live_server_url, reverse(route_name))

    def wait_for_url(self, fragment):
        self.wait.until(EC.url_contains(fragment))

    def fill_field(self, name, value):
        try:
            field = self.wait.until(
                EC.presence_of_element_located((By.NAME, name)),
            )
        except TimeoutException:
            trecho = ' '.join(self.browser.page_source.split())[:500]
            self.fail(
                f'Campo "{name}" não apareceu em {self.browser.current_url}. '
                f'Título da página: "{self.browser.title}". '
                f'Início do HTML (verifique se é um erro 500): {trecho}'
            )
        field.send_keys(value)

    def login(self, username='selenium-user', password='Senha-forte-123'):
        self.browser.get(self.url('login'))
        self.fill_field('nome_usuario', username)
        self.fill_field('senha_usuario', password)
        self.browser.find_element(By.CSS_SELECTOR, 'button.btn-entrar').click()
        self.wait.until(EC.url_to_be(self.url('painel')))

    def test_visitante_sem_login_e_redirecionado_para_login(self):
        self.browser.get(self.url('painel'))

        self.wait_for_url('/login/')
        self.assertIn('next=', self.browser.current_url)

    def test_cadastro_e_login_abrem_o_painel(self):
        self.browser.get(self.url('cadastro'))
        campos = {
            'nome_usuario': 'selenium-user',
            'email_usuario': 'selenium@example.com',
            'senha_usuario': 'Senha-forte-123',
            'confirmar_senha': 'Senha-forte-123',
            'nome_empresa': 'Empresa Selenium',
        }
        for nome, valor in campos.items():
            self.fill_field(nome, valor)
        self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.wait_for_url('/login/')
        self.assertTrue(
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'login-success')),
            ).is_displayed(),
        )
        self.login()
        self.assertIn('Olá, selenium-user', self.browser.page_source)

    def test_alerta_causal_nr15_gera_os_corretiva_e_exibe_no_painel(self):
        usuario = User.objects.create_user('carlos-e2e', password='Senha-forte-123')
        dispositivo = Dispositivo.objects.create(
            dono=usuario,
            nome='Prensa Hidráulica 01',
            localizacao='Galpão Central',
            limite_kwh=Decimal('100.00'),
        )
        resposta_api = self.client.post(
            reverse('api_leitura'),
            data=json.dumps({
                'valor_kwh': 80,
                'temperatura_c': 95,
                'ruido_db': 92,
            }),
            content_type='application/json',
            HTTP_X_DEVICE_TOKEN=str(dispositivo.token),
        )
        self.assertEqual(resposta_api.status_code, 201)

        self.login(username='carlos-e2e', password='Senha-forte-123')
        alerta_texto = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.alerta')),
        ).text
        self.assertIn(
            'Degradação de lubrificante mecânico provocando atrito e elevação de ruído.',
            alerta_texto,
        )
        self.assertIn('NR-15', alerta_texto)
        self.assertIn('Ordem de Serviço Corretiva gerada automaticamente', alerta_texto)

    def test_maturidade_missoes_e_emissao_de_dossie_auditavel(self):
        usuario = User.objects.create_user('ana-e2e', password='Senha-forte-123')
        Dispositivo.objects.create(
            dono=usuario,
            nome='Torno CNC 03',
            localizacao='Setor Usinagem',
            limite_kwh=Decimal('80.00'),
        )
        self.login(username='ana-e2e', password='Senha-forte-123')
        self.assertIn('Índice Nexora de Maturidade Operacional', self.browser.page_source)
        self.assertIn('Trilha Gamificada de Missões Operacionais', self.browser.page_source)

        self.browser.get(self.url('dossie_auditoria'))
        botao = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'main button[type="submit"]')),
        )
        botao.click()
        tabela = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table.tabela')),
        )
        self.assertIn('PDF', tabela.text)
        self.assertIn('JSON', tabela.text)
