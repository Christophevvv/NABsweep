# Generated by Django 2.1.1 on 2019-02-18 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0002_auto_20190212_1557'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalresult',
            name='pred_error_during_anomaly',
            field=models.FloatField(default=0.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresult',
            name='pred_error_no_anomaly',
            field=models.FloatField(default=0.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresultscore',
            name='false_negatives',
            field=models.IntegerField(default=0.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresultscore',
            name='false_positives',
            field=models.IntegerField(default=0.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresultscore',
            name='score',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresultscore',
            name='true_negatives',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='globalresultscore',
            name='true_positives',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
