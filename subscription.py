from typing import Union, List

class SubscriptionStatus:
    def __init__(
        self,
        js: dict
    ):
        self._js:dict = js
        self.channelName:Union[str|None] = js['channelName'] if 'channelName' in js.keys() else None
        self.event:str = js['event']
        self.pair:List[str] = js['pair']
        self.status:str = js['status']

        self.channelID:Union[int|None] = js['channelID'] if 'channelID' in js.keys() else None
        self.errorMessage:Union[str|None] = js['errorMessage'] if 'errorMessage' in js.keys() else None

    def __repr__(self):
        string:str = f'{self.event}: {self.status} -> {self.channelName}|{self.pair}'
        if self.channelID:
            string += f' ({self.channelID})'
        if self.errorMessage:
            string += f' ({self.errorMessage})'
        return string

