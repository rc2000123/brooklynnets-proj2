# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct
import concurrent.futures
import traceback
import time
import hashlib
from threading import Timer

def create_packet(seq_num,ack,fin,segment_data = b''):
    #create headers
    headers = struct.pack('i??', seq_num, ack, fin)
    packed_data = headers + segment_data
    
    #compute the checksum(hash) of the pakcked data
    hash_object = hashlib.md5()
    hash_object.update(packed_data)
    hash_bytes = hash_object.digest()
    
    header_with_hash = struct.pack('i??16s', seq_num, ack, fin,hash_bytes)
    #packed_data_with_hash = header_with_hash  + segment_data
    packed_data_with_hash = header_with_hash + segment_data
    
    return packed_data_with_hash
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
        self.expect_receive = 0
        self.closed = False
        self.header_size = 6 + 16

        self.packets_sent = []
        
        #a dict of the seq number and byte value
        self.buffer = {}
        
        #keep a list of keys(seq number) and acks
        
        self.received_acks = {}
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

        
    def retransmit(self):
        
        
        for i in range(self.base, len(self.packets_sent)):
            self.socket.sendto(self.packets_sent[i], (self.dst_ip, self.dst_port))

            
    def listener(self):
        while not self.closed:
            try:
                data, addr = self.socket.recvfrom()
                
                if data != b'':
                    unpacked_headers = struct.unpack('i??16s', data[:self.header_size])
                    received_segment = data[self.header_size:]
                    
                    # print("unpacked headers: ",unpacked_headers)
                    # print("received_segment: ",received_segment)
                    received_seq_num = unpacked_headers[0]
                    is_ack = unpacked_headers[1]
                    is_fin = unpacked_headers[2]
                    received_hash = unpacked_headers[3]
                    
                    #recreate headers
                    headers = struct.pack('i??', received_seq_num, is_ack, is_fin)
                    packed_data = None
                    packed_data = headers + received_segment
                        
                    #recompute the checksum(hash) of the packed data
                    hash_object = hashlib.md5()
                    hash_object.update(packed_data)
                    recreated_hash = hash_object.digest()
                    
                    # print(recreated_hash)
                    if recreated_hash != received_hash:
                        # print("this hash is corrupt")
                        continue
                    
                    
                    if is_ack:
                        # print("this is an ack")
                        self.received_acks[received_seq_num] = True

                    elif is_fin:
                        # print("this is a fin, sending fin-ack")
                        #headers = struct.pack('i??', received_seq_num, True, True)
                        fin_ack_packet = create_packet(received_seq_num,True,True)
                        self.socket.sendto(fin_ack_packet, (self.dst_ip, self.dst_port))
                        
                    else:
                        
                        # The rest is the list of bytes

                        if received_seq_num in self.buffer:
                            continue

                        
                        
                        # print("received a data packet")
                        
                        self.buffer[received_seq_num] = received_segment
                        # print("sending ack")

                        if received_seq_num != self.expect_receive:
                            val = self.expect_receive - 1

                        else:
                            val = received_seq_num

                        
                        ack_packet = create_packet(received_seq_num,True,False)
                        #headers = struct.pack('i??', received_seq_num, True, False)
                        self.socket.sendto(ack_packet, (self.dst_ip, self.dst_port))
                        
                
            except Exception as e:
                # print("listener died!")
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

        self.base = 0
        t = Timer(0.25, self.retransmit)
        t.start()

        for segment in segmented_bytes:
            
           
            packet_data = create_packet(self.seq_num, False, False, segment)
            
            self.packets_sent.append(packet_data)
            self.socket.sendto(packet_data, (self.dst_ip, self.dst_port))

            
            # timeout = 0.25
            # start_time = time.time()
            # #wait until i get an ack for the packet that I just sent
            if self.base in self.received_acks:
                t.cancel()
                self.base += 1
                t = Timer(0.25, self.retransmit)
                t.start()

            # while self.seq_num not in self.received_acks:
            #     time.sleep(0.01)


            
            self.seq_num += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
    
        
        # this sample code just calls the recvfrom method on the LossySocket
        
        #wait until buffer populates
        #while len(self.receive_buffer) == 0:
        #    continue
        

        #wait until buffer populates
        while self.expect_receive not in self.buffer:
            time.sleep(0.01)
        
        
        #while self.expect_receive not in self.buffer:
        #data = self.buffer[self.expect_receive]
        #unpacked_value = struct.unpack('i', data[:4])

        # The rest is the list of bytes
        #byte_list_unpacked = data[4:]
        
        #print(unpacked_value[0],byte_list_unpacked)
        #self.buffer[unpacked_value[0]] = byte_list_unpacked
    
    
        # For now, I'll just pass the full UDP payload to the app
        
        byte_array = self.buffer.pop(self.expect_receive)
        self.expect_receive += 1
        return byte_array

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.

        #headers = struct.pack('i??', self.seq_num, False, True)
        
        #packed_data = headers
        
        fin_packet = create_packet(self.seq_num,False,True)
        self.socket.sendto(fin_packet, (self.dst_ip, self.dst_port))

        timeout = 0.25
        start_time = time.time()
            #wait until i get an ack for the packet that I just sent
        while self.seq_num not in self.received_acks:
            if time.time() - start_time > timeout:
                self.socket.sendto(fin_packet, (self.dst_ip, self.dst_port))
                start_time = time.time()
            time.sleep(0.01)

        time.sleep(2)
        self.closed = True
        self.socket.stoprecv()
        return
