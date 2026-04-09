"""
Formulários do app 'clientes'.

Os formulários fazem a validação de dados antes de chegarem ao model.
Regras de negócio mais complexas (ex.: controle de estoque) ficam no model.

Widgets Bootstrap:
  Todos os campos usam classes do Bootstrap 5 para manter consistência visual
  com o restante da interface.
"""

from django import forms
from django.core.validators import MinValueValidator

from .models import Cliente, Produto, Venda


class ClienteForm(forms.ModelForm):
    """
    Formulário de criação e edição de clientes.

    Campos: nome, telefone, endereço.
    """

    class Meta:
        model = Cliente
        fields = ['nome', 'telefone', 'endereco']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000',
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rua, número, bairro',
            }),
        }
        labels = {
            'nome': 'Nome',
            'telefone': 'Telefone',
            'endereco': 'Endereço',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Telefone e endereço são opcionais (blank=True no model).
        # Marcamos required=False aqui para que o formulário de edição
        # também os aceite em branco sem retornar erro de validação.
        self.fields['telefone'].required = False
        self.fields['endereco'].required = False


class ProdutoForm(forms.ModelForm):
    """
    Formulário de criação e edição de produtos.

    Campos: nome, preco, estoque.
    Validações:
      - Preço e estoque não podem ser negativos (min=0 no widget E no validator).
        O widget define o atributo HTML 'min' (validação no navegador);
        o validator garante a rejeição no servidor mesmo se o HTML for contornado.
    """

    class Meta:
        model = Produto
        fields = ['nome', 'preco', 'estoque']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do produto',
            }),
            'preco': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',   # Permite centavos
                'min': '0',       # Validação no navegador (HTML5)
            }),
            'estoque': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',       # Validação no navegador (HTML5)
            }),
        }
        labels = {
            'nome': 'Nome do Produto',
            'preco': 'Preço (R$)',
            'estoque': 'Quantidade em Estoque',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona validators server-side em campos numéricos.
        # O model já possui MinValueValidator, mas adicioná-los aqui garante
        # que a validação aconteça no form.is_valid(), exibindo erros inline
        # antes de qualquer acesso ao banco de dados.
        self.fields['preco'].validators.append(MinValueValidator(0))
        self.fields['estoque'].validators.append(MinValueValidator(0))


class VendaForm(forms.ModelForm):
    """
    Formulário de criação e edição de vendas.

    Campos expostos: tipo, produto, cliente, quantidade.
    Campos NÃO expostos (definidos pela lógica da view/model):
      - valor_unitario: capturado do preço do produto no momento da venda.
      - pago:           definido automaticamente (True para à vista).
      - data:           preenchida pelo auto_now_add do model.

    Validações customizadas (método clean):
      1. Se o tipo for 'fiado', o cliente é obrigatório.
      2. Para novas vendas, verifica se há estoque suficiente antes de salvar.
         (Para edições, a validação de estoque fica no Venda.save() do model,
          pois precisa comparar com a quantidade anterior da venda.)
    """

    class Meta:
        model = Venda
        fields = ['tipo', 'produto', 'cliente', 'quantidade']
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_tipo',     # Usado pelo JS para mostrar/esconder o campo cliente
            }),
            'produto': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_cliente',  # Usado pelo JS para destaque visual
            }),
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',           # Quantidade mínima de 1 unidade (HTML5)
            }),
        }
        labels = {
            'tipo': 'Tipo de Venda',
            'produto': 'Produto',
            'cliente': 'Cliente',
            'quantidade': 'Quantidade',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garante quantidade mínima de 1 também no servidor
        self.fields['quantidade'].validators.append(MinValueValidator(1))
        # empty_label='': substitui os hífens "----------" por string vazia.
        # O Tom Select interpreta a opção vazia como placeholder e exibe
        # o texto configurado no JS ("Digite para pesquisar...").
        self.fields['produto'].empty_label = ''
        self.fields['cliente'].empty_label = ''

    def clean(self):
        """
        Validação cruzada entre campos do formulário.

        Executada após a validação individual de cada campo.
        Verifica regras que dependem de mais de um campo ao mesmo tempo.
        """
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        produto = cleaned_data.get('produto')
        quantidade = cleaned_data.get('quantidade')
        cliente = cleaned_data.get('cliente')

        # Regra 1: fiado exige cliente identificado
        if tipo == Venda.TIPO_FIADO and not cliente:
            self.add_error(
                'cliente',
                'Cliente é obrigatório para vendas a prazo (fiado).',
            )

        # Regra 2: verifica estoque antecipadamente (apenas em novas vendas)
        # Para edições (self.instance.pk existe), o Venda.save() cuida disso,
        # pois precisa considerar a quantidade anterior da venda.
        if produto and quantidade and not self.instance.pk:
            if produto.estoque < quantidade:
                raise forms.ValidationError(
                    f"Estoque insuficiente! '{produto.nome}' tem apenas "
                    f"{produto.estoque} unidade(s) disponíveis."
                )

        return cleaned_data
