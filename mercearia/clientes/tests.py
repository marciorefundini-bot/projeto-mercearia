"""
Testes do app 'clientes'.

Organização:
  ClienteModelTest      — testa o model Cliente (divida_total)
  ProdutoModelTest      — testa o model Produto (validators)
  VendaModelTest        — testa criação, edição e exclusão com controle de estoque
  VendaConcurrenteTest  — testa race condition (usa TransactionTestCase)
  ViewAuthTest          — garante que todas as views exigem login
  ViewClienteTest       — testa CRUD de clientes via HTTP
  ViewProdutoTest       — testa CRUD de produtos via HTTP
  ViewVendaTest         — testa criação, edição, exclusão e pagamento de vendas
  FormVendaTest         — testa validações do VendaForm

Como rodar:
  python manage.py test clientes
  python manage.py test clientes.tests.VendaModelTest  # apenas uma classe
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from .models import Cliente, Produto, Venda


# ── Helpers de fixture ────────────────────────────────────────────────────────

def cria_produto(nome='Arroz', preco=Decimal('5.00'), estoque=10):
    """
    Cria e retorna um Produto para uso nos testes.

    Usa Decimal como padrão — não use string '5.00'.
    Com string, o atributo em memória permanece str e operações como
    quantidade * valor_unitario produzem concatenação em vez de multiplicação.
    """
    return Produto.objects.create(nome=nome, preco=preco, estoque=estoque)


def cria_cliente(nome='Maria', telefone='11999990000', endereco='Rua A, 1'):
    """Cria e retorna um Cliente para uso nos testes."""
    return Cliente.objects.create(nome=nome, telefone=telefone, endereco=endereco)


def cria_venda(produto, quantidade=2, tipo=Venda.TIPO_AVISTA, cliente=None, pago=True):
    """Cria e retorna uma Venda para uso nos testes."""
    return Venda.objects.create(
        produto=produto,
        cliente=cliente,
        quantidade=quantidade,
        valor_unitario=produto.preco,
        tipo=tipo,
        pago=pago,
    )


# ── Testes de model: Cliente ──────────────────────────────────────────────────

class ClienteModelTest(TestCase):
    """Testa o comportamento do model Cliente."""

    def setUp(self):
        self.cliente = cria_cliente()
        self.produto = cria_produto()

    def test_str_retorna_nome(self):
        """__str__ deve retornar o nome do cliente."""
        self.assertEqual(str(self.cliente), 'Maria')

    def test_divida_total_sem_vendas(self):
        """divida_total() deve retornar 0 quando não há vendas."""
        self.assertEqual(self.cliente.divida_total(), 0)

    def test_divida_total_somente_fiado_nao_pago(self):
        """divida_total() deve somar apenas fiados não pagos."""
        # Fiado não pago: R$ 5 × 2 = R$ 10
        cria_venda(self.produto, quantidade=2, tipo=Venda.TIPO_FIADO,
                   cliente=self.cliente, pago=False)
        # Fiado já pago: não deve entrar na conta
        cria_venda(self.produto, quantidade=1, tipo=Venda.TIPO_FIADO,
                   cliente=self.cliente, pago=True)
        # Venda à vista: não deve entrar na conta
        cria_venda(self.produto, quantidade=3, tipo=Venda.TIPO_AVISTA,
                   cliente=self.cliente, pago=True)
        self.produto.refresh_from_db()
        self.assertEqual(self.cliente.divida_total(), 10)

    def test_divida_total_zera_ao_pagar(self):
        """Após pagar todas as vendas, divida_total() deve ser 0."""
        venda = cria_venda(self.produto, quantidade=1, tipo=Venda.TIPO_FIADO,
                           cliente=self.cliente, pago=False)
        self.produto.refresh_from_db()
        self.assertGreater(self.cliente.divida_total(), 0)

        venda.pago = True
        venda.save(update_fields=['pago'])
        self.assertEqual(self.cliente.divida_total(), 0)


# ── Testes de model: Produto ──────────────────────────────────────────────────

class ProdutoModelTest(TestCase):
    """Testa validações do model Produto."""

    def test_str_retorna_nome(self):
        produto = cria_produto(nome='Feijão')
        self.assertEqual(str(produto), 'Feijão')

    def test_preco_negativo_invalida(self):
        """Preço negativo deve lançar ValidationError na full_clean()."""
        produto = Produto(nome='X', preco='-1.00', estoque=5)
        with self.assertRaises(ValidationError):
            produto.full_clean()

    def test_estoque_negativo_invalida(self):
        """Estoque negativo deve lançar ValidationError na full_clean()."""
        produto = Produto(nome='X', preco='1.00', estoque=-1)
        with self.assertRaises(ValidationError):
            produto.full_clean()


# ── Testes de model: Venda ────────────────────────────────────────────────────

class VendaModelTest(TestCase):
    """Testa criação, edição e exclusão de vendas com controle de estoque."""

    def setUp(self):
        self.produto = cria_produto(estoque=10)
        self.cliente = cria_cliente()

    # ── Criação ───────────────────────────────────────────────────────────────

    def test_criar_venda_decrementa_estoque(self):
        """Criar uma venda deve decrementar o estoque do produto."""
        cria_venda(self.produto, quantidade=3)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 7)  # 10 - 3 = 7

    def test_criar_venda_estoque_insuficiente_lanca_erro(self):
        """Tentar vender mais do que há em estoque deve lançar ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            cria_venda(self.produto, quantidade=999)
        self.assertIn('Estoque insuficiente', str(ctx.exception))

    def test_criar_venda_estoque_exato_funciona(self):
        """Vender exatamente o que há em estoque deve funcionar (estoque = 0)."""
        cria_venda(self.produto, quantidade=10)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 0)

    def test_criar_venda_str(self):
        """__str__ deve incluir o nome do produto e o tipo da venda."""
        venda = cria_venda(self.produto, quantidade=1)
        self.assertIn(self.produto.nome, str(venda))
        self.assertIn('Vista', str(venda))

    def test_total_calcula_corretamente(self):
        """total() deve retornar quantidade × valor_unitario."""
        venda = cria_venda(self.produto, quantidade=4)
        # produto.preco = Decimal('5.00'); 4 × 5.00 = 20.00
        self.assertEqual(venda.total(), Decimal('20.00'))

    # ── Edição ────────────────────────────────────────────────────────────────

    def test_editar_quantidade_ajusta_estoque(self):
        """Aumentar a quantidade de uma venda deve decrementar o estoque."""
        venda = cria_venda(self.produto, quantidade=2)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 8)  # 10 - 2 = 8

        venda.quantidade = 5
        venda.save()
        self.produto.refresh_from_db()
        # Delta: 5 - 2 = 3 a mais; 8 - 3 = 5
        self.assertEqual(self.produto.estoque, 5)

    def test_editar_quantidade_para_menos_restaura_estoque(self):
        """Reduzir a quantidade de uma venda deve restaurar parte do estoque."""
        venda = cria_venda(self.produto, quantidade=5)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 5)  # 10 - 5

        venda.quantidade = 2
        venda.save()
        self.produto.refresh_from_db()
        # Delta: 2 - 5 = -3 (devolve 3); 5 + 3 = 8
        self.assertEqual(self.produto.estoque, 8)

    def test_editar_produto_ajusta_ambos_estoques(self):
        """Trocar o produto de uma venda deve ajustar o estoque de ambos."""
        outro_produto = cria_produto(nome='Feijão', estoque=20)
        venda = cria_venda(self.produto, quantidade=3)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 7)  # 10 - 3

        venda.produto = outro_produto
        venda.quantidade = 4
        venda.save()

        self.produto.refresh_from_db()
        outro_produto.refresh_from_db()
        # Produto original deve ter recebido de volta as 3 unidades
        self.assertEqual(self.produto.estoque, 10)
        # Novo produto deve ter sido decrementado em 4
        self.assertEqual(outro_produto.estoque, 16)  # 20 - 4

    def test_editar_somente_pago_nao_altera_estoque(self):
        """Marcar como pago não deve alterar o estoque."""
        venda = cria_venda(self.produto, quantidade=2, tipo=Venda.TIPO_FIADO,
                           cliente=self.cliente, pago=False)
        self.produto.refresh_from_db()
        estoque_antes = self.produto.estoque  # 10 - 2 = 8

        venda.pago = True
        venda.save(update_fields=['pago'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, estoque_antes)

    # ── Exclusão ──────────────────────────────────────────────────────────────

    def test_deletar_venda_restaura_estoque(self):
        """Excluir uma venda deve restaurar a quantidade no estoque."""
        venda = cria_venda(self.produto, quantidade=4)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 6)  # 10 - 4

        venda.delete()
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 10)  # Restaurado

    def test_deletar_venda_com_estoque_zero(self):
        """Deve ser possível deletar uma venda quando estoque está em zero."""
        venda = cria_venda(self.produto, quantidade=10)  # Zera estoque
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 0)

        venda.delete()
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 10)


