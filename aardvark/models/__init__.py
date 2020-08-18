from aardvark.plugins import AardvarkPlugin


class AardvarkPersistenceModel(AardvarkPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def create(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def read(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def update(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def delete(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def get_or_create(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def create_or_update(*args, **kwargs):
        raise NotImplementedError()
