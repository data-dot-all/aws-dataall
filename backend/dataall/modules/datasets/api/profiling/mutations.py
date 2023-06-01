from dataall.api import gql
from dataall.modules.datasets.api.profiling.resolvers import start_profiling_run

startDatasetProfilingRun = gql.MutationField(
    name='startDatasetProfilingRun',
    args=[gql.Argument(name='input', type=gql.Ref('StartDatasetProfilingRunInput'))],
    type=gql.Ref('DatasetProfilingRun'),
    resolver=start_profiling_run,
)