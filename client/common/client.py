from shared.socket import Socket
from shared.protocol import Protocol
import logging
import signal
import os

class Client:
    def __init__(self, server_ip, server_port, bets_per_batch):
        self.agency = os.getenv("CLI_ID", "")
        self.bets_per_batch = bets_per_batch

        # Initialize client socket
        self.client_socket = Socket()
        self.client_socket.connect(server_ip, server_port)

        # Initialize protocol
        self.protocol = Protocol()

        signal.signal(signal.SIGTERM, self._handle_sigterm)


    def _ask_for_winners(self):
        winners = self.protocol.ask_for_winners(self.client_socket, int(self.agency))
        logging.info(f'action: consulta_ganadores | result: success | cant_ganadores: {len(winners)} | ganadores: {winners}')


    def send_bets(self, bets_file):
        finished = False
        try:
            with open(bets_file) as file:
                while not finished:
                    finished, batch = self.next_batch(file)
                    self.protocol.send_bets(self.client_socket, self.agency, batch, finished)

                    ack = self.protocol.recv_ack(self.client_socket)
                    if(ack):
                        logging.info(f'action: apuestas enviadas | result: success | agency: {self.agency} | apuestas: {bets_file}')
                    else:
                        logging.info(f'action: apuestas enviadas | result: fail | agency: {self.agency} | apuestas: {bets_file}')

            self._ask_for_winners()
        except Exception as e:
            logging.error("action: apuestas enviadas | result: fail | error: {}".format(e)) 
        finally:
            self.stop()


    def next_batch(self, file):
        bets = []
        for i in range(self.bets_per_batch):
            line = file.readline()
            if not line:
                return True, bets
            
            bets.append(line)
        return False, bets


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