import socket

class Socket:
    def __init__(self, sock=None, addr=None):
        if not sock:
            self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else: self.skt = sock

        self.addr = addr

    def get_addr(self):
        return self.addr
    
    def bind(self, addr, port):
        self.skt.bind((addr, port))

    def listen(self, listen_backlog):
        self.skt.listen(listen_backlog)

    def accept(self):
        client_skt, addr = self.skt.accept()
        if client_skt:
            return Socket(client_skt, addr)
        else: return None

    def connect(self, addr, port):
        self.skt.connect((addr, port))

    def send_msg(self, msg):
        totalsent = 0
        msg_len = len(msg)
        while totalsent < msg_len:
            sent = self.skt.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent = totalsent + sent

    def recv_msg(self, size):
        chunks = []
        bytes_recd = 0
        while bytes_recd < size:
            chunk = self.skt.recv(size - bytes_recd)
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)

    def close(self):
        self.skt.shutdown(socket.SHUT_RDWR)
        self.skt.close()

    
