import os
from urllib.parse import urljoin

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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

    def login(self, username='selenium-user', password='Senha-forte-123'):
        self.browser.get(self.url('login'))
        self.browser.find_element(By.NAME, 'nome_usuario').send_keys(username)
        self.browser.find_element(By.NAME, 'senha_usuario').send_keys(password)
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
            self.browser.find_element(By.NAME, nome).send_keys(valor)
        self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        self.wait_for_url('/login/')
        self.assertTrue(
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'login-success')),
            ).is_displayed(),
        )
        self.login()
        self.assertIn('Olá, selenium-user', self.browser.page_source)
