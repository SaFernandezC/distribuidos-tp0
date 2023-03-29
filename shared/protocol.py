from configparser import ConfigParser
import os
import logging
import json

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
        config_params["cant_bytes_agency"] = int(os.getenv('CANT_BYTES_AGENCY', config["DEFAULT"]["CANT_BYTES_AGENCY"]))

    except KeyError as e:
        raise KeyError("Key was not found. Error: {} .Aborting".format(e))
    except ValueError as e:
        raise ValueError("Key could not be parsed. Error: {}. Aborting".format(e))

    return config_params


def encode_batch(agency, data, last_batch):
    return json.dumps({"agency":agency, "data":data, "last_batch":last_batch})

def decode_batch(batch):
    return json.loads(batch)


class Protocol:
    def __init__(self):
        config_params = _initialize_config()
        self.max_packet_size = config_params["max_packet_size"]
        self.cant_bytes_len = config_params["cant_bytes_len"]
        self.cant_bytes_ack = config_params["cant_bytes_ack"]
        self.cant_bytes_agency = config_params["cant_bytes_agency"]

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
    
    def _recv_chunk(self, skt, msg_len):
        chunks_size = self._size_to_chunks(msg_len)
        batch = ""
        for chunk in chunks_size:
            data = skt.recv_msg(chunk)
            batch += data.decode()
        return batch
    
    def _send_chunk(self, skt, chunk, chunk_size):
        divided_chunk = self._divide_msg(chunk, chunk_size)
        for part in divided_chunk:
            skt.send_msg(bytes(part, 'utf-8'))        

    def send_bets(self, skt, agency, data, last_batch):
        batch = encode_batch(agency, data, last_batch)

        batch_size = len(batch)
        skt.send_msg(batch_size.to_bytes(self.cant_bytes_len, byteorder='big'))

        self._send_chunk(skt, batch, batch_size)
        logging.debug(f'action: Batch sended | result: success | agency: {agency} | msg_len: {batch_size}')


    def recv_bets(self, skt):
        batch_size_bytes = skt.recv_msg(self.cant_bytes_len)
        batch_size = int.from_bytes(batch_size_bytes, byteorder='big')

        batch = self._recv_chunk(skt, batch_size)
        batch = decode_batch(batch)
        logging.debug(f'action: Batch received | result: success | ip: {batch["agency"]} | msg_len: {batch_size}')
        return batch

    def send_ack(self, skt, status):
        # Receives status=true for ok or status=false for error
        msg = self.ack_ok if status == True else self.ack_error
        skt.send_msg(msg.to_bytes(self.cant_bytes_ack, byteorder='big'))
        logging.debug(f'action: Send ack | result: success | ip: {skt.get_addr()} | msg: {status}')

    def recv_ack(self, skt):
        ack_bytes = skt.recv_msg(self.cant_bytes_ack)
        ack = int.from_bytes(ack_bytes, byteorder='big')

        response = True if ack == self.ack_ok else False
        logging.debug(f'action: Receive ack | result: success | ip: {skt.get_addr()} | msg: {response}')
        return response

    def ask_for_winners(self, skt, agency_id):
        skt.send_msg(agency_id.to_bytes(self.cant_bytes_agency, byteorder='big'))

        winners_size_bytes = skt.recv_msg(self.cant_bytes_agency)
        winners_size = int.from_bytes(winners_size_bytes, byteorder='big')
        winners = self._recv_chunk(skt, winners_size)
        if len(winners) == 0: return []
        return winners.split(',')

    def recv_ask_for_winners(self, skt):
        agency_bytes = skt.recv_msg(self.cant_bytes_agency)
        agency = int.from_bytes(agency_bytes, byteorder='big')
        return agency
    
    def send_winners(self, skt, winners):
        winners = ','.join(winners)
        size = len(winners)
        skt.send_msg(size.to_bytes(self.cant_bytes_agency, byteorder='big'))
        self._send_chunk(skt, winners, size)



    
