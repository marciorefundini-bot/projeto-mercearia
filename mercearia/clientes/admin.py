from django.contrib import admin
from .models import Cliente, Produto, Fiado

admin.site.register(Cliente)
admin.site.register(Produto)
admin.site.register(Fiado)