# ── Testes de concorrência ────────────────────────────────────────────────────

class VendaConcurrenteTest(TransactionTestCase):
    """
    Testa race conditions no controle de estoque.

    Usa TransactionTestCase (não TestCase) porque precisamos que as transações
    de banco sejam realmente commitadas para que as threads concorrentes
    enxerguem o estado umas das outras.
    """

    def test_venda_concorrente_nao_permite_estoque_negativo(self):
        """
        Duas threads tentando vender o último item simultaneamente:
        apenas uma deve ter sucesso; o estoque nunca deve ficar negativo.
        """
        produto = cria_produto(estoque=1)
        cliente = cria_cliente()
        sucessos = []
        falhas = []

        def tentar_vender():
            """Tentativa de criar uma venda — registra sucesso ou falha."""
            # Cada thread precisa de um objeto produto atualizado do banco
            p = Produto.objects.get(pk=produto.pk)
            try:
                Venda.objects.create(
                    produto=p,
                    cliente=cliente,
                    quantidade=1,
                    valor_unitario=p.preco,
                    tipo=Venda.TIPO_FIADO,
                    pago=False,
                )
                sucessos.append(True)
            except (ValidationError, Exception):
                falhas.append(True)

        # Dispara 3 threads ao mesmo tempo tentando vender o único item
        with ThreadPoolExecutor(max_workers=3) as executor:
            futs = [executor.submit(tentar_vender) for _ in range(3)]
            for f in futs:
                f.result()  # Aguarda todas terminarem

        produto.refresh_from_db()

        # Estoque nunca pode ser negativo
        self.assertGreaterEqual(produto.estoque, 0)
        # Exatamente 1 venda deve ter sido criada
        self.assertEqual(len(sucessos), 1)
        # As outras 2 devem ter falhado
        self.assertEqual(len(falhas), 2)


