import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.urls import reverse
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.ui import WebDriverWait

from .models import Dispositivo, Leitura


@tag('selenium')
class UserStoriesSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1280,900')
        cls.driver = webdriver.Chrome(options=options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='selenium',
            email='selenium@example.com',
            password='senha-forte-123',
        )
        self.dispositivo = Dispositivo.objects.create(
            dono=self.usuario,
            empresa=self.usuario.perfil.empresa,
            nome='Prensa Selenium',
            limite_kwh=Decimal('100.00'),
        )
        agora = timezone.now()
        inicio_atual = agora.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        inicio_anterior = (inicio_atual - timedelta(days=1)).replace(day=1)
        Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('100.00'),
            registrado_em=inicio_anterior + (agora - inicio_atual) / 2,
        )
        Leitura.objects.create(
            dispositivo=self.dispositivo,
            valor_kwh=Decimal('20.00'),
            registrado_em=agora - timedelta(seconds=1),
        )
        for sinal, valor in (('ruido', 88), ('temperatura', 92)):
            resposta = self.client.post(
                reverse('api_evento'),
                data=json.dumps({'tipo': sinal, 'valor': valor}),
                content_type='application/json',
                HTTP_X_DEVICE_TOKEN=str(self.dispositivo.token),
            )
            self.assertIn(resposta.status_code, (201, 202))

    def test_painel_e_ordem_de_servico_gerada_pelos_eventos(self):
        self.driver.get(f'{self.live_server_url}{reverse("login")}')
        self.driver.find_element(By.NAME, 'nome_usuario').send_keys('selenium')
        self.driver.find_element(By.NAME, 'senha_usuario').send_keys('senha-forte-123')
        self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        WebDriverWait(self.driver, 10).until(
            expected.url_contains(reverse('painel')),
        )
        conteudo = self.driver.find_element(By.TAG_NAME, 'body').text
        self.assertIn('CO₂e evitado estimado', conteudo)
        self.assertIn('6,54 kg', conteudo)
        self.assertIn('Economia anual estimada', conteudo)
        self.assertIn(
            'Degradação de lubrificante mecânico provocando atrito e elevação de ruído',
            conteudo,
        )

        campo_valor = self.driver.find_element(By.ID, 'id_valor_financiado')
        campo_valor.clear()
        campo_valor.send_keys('200000')
        self.driver.find_element(
            By.XPATH,
            '//button[normalize-space()="Simular economia anual"]',
        ).click()
        WebDriverWait(self.driver, 10).until(
            expected.text_to_be_present_in_element(
                (By.CLASS_NAME, 'bndes-result'),
                'R$ 2400,00',
            ),
        )

        self.driver.find_element(By.LINK_TEXT, 'Abrir OS #1').click()
        WebDriverWait(self.driver, 10).until(
            expected.url_contains(reverse('ordem_servico_detalhe', args=[1])),
        )
        self.assertIn(
            'Investigar: Degradação de lubrificante mecânico',
            self.driver.find_element(By.TAG_NAME, 'body').text,
        )
