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

def process_pattern(pattern):
    pattern = [x.strip() for x in pattern.split('->')]

    if len(pattern) == 1:
        pattern += pattern
    assert len(pattern) == 2
    
    pattern = tuple(choices_dict.get(x, x) for x in pattern)
    
    return pattern

choices_dict = {
        '(D)' : r"\(([\d\s]+)\)", 
        '(D.D)' : r"\(([\d\s]+)\.([\d\s]+)\)", 
        '(C.D)' : r"\(([A-Z\s]+)\.([\d\s]+)\)", 
        '(D,D)' : r"\(([\d\s]+)\)",
        '[D]' : r"\[([\d\s]+)[\]\,\)\-\–]",
        'D.' : r"([\d\s]+)\.",
        '§D' : r"§([\d\s]+)"
    }