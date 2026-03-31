from django import forms
from .models import Cliente, Produto, Venda


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'telefone', 'endereco']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua, número, bairro'}),
        }
        labels = {
            'nome': 'Nome',
            'telefone': 'Telefone',
            'endereco': 'Endereço',
        }


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'preco', 'estoque']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do produto'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'estoque': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'nome': 'Nome do Produto',
            'preco': 'Preço (R$)',
            'estoque': 'Quantidade em Estoque',
        }


class VendaForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ['tipo', 'produto', 'cliente', 'quantidade']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select', 'id': 'id_cliente'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
        labels = {
            'tipo': 'Tipo de Venda',
            'produto': 'Produto',
            'cliente': 'Cliente',
            'quantidade': 'Quantidade',
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        produto = cleaned_data.get('produto')
        qtd = cleaned_data.get('quantidade')
        cliente = cleaned_data.get('cliente')

        if tipo == Venda.TIPO_FIADO and not cliente:
            self.add_error('cliente', 'Cliente é obrigatório para vendas a prazo (fiado).')

        if produto and qtd and not self.instance.pk:
            if produto.estoque < qtd:
                raise forms.ValidationError(
                    f"Estoque insuficiente! '{produto.nome}' tem apenas {produto.estoque} unidade(s)."
                )
        return cleaned_data
