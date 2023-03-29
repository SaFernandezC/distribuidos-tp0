import logging
import signal
from shared.socket import Socket
from shared.protocol import Protocol
from common.utils import Bet, store_bets, load_bets, has_won

class Server:
    def __init__(self, port, listen_backlog, number_of_clients):
        # Initialize server socket
        self._server_socket = Socket()
        self._server_socket.bind('', port)
        self._server_socket.listen(listen_backlog)
        self.number_of_clients = number_of_clients

        self.protocol = Protocol()

        self.is_alive = True
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        clients = {}

        while self.is_alive and len(clients) < self.number_of_clients:
            client_sock = self.__accept_new_connection()
            processed_client = self.__handle_client_connection(client_sock)   

            clients[processed_client] = client_sock   

        winners = self._define_winners(clients)
        self._send_winners(clients, winners)
        self.stop()


    def _send_winners(self, clients, winners):
        for id in clients.keys():
            self.protocol.send_winners(clients[id], winners[id])
            clients[id].close()

    def _define_winners(self, clients):
        bets = load_bets()

        winners = {}
        for agency in clients.keys():
            winners[agency] = []

        for bet in bets:
            if has_won(bet):
                winners[bet.agency].append(bet.document)

        logging.info(f"action: sorteo | result: success")
        return winners


    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            last_batch_received = False
            while not last_batch_received:
                batch = self.protocol.recv_bets(client_sock)
                bets, last_batch_received = self.parse_msg(batch)
                store_bets(bets)
                self.protocol.send_ack(client_sock, True)
                logging.info(f"action: batch almacenado | result: success | agency: {batch['agency']} | cantidad apuestas: {len(batch['data'])}")

        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            agency = self.protocol.recv_ask_for_winners(client_sock)
            return agency
            # client_sock.close()


    def parse_msg(self, msg):
        bets = []
        for bet in msg["data"]:
            splitted_string = bet.split(',')
            new_bet = Bet(msg["agency"], splitted_string[0], splitted_string[1],
                        splitted_string[2], splitted_string[3], splitted_string[4])
            bets.append(new_bet)
        
        return bets, msg["last_batch"]
        

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        c = self._server_socket.accept()
        addr = c.get_addr()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c

    def _handle_sigterm(self, *args):
        logging.info('SIGTERM received - Shutting server down')
        self.stop()

    def stop(self):
        self._server_running = False
        try:
            self._server_socket.close()
        except OSError as e:
            logging.error("action: stop server | result: fail | error: {e}")
        finally:
            logging.info('Server stopped')  