import logging
import signal
from shared.socket import Socket
from shared.protocol import Protocol
from common.utils import Bet, store_bets, load_bets, has_won
import multiprocessing

WORKERS = 3

class Server:
    def __init__(self, port, listen_backlog, number_of_clients):
        self._server_socket = Socket()
        self._server_socket.bind('', port)
        self._server_socket.listen(listen_backlog)
        self.number_of_clients = number_of_clients
        
        self.is_alive = True
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        self.protocol = Protocol()

        self.clients_queue = multiprocessing.Queue()
        self.bets_queue = multiprocessing.Queue()
        self.waiting_result_queue = multiprocessing.Queue()

        self._workers = [multiprocessing.Process(target=self._handle_connection,
                                                 args=(self.clients_queue, self.bets_queue))
                                                 for i in range(WORKERS)]

        self._bet_writer = multiprocessing.Process(target=self._write_bets,
                                                  args=(self.bets_queue, self.waiting_result_queue))

        self._winner_definer = multiprocessing.Process(target=self._perform_lottery,
                                                  args=(self.waiting_result_queue,))

    def _perform_lottery(self, waiting_result_queue):
        """
        Lottery process: loops getting clients from waiting_result_queue until all clients
        finished sending bets.
        Then defines winners and sends winners to clients
        """
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
        """
        Write bets process: takes a batch of bets from bets_queue, stores those bets,
        if that was the last batch of that agency pushes that agency into waiting_result_queue
        """
        while True:
            try:
                client_sock, bets, last_batch = bets_queue.get()
                store_bets(bets)
                if last_batch:
                    waiting_result_queue.put(client_sock)
            except Exception as e:
                logging.error("action: escribiendo apuestas | result: fail | error: {}".format(e))

    def _handle_connection(self, clients_queue, bets_queue):
        """
        Workers process: Takes clients from clients_queue, receives one bets batch from that
        client, pushes that batch to bets_queue then sends ack to client.
        If that was NOT the last batch pushes the client back to clients_queue to
        repite the process.
        Processing is done by batch and not by client.
        """
        while True:
            try:
                client_sock = clients_queue.get()
                batch = self.protocol.recv_bets(client_sock)
                bets, last_batch_received = self.parse_msg(batch)

                bets_queue.put((client_sock, bets, last_batch_received))
                self.protocol.send_ack(client_sock, True)
                
                if not last_batch_received:
                    clients_queue.put(client_sock)
                else:
                    logging.info(f"action: all bets received from agency | result: success | agency: {batch['agency']}")

                logging.debug(f"action: batch almacenado | result: success | agency: {batch['agency']} | cantidad apuestas: {len(batch['data'])}")
            except Exception as e:
                logging.error("action: handle_connections | result: fail | error: {}".format(e))

    def run(self):
        """
        Main process: starts other processes and iterate accepting new clients.
        After accepting a new client pushes it to clients queue
        """
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
        """
        Calls protocol to send winners. Closes clients sockets
        """
        for id in clients.keys():
            self.protocol.send_winners(clients[id], winners[id])
            clients[id].close()

    def _define_winners(self, clients):
        """
        Defines winners per agency
        """
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
        """"
        Parses bets received from protocol
        """
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
        logging.info('action: accept_connections | result: in_progress')
        c = self._server_socket.accept()
        addr = c.get_addr()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c

    def _handle_sigterm(self, *args):
        """
        Handles SIGTERM signal
        """
        logging.info('SIGTERM received - Shutting server down')
        self.stop()

    def stop(self):
        """
        Stops the server
        """
        self.is_alive = False
        try:
            self._server_socket.close()
            for worker in self._workers:
                worker.join()
            self._bet_writer.join()
            self._winner_definer.join()
        except OSError as e:
            logging.error("action: stop server | result: fail | error: {}".format(e))
        finally:
            logging.info('Server stopped')  