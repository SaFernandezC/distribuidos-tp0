from configparser import ConfigParser
import os
import logging

LEN_STRING = 2
LEN_NUMBER = 2
LEN_TYPE = 1
NORMAL_BATCH = 'N'
LAST_BATCH = 'L'
ACK_OK = 0
ACK_ERROR = 1

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

class Protocol:
    def __init__(self):
        config_params = _initialize_config()
        self.max_packet_size = config_params["max_packet_size"]
        self.cant_bytes_len = config_params["cant_bytes_len"]
        self.cant_bytes_ack = config_params["cant_bytes_ack"]
        self.cant_bytes_agency = config_params["cant_bytes_agency"]

    def encode_batch(self, agency, data, last_batch):
        """
        Batch encoder:
        - 1 byte for msg type (NORMAL_BATCH or LAST_BATCH)
        - 2 bytes with agency_id
        - 2 bytes with amount of bets to send
        - Bets data -> 2 bytes with field length and then send the field info
        """
        msg_type = LAST_BATCH if last_batch else NORMAL_BATCH

        payload = bytearray()
        payload += bytes(msg_type, 'latin1')
        payload += len(agency).to_bytes(LEN_STRING, byteorder='big')
        payload += bytes(agency, 'latin1')

        payload += len(data).to_bytes(LEN_NUMBER, byteorder='big')

        for bet in data:
            splited_bet = bet.split(',')
            for item in splited_bet:
                payload += len(item).to_bytes(LEN_STRING, byteorder='big')
                payload += bytes(item, 'latin1')
        return payload

    def read_str(self, skt):
        """
        Read 2 bytes to know the length of the string
        then reads 'size' bytes to get the string
        """
        size_bytes = skt.recv_msg(LEN_STRING)
        size = int.from_bytes(size_bytes, byteorder='big')
        string = skt.recv_msg(size).decode()
        return string

    def read_number(self, skt):
        """
        Reads 2 bytes to get a number
        """
        num = skt.recv_msg(LEN_NUMBER)
        return int.from_bytes(num, byteorder='big')

    def decode_batch(self, skt):
        """
        Reads from socket to decode a batch following
        the rules of encode_batch() function.
        Returns dict {agency: xx, data: [], last_batch: true/false}
        """
        batch_type = skt.recv_msg(LEN_TYPE).decode()
        agency = self.read_str(skt)
        data_len = self.read_number(skt)

        bets = []
        for _ in range(data_len):
            name = self.read_str(skt)
            last_name = self.read_str(skt)
            document = self.read_str(skt)
            birth = self.read_str(skt)
            number = self.read_str(skt)
            bets.append(f"{name},{last_name},{document},{birth},{number}")

        last = True if batch_type == LAST_BATCH else False
        return {"agency":agency , "data": bets, "last_batch": last}

    def _divide_msg(self, bet, bet_size):
        """
        Returns size of packets to send as we can't 
        send more than 8192 bytes per packet
        """
        if bet_size < self.max_packet_size:
            return [bet]
        
        n = self.max_packet_size
        chunks = [bet[i:i+n] for i in range(0, bet_size, n)]
        return chunks
    
    def _send_chunk(self, skt, chunk, chunk_size):
        """
        Send chunk divided into parts that do not
        exceed size limit (8192b)
        """
        divided_chunk = self._divide_msg(chunk, chunk_size)
        for part in divided_chunk:
            skt.send_msg(part)        

    def send_bets(self, skt, agency, data, last_batch):
        """
        Encode batch and sends it using _send_chunk() function
        """
        batch = self.encode_batch(agency, data, last_batch)
        batch_size = len(batch)
        self._send_chunk(skt, batch, batch_size)
        logging.debug(f'action: Batch sended | result: success | agency: {agency} | msg_len: {batch_size}')

    def recv_bets(self, skt): 
        """
        Receive batch of bets, decoding it
        """       
        batch = self.decode_batch(skt)
        logging.debug(f'action: Batch received | result: success | ip: {batch["agency"]} | msg_len: {len(batch)}')
        return batch

    def send_ack(self, skt, status):
        """
        Receives status=true for OK_ACK or status=false for ERROR
        Sends ACK
        """ 
        msg = ACK_OK if status == True else ACK_ERROR
        skt.send_msg(msg.to_bytes(self.cant_bytes_ack, byteorder='big'))
        logging.debug(f'action: Send ack | result: success | ip: {skt.get_addr()} | msg: {status}')

    def recv_ack(self, skt):
        """
        Receives ACK and returns it
        """ 
        ack_bytes = skt.recv_msg(self.cant_bytes_ack)
        ack = int.from_bytes(ack_bytes, byteorder='big')

        response = True if ack == ACK_OK else False
        logging.debug(f'action: Receive ack | result: success | ip: {skt.get_addr()} | msg: {response}')
        return response

    def ask_for_winners(self, skt, agency_id):
        """
        Send msg with 'agency_id' asking for winners
        Then waits until receive winners list
        """ 
        skt.send_msg(agency_id.to_bytes(self.cant_bytes_agency, byteorder='big'))

        winners_size_bytes = skt.recv_msg(self.cant_bytes_agency)
        winners_size = int.from_bytes(winners_size_bytes, byteorder='big')
        winners = skt.recv_msg(winners_size).decode()

        if len(winners) == 0:
             return []
        else: return winners.split(',')

    def recv_ask_for_winners(self, skt):
        """
        Receives ask for winners
        """
        agency_bytes = skt.recv_msg(self.cant_bytes_agency)
        agency = int.from_bytes(agency_bytes, byteorder='big')
        return agency
    
    def send_winners(self, skt, winners):
        """
        Send winners list using _send_chunk() function
        """
        winners = ','.join(winners)
        size = len(winners)
        skt.send_msg(size.to_bytes(self.cant_bytes_agency, byteorder='big'))
        self._send_chunk(skt, bytes(winners, 'latin1'), size)



    
