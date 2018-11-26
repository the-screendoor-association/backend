class ReceivedCall:
    def __init__(self, date=None, rtime=None, name=None, number=None):
        self.date = date
        self.rtime = rtime
        self.name = name
        self.number = number
        
class StoredCall:
    def __init__(self, datetime=None, name=None, number=None):
        self.datetime = datetime
        self.name = name
        self.number = number
        
    def __str__(self):
        return ';'.join([self.datetime, self.name, self.number])