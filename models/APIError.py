class APIError(Exception):
    def __init__(
        self,
        message: str,
        code: int = 400,
        details: str = "Invalid parameters supplied!",
    ):
        self.message = message
        self.code = code
        self.details = details
