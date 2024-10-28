from dataall.core.resource_threshold.db.resource_threshold_models import ResourceThreshold
from sqlalchemy import and_
from datetime import date


class ResourceThresholdRepository:
    @staticmethod
    def get_count_today(session, username, action_type):
        amount = (
            session.query(ResourceThreshold.count)
            .filter(
                and_(
                    ResourceThreshold.username == username,
                    ResourceThreshold.actionType == action_type,
                    ResourceThreshold.date == date.today(),
                )
            )
            .scalar()
        )
        return amount if amount else 0

    @staticmethod
    def add_entry(session, username, action_type):
        user_entry = ResourceThresholdRepository._get_user_entry(session, username, action_type)
        if user_entry:
            session.query(ResourceThreshold).filter(
                and_(
                    ResourceThreshold.username == username,
                    ResourceThreshold.actionType == action_type,
                )
            ).update({ResourceThreshold.count: 1, ResourceThreshold.date: date.today()}, synchronize_session=False)
            session.commit()
        else:
            action_entry = ResourceThreshold(username=username, actionType=action_type)
            session.add(action_entry)
            session.commit()

    @staticmethod
    def increment_count(session, username, action_type):
        session.query(ResourceThreshold).filter(
            and_(
                ResourceThreshold.username == username,
                ResourceThreshold.actionType == action_type,
                ResourceThreshold.date == date.today(),
            )
        ).update({ResourceThreshold.count: ResourceThreshold.count + 1}, synchronize_session=False)
        session.commit()

    @staticmethod
    def _get_user_entry(session, username, action_type):
        entry = (
            session.query(ResourceThreshold)
            .filter(and_(ResourceThreshold.username == username, ResourceThreshold.actionType == action_type))
            .first()
        )
        return entry