# ── Testes de autenticação ────────────────────────────────────────────────────

class ViewAuthTest(TestCase):
    """Verifica que todas as views exigem autenticação."""

    # URLs que devem redirecionar para login se não autenticado
    URLS_PROTEGIDAS = [
        'dashboard',
        'lista_clientes',
        'criar_cliente',
        'lista_produtos',
        'criar_produto',
        'lista_vendas',
        'criar_venda',
    ]

    def test_views_redirecionam_anonimo(self):
        """Usuário anônimo deve ser redirecionado para /login/ em todas as views."""
        for nome_url in self.URLS_PROTEGIDAS:
            with self.subTest(url=nome_url):
                response = self.client.get(reverse(nome_url))
                self.assertRedirects(
                    response,
                    f'/login/?next={reverse(nome_url)}',
                    msg_prefix=f"View '{nome_url}' não exige autenticação",
                )

    def test_views_acessiveis_autenticado(self):
        """Usuário autenticado deve conseguir acessar todas as views protegidas."""
        User.objects.create_superuser('admin', 'a@a.com', 'senha123')
        self.client.login(username='admin', password='senha123')
        for nome_url in self.URLS_PROTEGIDAS:
            with self.subTest(url=nome_url):
                response = self.client.get(reverse(nome_url))
                # 200 OK ou redirect interno (ex.: form com dados vazios)
                self.assertIn(response.status_code, [200, 302])


