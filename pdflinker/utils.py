import re
from enum import Enum

class Alignment(Enum):
    LEFT = "left"
    RIGHT = "right"
    LEFT_END = "left-end"
    RIGHT_END = "right-end"
    END = "end"
    NONE = "none"
    EXCLUDE = "exclude"
    
    @classmethod
    def has_value(cls, value):
        values = set(item.value for item in cls)
        return value in values 
    
    def __str__(self):
        return self.value

def remove_capturing_pattern(pattern):
    return re.sub(r"^\(([^\?])",r"(?:\1",
        re.sub(r"([^\\])\(([^\?])",r"\1(?:\2", pattern))

    return re.sub(r"^\(","",
        re.sub(r"([^\\])[\(\)]", r"\1", pattern))

def process_pattern(patt):
    if patt in choices_dict:
        patt = choices_dict[patt]
    return patt

choices_dict = {
        '(D)' : r"\(([\d\s]+)\)", 
        '(D.D)' : r"\(([\d\s]+)\.([\d\s]+)\)", 
        '(D,D)' : r"\(([\d\s]+)\)",
        '[D]' : r"\[([\d\s]+)[\]\,\)]"
    }