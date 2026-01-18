"""Django app configuration for RMA Automation plugin."""

from django.apps import AppConfig


class RMAAutomationConfig(AppConfig):
    """App configuration for the RMA Automation plugin."""

    name = 'inventree_rma_plugin'
    verbose_name = 'RMA Automation'
    default_auto_field = 'django.db.models.AutoField'
