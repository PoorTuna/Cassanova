class NodeToolStatusUnavailable(Exception):
    def __init__(self, msg: str, return_code: int):
        self.msg = msg
        self.return_code = return_code
        super().__init__(self.msg)
