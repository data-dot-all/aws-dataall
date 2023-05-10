"""
DAO layer that encapsulates the logic and interaction with the database for worksheets
"""
from sqlalchemy import or_, and_
from sqlalchemy.orm import Query

from dataall.core.group.services.group_resource_manager import GroupResource
from dataall.db import paginate
from dataall.modules.worksheets.db.models import Worksheet, WorksheetShare, WorksheetQueryResult


class WorksheetRepository(GroupResource):
    """DAO layer for worksheets"""
    _DEFAULT_PAGE = 1
    _DEFAULT_PAGE_SIZE = 10

    def count_resources(self, session, environment, group_uri) -> int:
        return (
            session.query(WorksheetQueryResult)
            .filter(
                WorksheetQueryResult.AwsAccountId == environment.AwsAccountId
            )
            .count()
        )

    def find_worksheet_by_uri(session, uri) -> Worksheet:
        return session.query(Worksheet).get(uri)
    
    def find_worksheet_share_by_uri(session, uri) -> WorksheetShare:
        return session.query(WorksheetShare).get(uri)
    
    def query_user_worksheets(session, username, groups, filter) -> Query:
        query = session.query(Worksheet).filter(
            or_(
                Worksheet.owner == username,
                Worksheet.SamlAdminGroupName.in_(groups),
            )
        )
        if filter and filter.get('term'):
            query = query.filter(
                or_(
                    Worksheet.label.ilike('%' + filter.get('term') + '%'),
                    Worksheet.description.ilike('%' + filter.get('term') + '%'),
                    Worksheet.tags.contains(f"{{{filter.get('term')}}}"),
                )
            )
        return query

    def paginated_user_worksheets(
        session, username, groups, uri, data=None, check_perm=None
    ) -> dict:
        return paginate(
            query=WorksheetRepository.query_user_worksheets(session, username, groups, data),
            page=data.get('page', WorksheetRepository._DEFAULT_PAGE),
            page_size=data.get('pageSize', WorksheetRepository._DEFAULT_PAGE_SIZE),
        ).to_dict()
    
    @classmethod
    def get_worksheet_share(session, uri, data) -> WorksheetShare:
        return (
            session.query(WorksheetShare)
            .filter(
                and_(
                    WorksheetShare.worksheetUri == uri,
                    WorksheetShare.principalId == data.get('principalId'),
                    WorksheetShare.principalType == data.get('principalType'),
                )
            )
            .first()
        )
