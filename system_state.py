
class SystemState:
    def __init__(
        self, 
        connectionID:int,
        event:str, 
        status:str, 
        version:str
    ):
        self.connectionID = connectionID
        self.event = event
        self.status = status
        self.version = version

    def __repr__(self):
        return f'{self.event}: {self.status} ({self.version})'

