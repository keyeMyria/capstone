# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-05 17:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cap', '0002_auto_20170627_2215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='casexml',
            name='volume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_xmls', to='cap.VolumeXML'),
        ),
        migrations.AlterField(
            model_name='pagexml',
            name='volume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_xmls', to='cap.VolumeXML'),
        ),
    ]
