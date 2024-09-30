import time
from tests_new.integration_tests.utils import poller


class AthenaClient:
    def __init__(self, session, region):
        self._client = session.client('athena', region_name=region)
        self._region = region

    def _run_query(self, query, workgroup='primary', output_location=None):
        if output_location:
            result = self._client.start_query_execution(
                QueryString=query, ResultConfiguration={'OutputLocation': output_location}
            )
        else:
            result = self._client.start_query_execution(QueryString=query, WorkGroup=workgroup)
        return result['QueryExecutionId']

    @poller(check_success=lambda state: state not in ['QUEUED', 'RUNNING'], timeout=600, sleep_time=5)
    def _wait_for_query(self, query_id):
        result = self._client.get_query_execution(QueryExecutionId=query_id)
        return result['QueryExecution']['Status']['State']

    def execute_query(self, query, workgroup='primary', output_location=None):
        q_id = self._run_query(query, workgroup, output_location)
        return self._wait_for_query(q_id)

    def list_work_groups(self):
        result = self._client.list_work_groups()
        return [x['Name'] for x in result['WorkGroups']]

    def get_env_work_group(self, env_name):
        workgroups = self.list_work_groups()
        for workgroup in workgroups:
            if env_name in workgroup:
                return workgroup
        return workgroups[0] if workgroups else None
