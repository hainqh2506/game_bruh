"""Room WebSocket / event names. Add a constant here when adding a new command."""


class Client:
    PING = "ping"
    START = "start"
    REMATCH = "rematch"
    GUESS = "guess"


class Server:
    ROOM = "room"
    STARTED = "started"
    GUESS_RESULT = "guess_result"
    PEER_UPDATE = "peer_update"
    PEER_SOLVED = "peer_solved"
    FINISHED = "finished"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
