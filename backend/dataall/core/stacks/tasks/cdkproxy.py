import logging
import os
import sys

from dataall.base.cdkproxy.cdk_cli_wrapper import deploy_cdk_stack, _CDK_CLI_WRAPPER_EXTENSIONS
from dataall.base.loader import load_modules, ImportMode
from dataall.base.db import get_engine

root = logging.getLogger()
root.setLevel(logging.INFO)
if not root.hasHandlers():
    root.addHandler(logging.StreamHandler(sys.stdout))
logger = logging.getLogger(__name__)

load_modules(modes={ImportMode.CDK_CLI_EXTENSION})
logger.warning(f'Loading  _CDK_CLI_WRAPPER_EXTENSIONS {_CDK_CLI_WRAPPER_EXTENSIONS}')


if __name__ == '__main__':
    envname = os.environ.get('envname', 'local')
    engine = get_engine(envname=envname)

    stack_uri = os.getenv('stackUri')
    logger.info(f'Starting deployment task for stack : {stack_uri}')

    deploy_cdk_stack(engine=engine, stackid=stack_uri, app_path='../../base/cdkproxy/app.py')

    logger.info('Deployment task finished successfully')
