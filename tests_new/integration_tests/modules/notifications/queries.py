# TODO: This file will be replaced by using the SDK directly


def mark_notification_read(client, uri):
    query = {
        'operationName': 'markNotificationAsRead',
        'variables': {'notificationUri': uri},
        'query': """
            mutation markNotificationAsRead($notificationUri: String!) {
              markNotificationAsRead(notificationUri: $notificationUri)
            }
                """,
    }
    response = client.query(query=query)
    return response.data.markNotificationAsRead


def delete_notification(client, uri):
    query = {
        'operationName': 'deleteNotification',
        'variables': {'notificationUri': uri},
        'query': """
            mutation deleteNotification($notificationUri: String!) {
              deleteNotification(notificationUri: $notificationUri)
            }
                """,
    }
    response = client.query(query=query)
    return response.data.deleteNotification


def list_notifications(client, filter={}):
    query = {
        'operationName': 'listNotifications',
        'variables': {'filter': filter},
        'query': """
            query listNotifications($filter: NotificationFilter) {
              listNotifications(filter: $filter) {
                count
                page
                pages
                hasNext
                hasPrevious
                nodes {
                  notificationUri
                  message
                  type
                  is_read
                  target_uri
                }
              }
            }
                """,
    }
    response = client.query(query=query)
    return response.data.listNotifications


def count_unread_notificiations(client):
    query = {
        'operationName': 'countUnreadNotifications',
        'variables': {},
        'query': """
            query countUnreadNotifications {
              countUnreadNotifications
            }
                """,
    }
    response = client.query(query=query)
    return response.data.countUnreadNotifications


def count_read_notificiations(client):
    query = {
        'operationName': 'countReadNotifications',
        'variables': {},
        'query': """
            query countReadNotifications {
              countReadNotifications
            }
                """,
    }
    response = client.query(query=query)
    return response.data.countReadNotifications


def count_deleted_notificiations(client):
    query = {
        'operationName': 'countDeletedNotifications',
        'variables': {},
        'query': """
            query countDeletedNotifications {
              countDeletedNotifications
            }
                """,
    }
    response = client.query(query=query)
    return response.data.countDeletedNotifications
