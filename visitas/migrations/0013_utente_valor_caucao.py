from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ("visitas", "0012_pagamentomensalidade"),
]

    operations = [
        migrations.AddField(
            model_name="utente",
            name="valor_caucao",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text=(
                    "Valor administrativo da caução. Não altera o saldo "
                    "pessoal nem o cálculo das mensalidades."
                ),
                max_digits=10,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.00")
                    )
                ],
                verbose_name="Valor da caução",
            ),
        ),
    ]
