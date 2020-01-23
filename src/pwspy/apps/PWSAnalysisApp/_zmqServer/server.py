import zmq
import threading


class Server(threading.Thread):
    def __init__(self):
        super().__init__()
        print("Server initializing")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5867")
        self.thread = threading.Thread(name="pwspyServerThread")
        self._stopRunMethod = False

    def run(self):
        """This will be run in a separate thread when `start` is called."""
        while not self._stopRunMethod:
            try:
                msg = self.socket.recv_json(zmq.NOBLOCK)  # Wait for a message
            except zmq.ZMQError: #No message has been received.
                continue
            print(f"Received Message: {msg}")
            self.socket.send_json({'ack': True})

    def stop(self):
        self._stopRunMethod = True
        print("Server Trying to stop")
        self.join()
        print("Server Thread Joined")
        self.socket.close()
        self.context.term()
        print("Server successfully closed.")
