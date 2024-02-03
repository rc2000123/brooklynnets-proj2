# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.seq_num = 0
        self.expect_recieve = 0
        
        #a dict of the seq number and byte value
        self.buffer = {}
        

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # for now I'm just sending the raw application-level data in one UDP payload
        segmented_bytes = []
        while (len(data_bytes) > 1472 - 4):
            new_segment = data_bytes[:1472 - 4]
            segmented_bytes.append(new_segment)
            data_bytes = data_bytes[1472 - 4:]
        
        if len(data_bytes) > 0:
            segmented_bytes.append(data_bytes)
        
        for segment in segmented_bytes:
            packed_value = struct.pack('i', self.seq_num)
            packed_data = packed_value + segment
            self.socket.sendto(packed_data, (self.dst_ip, self.dst_port))
            self.seq_num += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        
        # this sample code just calls the recvfrom method on the LossySocket
        
        while self.expect_recieve not in self.buffer:
            data, addr = self.socket.recvfrom()
            
            unpacked_value = struct.unpack('i', data[:4])

            # The rest is the list of bytes
            byte_list_unpacked = data[4:]
            
            print(unpacked_value[0],byte_list_unpacked)
            self.buffer[unpacked_value[0]] = byte_list_unpacked
        
        # For now, I'll just pass the full UDP payload to the app
        
        byte_array = self.buffer.pop(self.expect_recieve)
        self.expect_recieve += 1
        return byte_array

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