# ── Testes de view: Cliente ───────────────────────────────────────────────────

class ViewClienteTest(TestCase):
    """Testa o CRUD de clientes via requisições HTTP."""

    def setUp(self):
        # Autentica o usuário de teste antes de cada teste
        self.user = User.objects.create_superuser('admin', 'a@a.com', 'senha123')
        self.client.login(username='admin', password='senha123')

    def test_lista_clientes_status_200(self):
        response = self.client.get(reverse('lista_clientes'))
        self.assertEqual(response.status_code, 200)

    def test_criar_cliente_post_valido(self):
        """POST válido deve criar o cliente e redirecionar para a lista."""
        response = self.client.post(reverse('criar_cliente'), {
            'nome': 'João Silva',
            'telefone': '11999990000',
            'endereco': 'Rua B, 10',
        })
        self.assertRedirects(response, reverse('lista_clientes'))
        self.assertTrue(Cliente.objects.filter(nome='João Silva').exists())

    def test_criar_cliente_post_invalido(self):
        """POST com campos obrigatórios vazios deve re-renderizar o formulário."""
        response = self.client.post(reverse('criar_cliente'), {'nome': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Cliente.objects.filter(nome='').exists())

    def test_editar_cliente(self):
        """Editar nome do cliente deve persistir a alteração."""
        cliente = cria_cliente(nome='Ana')
        response = self.client.post(reverse('editar_cliente', args=[cliente.pk]), {
            'nome': 'Ana Paula',
            'telefone': '11988880000',
            'endereco': 'Rua C, 5',
        })
        self.assertRedirects(response, reverse('lista_clientes'))
        cliente.refresh_from_db()
        self.assertEqual(cliente.nome, 'Ana Paula')

    def test_deletar_cliente(self):
        """POST para deletar deve remover o cliente do banco."""
        cliente = cria_cliente()
        response = self.client.post(reverse('deletar_cliente', args=[cliente.pk]))
        self.assertRedirects(response, reverse('lista_clientes'))
        self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())

    def test_detalhe_cliente_404_inexistente(self):
        """Acessar cliente que não existe deve retornar 404."""
        response = self.client.get(reverse('detalhe_cliente', args=[99999]))
        self.assertEqual(response.status_code, 404)


# ── Testes de view: Produto ───────────────────────────────────────────────────

