import re
from enum import Enum

class Alignment(Enum):
    LEFT = "left"
    RIGHT = "right"
    LEFT_END = "left-end"
    RIGHT_END = "right-end"
    END = "end"
    NONE = "none"
    
    @classmethod
    def has_value(cls, value):
        values = set(item.value for item in cls)
        return value in values 

def remove_capturing_pattern(pattern):
    return re.sub(r"([^\\])[\(\)]", r"\1", pattern)
