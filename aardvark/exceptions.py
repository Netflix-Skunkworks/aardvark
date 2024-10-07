class AardvarkError(Exception):
    pass


class AccessAdvisorError(AardvarkError):
    pass


class CombineError(AardvarkError):
    pass


class DatabaseError(AardvarkError):
    pass


class RetrieverError(AardvarkError):
    pass