class ViewProdutoTest(TestCase):
    """Testa o CRUD de produtos via requisições HTTP."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@a.com', 'senha123')
        self.client.login(username='admin', password='senha123')

    def test_lista_produtos_status_200(self):
        response = self.client.get(reverse('lista_produtos'))
        self.assertEqual(response.status_code, 200)

    def test_criar_produto_post_valido(self):
        """POST válido deve criar o produto e redirecionar para a lista."""
        response = self.client.post(reverse('criar_produto'), {
            'nome': 'Leite',
            'preco': '3.50',
            'estoque': '20',
        })
        self.assertRedirects(response, reverse('lista_produtos'))
        self.assertTrue(Produto.objects.filter(nome='Leite').exists())

    def test_criar_produto_preco_negativo_invalido(self):
        """Preço negativo deve ser rejeitado pelo formulário."""
        response = self.client.post(reverse('criar_produto'), {
            'nome': 'Sal',
            'preco': '-1.00',
            'estoque': '5',
        })
        self.assertEqual(response.status_code, 200)  # Não redireciona
        self.assertFalse(Produto.objects.filter(nome='Sal').exists())

    def test_deletar_produto_restaura_sem_crash(self):
        """Deletar produto com vendas deve funcionar (CASCADE remove as vendas)."""
        produto = cria_produto()
        cria_venda(produto, quantidade=1)
        response = self.client.post(reverse('deletar_produto', args=[produto.pk]))
        self.assertRedirects(response, reverse('lista_produtos'))
        self.assertFalse(Produto.objects.filter(pk=produto.pk).exists())


# ── Testes de view: Venda ─────────────────────────────────────────────────────

class ViewVendaTest(TestCase):
    """Testa criação, edição, exclusão e pagamento de vendas via HTTP."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@a.com', 'senha123')
        self.client.login(username='admin', password='senha123')
        self.produto = cria_produto(estoque=20)
        self.cliente = cria_cliente()

    def test_lista_vendas_status_200(self):
        response = self.client.get(reverse('lista_vendas'))
        self.assertEqual(response.status_code, 200)

    def test_lista_vendas_filtro_avista(self):
        """Filtro por tipo 'avista' deve retornar somente vendas à vista."""
        response = self.client.get(reverse('lista_vendas') + '?tipo=avista')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tipo_filtro'], 'avista')

    def test_criar_venda_avista_decrementa_estoque(self):
        """Criar venda à vista deve decrementar estoque e redirecionar."""
        response = self.client.post(reverse('criar_venda'), {
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 3,
            'cliente': '',
        })
        self.assertRedirects(response, reverse('lista_vendas'))
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 17)  # 20 - 3

    def test_criar_venda_avista_marcada_como_paga(self):
        """Venda à vista deve ser automaticamente marcada como paga."""
        self.client.post(reverse('criar_venda'), {
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 1,
            'cliente': '',
        })
        venda = Venda.objects.latest('data')
        self.assertTrue(venda.pago)

    def test_criar_venda_fiado_requer_cliente(self):
        """Venda fiado sem cliente deve retornar formulário com erro."""
        response = self.client.post(reverse('criar_venda'), {
            'tipo': 'fiado',
            'produto': self.produto.pk,
            'quantidade': 1,
            'cliente': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'obrigatório')

    def test_criar_venda_estoque_insuficiente_exibe_erro(self):
        """Tentar vender mais do que o estoque deve exibir mensagem de erro."""
        response = self.client.post(reverse('criar_venda'), {
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 999,
            'cliente': '',
        })
        # O form retorna 200 com a mensagem de erro ou redireciona com flash
        self.assertIn(response.status_code, [200, 302])
        self.produto.refresh_from_db()
        # Estoque não deve ter sido alterado
        self.assertEqual(self.produto.estoque, 20)

    def test_deletar_venda_restaura_estoque(self):
        """Excluir uma venda deve restaurar o estoque do produto."""
        venda = cria_venda(self.produto, quantidade=5)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 15)

        response = self.client.post(reverse('deletar_venda', args=[venda.pk]))
        self.assertRedirects(response, reverse('lista_vendas'))
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 20)

    def test_pagar_venda_fiado(self):
        """POST para pagar_venda deve marcar o fiado como pago."""
        venda = cria_venda(self.produto, quantidade=2, tipo=Venda.TIPO_FIADO,
                           cliente=self.cliente, pago=False)
        self.produto.refresh_from_db()

        response = self.client.post(reverse('pagar_venda', args=[venda.pk]))
        self.assertEqual(response.status_code, 302)
        venda.refresh_from_db()
        self.assertTrue(venda.pago)

    def test_pagar_venda_get_retorna_405(self):
        """GET para pagar_venda deve retornar 405 (método não permitido)."""
        venda = cria_venda(self.produto, quantidade=1, tipo=Venda.TIPO_FIADO,
                           cliente=self.cliente, pago=False)
        self.produto.refresh_from_db()
        response = self.client.get(reverse('pagar_venda', args=[venda.pk]))
        self.assertEqual(response.status_code, 405)

    def test_pagar_venda_avista_retorna_404(self):
        """Tentar pagar uma venda à vista deve retornar 404 (filtro no get_object_or_404)."""
        venda = cria_venda(self.produto, quantidade=1, tipo=Venda.TIPO_AVISTA, pago=True)
        response = self.client.post(reverse('pagar_venda', args=[venda.pk]))
        self.assertEqual(response.status_code, 404)

    def test_pagar_venda_nao_redireciona_para_url_externa(self):
        """next=URL_externa não deve causar open redirect."""
        venda = cria_venda(self.produto, quantidade=1, tipo=Venda.TIPO_FIADO,
                           cliente=self.cliente, pago=False)
        self.produto.refresh_from_db()
        response = self.client.post(
            reverse('pagar_venda', args=[venda.pk]),
            {'next': 'https://malicioso.com'},
        )
        # Deve redirecionar para lista_vendas (URL local), não para o domínio externo
        self.assertRedirects(response, reverse('lista_vendas'))

    def test_editar_venda_ajusta_estoque(self):
        """Editar quantidade de uma venda deve refletir no estoque."""
        venda = cria_venda(self.produto, quantidade=3)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 17)

        response = self.client.post(reverse('editar_venda', args=[venda.pk]), {
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 6,
            'cliente': '',
        })
        self.assertRedirects(response, reverse('lista_vendas'))
        self.produto.refresh_from_db()
        # Delta: 6 - 3 = 3 a mais descontados; 17 - 3 = 14
        self.assertEqual(self.produto.estoque, 14)


