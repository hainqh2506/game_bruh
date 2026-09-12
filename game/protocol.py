"""Room WebSocket / event names. Add a constant here when adding a new command."""


class Client:
    PING = "ping"
    START = "start"
    REMATCH = "rematch"
    GUESS = "guess"
    NEXT_ROUND = "next_round"
    REACTION = "reaction"


class Server:
    ROOM = "room"
    STARTED = "started"
    GUESS_RESULT = "guess_result"
    PEER_UPDATE = "peer_update"
    PEER_SOLVED = "peer_solved"
    ROUND_FINISHED = "round_finished"
    FINISHED = "finished"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    REACTION = "reaction"
