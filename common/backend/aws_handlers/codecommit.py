from common.aws_handlers.sts import SessionHelper


class CodeCommit:
    def __init__(self):
        pass

    @staticmethod
    def client(AwsAccountId, region):
        session = SessionHelper.remote_session(AwsAccountId)
        return session.client('codecommit', region_name=region)
