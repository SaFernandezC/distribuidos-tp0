from shared.socket import Socket
from shared.protocol import Protocol
import logging
import signal
import os

class Client:
    def __init__(self, server_ip, server_port, bets_per_batch):
        try:
            self.agency = os.getenv("CLI_ID", "")
            self.bets_per_batch = bets_per_batch
            self.client_socket = Socket()
            self.client_socket.connect(server_ip, server_port)
            self.protocol = Protocol()

            signal.signal(signal.SIGTERM, self._handle_sigterm)
        except Exception as e:
            self.stop()
            logging.error("action: create client | result: fail | error: {}".format(e))

    def _ask_for_winners(self):
        """
        Asks for winners to the protocol and then prints them
        """
        winners = self.protocol.ask_for_winners(self.client_socket, int(self.agency))
        logging.info(f'action: consulta_ganadores | result: success | cant_ganadores: {len(winners)} | ganadores: {winners}')

    def send_bets(self, bets_file):
        """
        Iterates until all bets from file are sent.
        Then calls ask_for_winners() function
        """
        finished = False
        try:
            with open(bets_file, encoding='latin1') as file:
                while not finished:
                    finished, batch = self.next_batch(file)
                    self.protocol.send_bets(self.client_socket, self.agency, batch, finished)
                    ack = self.protocol.recv_ack(self.client_socket)
                    if(ack):
                        logging.debug(f'action: apuestas enviadas | result: success | agency: {self.agency} | apuestas: {bets_file}')
                    else:
                        logging.debug(f'action: apuestas enviadas | result: fail | agency: {self.agency} | apuestas: {bets_file}')
                
                logging.info(f'action: apuestas enviadas | result: success | agency: {self.agency}')
            self._ask_for_winners()
        except Exception as e:
            logging.error("action: apuestas enviadas | result: fail | error: {}".format(e)) 
        finally:
            self.stop()

    def next_batch(self, file):
        """
        Reads next bets batch from file.
        Returns bets and True if that is last_batch, else False
        """
        bets = []
        for i in range(self.bets_per_batch):
            line = file.readline().strip()
            if not line:
                return True, bets
            bets.append(line)
        return False, bets

    def _handle_sigterm(self, *args):
        """
        Handles SIGTERM signal
        """
        logging.info('SIGTERM received - Shutting client down')
        self.stop()

    def stop(self):
        """
        Stops the client
        """
        try:
            self.client_socket.close()
            logging.info("action: stop client | result: success")  
        except OSError as e:
            logging.error("action: stop client | result: fail | error: {}".format(e))