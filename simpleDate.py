

class Hour:
    __slots__ = ("seconds", "minutes", "hours")
    def __init__(self, hours:int=0, minutes:int=0, seconds:float=0.) -> None:
        self.seconds:float = float(seconds % 60)
        minutes = int(seconds // 60) + minutes
        self.minutes:int = minutes % 60
        self.hours = (minutes // 60) + hours

    def __add__(self, other:"Hour")->"Hour": return Hour(seconds=self.nbSeconds() + other.nbSeconds())
    def __sub__(self, other:"Hour")->"Hour": return Hour(seconds=self.nbSeconds() - other.nbSeconds())
    
    def __mult__(self, other:float)->"Hour": return Hour(seconds=self.nbSeconds() * other)
    def __truediv__(self, other:float)->"Hour": return Hour(seconds=self.nbSeconds() / other)

    def __neg__(self)->"Hour": return Hour(seconds= -self.nbSeconds())
    def __pos__(self)->"Hour": return Hour(seconds= +self.nbSeconds())

    def nbSeconds(self)->float:
        """the total number of seconds"""
        return float(self.hours * 3600 + self.minutes * 60 + self.seconds)
    
    def __str__(self)->str:
        return f"{self.hours:02}:{self.minutes:02}:{int(self.seconds):02}" \
            + (f".{self.seconds % 1}" if self.seconds % 1 != 0 else "")
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.hours}, {self.minutes}, {self.seconds})"