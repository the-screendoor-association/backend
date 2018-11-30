import executive    

class Call:
    def __init__(self, datetime=None, name=None, number=None):
        self.datetime = datetime
        self.name = name
        self.number = number
        
    def __str__(self):
        return ';'.join([self.datetime, self.name, self.number])

if __name__ == '__main__':
    executive.start()