class WS1IntegrationException(Exception):
    """
    WorkMail/WS1 integration exception.

    It is raised when WS1 event can't be handled.
    """
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code
