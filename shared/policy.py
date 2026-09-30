from enum import Enum

class Risk(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"

def requires_approval(risk: Risk) -> bool:
    return risk in {Risk.WRITE, Risk.DESTRUCTIVE}

def allowed_by_default(risk: Risk) -> bool:
    return risk == Risk.READ
