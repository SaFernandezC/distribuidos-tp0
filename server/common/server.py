import logging
import signal
from shared.socket import Socket
from shared.protocol import Protocol
from common.utils import Bet, store_bets, load_bets, has_won
import multiprocessing

# Hacerlo config
WORKERS = 3

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

        self.clients_queue = multiprocessing.Queue()
        self.bets_queue = multiprocessing.Queue()
        self.waiting_result_queue = multiprocessing.Queue()

        self._workers = [multiprocessing.Process(target=self._handle_connection,
                                                 args=(self.clients_queue, self.bets_queue, self.waiting_result_queue))
                                                 for i in range(WORKERS)]

        self._bet_writer = multiprocessing.Process(target=self._write_bets,
                                                  args=(self.bets_queue, self.waiting_result_queue))

        self._winner_definer = multiprocessing.Process(target=self._perform_lottery,
                                                  args=(self.waiting_result_queue,))

    def _perform_lottery(self, waiting_result_queue):
        try:
            agencies = {}

            while len(agencies) < self.number_of_clients:
                client_sock = waiting_result_queue.get()
                agency = self.protocol.recv_ask_for_winners(client_sock)
                agencies[agency] = client_sock

            winners = self._define_winners(agencies)
            self._send_winners(agencies, winners)

        except Exception as e:
            logging.error("action: definiendo ganadores | result: fail | error: {}".format(e))
            

    def _write_bets(self, bets_queue, waiting_result_queue):
        while True:
            try:
                client_sock, bets, last_batch = bets_queue.get()
                store_bets(bets)
                if last_batch:
                    waiting_result_queue.put(client_sock)
            except Exception as e:
                logging.error("action: escribiendo apuestas | result: fail | error: {}".format(e))

    def _handle_connection(self, clients_queue, bets_queue, waiting_result_queue):
        while True:
            try:
                client_sock = clients_queue.get()
                batch = self.protocol.recv_bets(client_sock)
                bets, last_batch_received = self.parse_msg(batch)

                bets_queue.put((client_sock, bets, last_batch_received))
                self.protocol.send_ack(client_sock, True)
                
                if not last_batch_received:
                    clients_queue.put(client_sock)

                logging.info(f"action: batch almacenado | result: success | agency: {batch['agency']} | cantidad apuestas: {len(batch['data'])}")
            except Exception as e:
                logging.error("action: handle_connections | result: fail | error: {}".format(e))

    def run(self):
        for worker in self._workers:
            worker.start()

        self._bet_writer.start()
        self._winner_definer.start()

        while self.is_alive:
            client_sock = self.__accept_new_connection()
            if client_sock:
                self.clients_queue.put(client_sock)
            elif self.is_alive:
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
            logging.error("action: stop server | result: fail | error: {}".format(e))
        finally:
            logging.info('Server stopped')  