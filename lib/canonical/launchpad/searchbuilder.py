__metaclass__ = type

# constants for use in search criteria
NULL = "NULL"

class any:
    def __init__(self, *query_values):
        self.query_values = query_values
