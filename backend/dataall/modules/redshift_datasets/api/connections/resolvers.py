import logging

from dataall.base.api.context import Context

from dataall.modules.redshift_datasets.services.redshift_connection_service import RedshiftConnectionService

log = logging.getLogger(__name__)


def create_redshift_connection(context: Context, source, input=None):
    # TODO: validate input

    admin_group = input['SamlAdminGroupName']
    uri = input['environmentUri']
    return RedshiftConnectionService.create_redshift_connection(uri=uri, admin_group=admin_group, data=input)

def delete_redshift_connection(context: Context, source, connectionUri):
    return RedshiftConnectionService.delete_redshift_connection(connectionUri)
