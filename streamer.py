# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct
import concurrent.futures
import traceback
import time

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
        self.closed = False
        self.header_size = 6
        
        #a dict of the seq number and byte value
        self.buffer = {}
        
        #keep a list of keys(seq number) and acks
        
        self.recived_acks = {}
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def listener(self):
        while not self.closed:
            try:
                data, addr = self.socket.recvfrom()
                if data != b'':
                    #unpacked_value = struct.unpack('i', data[:4])
                    
                    #print(data[4])
                    #unpacked_ack = struct.unpack('?', data[4])
                    #print(unpacked_ack)
                    
                    unpacked_headers = struct.unpack('i??', data[:self.header_size])
                    received_seq_num = unpacked_headers[0]
                    is_ack = unpacked_headers[1]
                    is_fin = unpacked_headers[2]
                    print(received_seq_num,is_ack,is_fin)
                    
                    
                    if is_ack:
                        print("this is an ack")
                        self.recived_acks[received_seq_num] = True
                    else:
                        
                        # The rest is the list of bytes
                        print("this is a data packet")
                        byte_list_unpacked = data[self.header_size:]
                        self.buffer[received_seq_num] = byte_list_unpacked
                        print("sending ack")
                        headers = struct.pack('i??', received_seq_num, True, False)
                        self.socket.sendto(headers, (self.dst_ip, self.dst_port))
                        
                
            except Exception as e:
                print("listener died!")
                print(e)
                traceback.print_exc()

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # for now I'm just sending the raw application-level data in one UDP payload
        segmented_bytes = []
        
        
        
        while (len(data_bytes) > 1472 - self.header_size):
            new_segment = data_bytes[:1472 - self.header_size]
            segmented_bytes.append(new_segment)
            data_bytes = data_bytes[1472 - self.header_size:]
        
        if len(data_bytes) > 0:
            segmented_bytes.append(data_bytes)
        
        for segment in segmented_bytes:
            #packed_value = struct.pack('i', self.seq_num)
            #is_ack_value = struct.pack("?", False)

            
            headers = struct.pack('i??', self.seq_num, False, False)
            
            packed_data = headers + segment
            self.socket.sendto(packed_data, (self.dst_ip, self.dst_port))
            
            
            #wait until i get an ack for the packet that I just sent
            while self.seq_num not in self.recived_acks:
                time.sleep(0.01)
            
            self.seq_num += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
    
        
        # this sample code just calls the recvfrom method on the LossySocket
        
        #wait until buffer populates
        #while len(self.receive_buffer) == 0:
        #    continue
        

        #wait until buffer populates
        while self.expect_recieve not in self.buffer:
            time.sleep(0.01)
        
        
        #while self.expect_recieve not in self.buffer:
        #data = self.buffer[self.expect_recieve]
        #unpacked_value = struct.unpack('i', data[:4])

        # The rest is the list of bytes
        #byte_list_unpacked = data[4:]
        
        #print(unpacked_value[0],byte_list_unpacked)
        #self.buffer[unpacked_value[0]] = byte_list_unpacked
    
    
        # For now, I'll just pass the full UDP payload to the app
        
        byte_array = self.buffer.pop(self.expect_recieve)
        self.expect_recieve += 1
        return byte_array

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.closed = True
        self.socket.stoprecv()
