from shared.socket import Socket
from shared.protocol import Protocol
import logging
import signal
import os

class Client:
    def __init__(self, server_ip, server_port):
        self.agency = os.getenv("CLI_ID", "")
        self.name = os.getenv('NOMBRE', "")
        self.lastname = os.getenv('APELLIDO', "")
        self.document = os.getenv('DOCUMENTO', "")
        self.birthdate = os.getenv('NACIMIENTO', "")
        self.number = os.getenv('NUMERO', "")

        # Initialize client socket
        self.client_socket = Socket()
        self.client_socket.connect(server_ip, server_port)

        # Initialize protocol
        self.protocol = Protocol()

        # self.is_alive = True
        signal.signal(signal.SIGTERM, self._handle_sigterm)


    def _create_bet(self):
        return f"{self.agency},{self.name},{self.lastname},{self.document},{self.birthdate},{self.number}"


    def send_bets(self):

        try:
            bet = self._create_bet()
            self.protocol.send_bet(self.client_socket, bet)
            ack = self.protocol.recv_ack(self.client_socket)
            if(ack):
                logging.info(f'action: apuesta_enviada | result: success | dni: {self.document} | numero: {self.number}')
            else:
                logging.info(f'action: apuesta_enviada | result: fail | dni: {self.document} | numero: {self.number}')
        
        except Exception as e:
            logging.error("action: apuesta_enviada | result: fail | error: {}".format(e)) 
        finally:
            self.stop()


    def _handle_sigterm(self, *args):
        logging.info('SIGTERM received - Shutting client down')
        self.stop()

    def stop(self):
        try:
            self.client_socket.close()
        except OSError as e:
            logging.error("action: stop client | result: fail | error: {e}")
        finally:
            logging.info("action: stop client | result: success")  