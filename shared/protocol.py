from configparser import ConfigParser
import os
import logging

def _initialize_config():
    config = ConfigParser(os.environ)
    # If config.ini does not exists original config object is not modified
    path = os.path.dirname(os.path.realpath(__file__))
    configdir = '/'.join([path,'protocol.ini'])
    config.read(configdir)

    config_params = {}
    try:
        config_params["max_packet_size"] = int(os.getenv('MAX_PACKET_SIZE', config["DEFAULT"]["MAX_PACKET_SIZE"]))
        config_params["cant_bytes_len"] = int(os.getenv('CANT_BYTES_LEN', config["DEFAULT"]["CANT_BYTES_LEN"]))
        config_params["cant_bytes_ack"] = int(os.getenv('CANT_BYTES_ACK', config["DEFAULT"]["CANT_BYTES_ACK"]))

    except KeyError as e:
        raise KeyError("Key was not found. Error: {} .Aborting".format(e))
    except ValueError as e:
        raise ValueError("Key could not be parsed. Error: {}. Aborting".format(e))

    return config_params

class Protocol:
    def __init__(self):
        config_params = _initialize_config()
        self.max_packet_size = config_params["max_packet_size"]
        self.cant_bytes_len = config_params["cant_bytes_len"]
        self.cant_bytes_ack = config_params["cant_bytes_ack"]

        self.ack_ok = 0
        self.ack_error = 1
    

    def _divide_msg(self, bet, bet_size):
        if bet_size < self.max_packet_size:
            return bet
        
        n = self.max_packet_size
        chunks = [bet[i:i+n] for i in range(0, bet_size, n)]
        return chunks


    def _size_to_chunks(self, size):
        if size < self.max_packet_size:
            return [size]
        
        chunks_size = []
        while size > 0:
            current_size = size if size < self.max_packet_size else self.max_packet_size
            chunks_size.append(current_size)
            size -= current_size
        
        return chunks_size
    

    def send_bet(self, skt, bet):

        bet_size = len(bet)

        skt.send_msg(bet_size.to_bytes(self.cant_bytes_len, byteorder='big'))

        divided_bet = self._divide_msg(bet, bet_size)
        for part in divided_bet:
            skt.send_msg(bytes(part, 'utf-8'))

        logging.info(f'action: Send bet | result: success | ip: {skt.get_addr()} | msg: {bet}')

    def recv_bet(self, skt):

        bet_size_bytes = skt.recv_msg(4)
        bet_size = int.from_bytes(bet_size_bytes, byteorder='big')

        bet_data = ""
        
        chunks_size = self._size_to_chunks(bet_size)
        for chunk in chunks_size:
            data = skt.recv_msg(chunk)
            bet_data += data.decode()

        logging.info(f'action: Receive bet | result: success | ip: {skt.get_addr()} | msg: {bet_data}')
        return bet_data

    def send_ack(self, skt, status):
        # Receives status=true for ok or status=false for error
        msg = self.ack_ok if status == True else self.ack_error
        skt.send_msg(msg.to_bytes(self.cant_bytes_ack, byteorder='big'))
        logging.info(f'action: Send ack | result: success | ip: {skt.get_addr()} | msg: {msg}')

    def recv_ack(self, skt):
        ack_bytes = skt.recv_msg(self.cant_bytes_ack)
        ack = int.from_bytes(ack_bytes, byteorder='big')

        response = True if ack == self.ack_ok else False
        logging.info(f'action: Receive ack | result: success | ip: {skt.get_addr()} | msg: {ack}')
        return response