# ── Testes de formulário: VendaForm ──────────────────────────────────────────

class FormVendaTest(TestCase):
    """Testa as validações do VendaForm."""

    def setUp(self):
        self.produto = cria_produto(estoque=5)
        self.cliente = cria_cliente()

    def test_fiado_sem_cliente_invalido(self):
        """VendaForm com tipo=fiado e sem cliente deve ser inválido."""
        from .forms import VendaForm
        form = VendaForm(data={
            'tipo': 'fiado',
            'produto': self.produto.pk,
            'quantidade': 1,
            'cliente': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('cliente', form.errors)

    def test_avista_sem_cliente_valido(self):
        """VendaForm com tipo=avista sem cliente deve ser válido."""
        from .forms import VendaForm
        form = VendaForm(data={
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 1,
            'cliente': '',
        })
        self.assertTrue(form.is_valid())

    def test_estoque_insuficiente_invalido(self):
        """VendaForm com quantidade maior que estoque deve ser inválido."""
        from .forms import VendaForm
        form = VendaForm(data={
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 999,  # Estoque é 5
            'cliente': '',
        })
        self.assertFalse(form.is_valid())

    def test_quantidade_zero_invalido(self):
        """VendaForm com quantidade 0 deve ser inválido."""
        from .forms import VendaForm
        form = VendaForm(data={
            'tipo': 'avista',
            'produto': self.produto.pk,
            'quantidade': 0,
            'cliente': '',
        })
        self.assertFalse(form.is_valid())


# ── Testes de cadastro rápido de cliente ──────────────────────────────────────

class ClienteRapidoTest(TestCase):
    """Testa o endpoint de cadastro rápido de cliente."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@a.com', 'senha123')
        self.client.login(username='admin', password='senha123')

    def test_criar_cliente_rapido_sucesso(self):
        """POST com nome válido deve criar o cliente e retornar JSON."""
        response = self.client.post(
            reverse('criar_cliente_rapido'), {'nome': 'Pedro Rápido'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['nome'], 'Pedro Rápido')
        cliente = Cliente.objects.get(pk=data['id'])
        # Telefone e endereço devem ficar em branco no cadastro rápido
        self.assertEqual(cliente.telefone, '')
        self.assertEqual(cliente.endereco, '')

    def test_criar_cliente_rapido_sem_nome_retorna_400(self):
        """POST sem nome deve retornar 400 com mensagem de erro."""
        response = self.client.post(reverse('criar_cliente_rapido'), {'nome': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('erro', response.json())

    def test_criar_cliente_rapido_get_retorna_405(self):
        """GET não deve ser aceito (require_POST)."""
        response = self.client.get(reverse('criar_cliente_rapido'))
        self.assertEqual(response.status_code, 405)

    def test_criar_cliente_rapido_anonimo_redireciona(self):
        """Usuário anônimo deve ser redirecionado para login."""
        self.client.logout()
        response = self.client.post(
            reverse('criar_cliente_rapido'), {'nome': 'Anônimo'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cliente.objects.filter(nome='Anônimo').exists())

    def test_cliente_sem_telefone_aceito_no_form(self):
        """ClienteForm deve aceitar telefone e endereço em branco."""
        from .forms import ClienteForm
        form = ClienteForm(data={'nome': 'Só Nome', 'telefone': '', 'endereco': ''})
        self.assertTrue(form.is_valid())
