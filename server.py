# This program was modified by Anupa Ragoonanan (n01423202)

import socket
import argparse
import struct 
from collections import OrderedDict

def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 2. Bind the socket to the port (0.0.0.0 means all interfaces)
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save each received file as 'received_<ip>_<port>.jpg' based on sender.")
    sock.bind(server_address)

    # Packet reordering
    expected_seq_num = 0
    buffer = OrderedDict() # store out-of-order packets
    received_data = bytearray()

    # 3. Keep listening for new transfers
    try:
        while True:
            data, addr = sock.recvfrom(2048)

            # If we receive an empty packet, it means "End of File"
            if not data:
                continue
            if len(data) < 4:
                continue

            seq_num = struct.unpack('!I', data[:4])[0]
            packet_data = data[4:]

            # check for EOF marker
            if seq_num == 0xFFFFFFFF:
                print(f"[*] End of file signal received from {addr}.")
                # save the file
                if received_data:
                    with open(output_file, 'wb') as f:
                        f.write(received_data)
                    print(f"[*] File saved as '{output_file}'")
                # Send ACK for EOF
                ack_packet = struct.pack('!I', seq_num)
                sock.sendto(ack_packet, addr)
                # reset for next file
                expected_seq_num = 0
                buffer.clear()
                received_data = bytearray()
                continue
                
            # Send ACK for received packet
            ack_packet = struct.pack('!I', seq_num)
            sock.sendto(ack_packet, addr)

            # Process packet based on sequence number
            if seq_num == expected_seq_num:                
                received_data.extend(packet_data)
                expected_seq_num += 1
                
                # 2. VITAL STEP: Check if the *next* packet is already waiting in our buffer
                while expected_seq_num in buffer:
                    print(f"[*] Writing buffered packet seq {expected_seq_num} to file.")
                    buffered_data = buffer.pop(expected_seq_num)
                    received_data.extend(buffered_data) # skip sequence number in buffered packet
                    expected_seq_num += 1
                    
            elif seq_num > expected_seq_num:
                # Packet arrived too early (out of order). Store it for later.
                if seq_num not in buffer:
                    buffer[seq_num] = packet_data
                    print(f"[*] Stored out-of-order packet seq {seq_num} in buffer.")
                else:
                    print(f"[*] Duplicate out-of-order packet seq {seq_num} received. Ignoring.")
            else:
                # Packet is old (duplicate). Ignore it.
                print(f"[*] Duplicate packet seq {seq_num} received. Ignoring.")
                pass
        """
        while True:
            f = None
            sender_filename = None
            reception_started = False
            while True:
                data, addr = sock.recvfrom(4096)
                # Protocol: If we receive an empty packet, it means "End of File"
                if not data:
                    print(f"[*] End of file signal received from {addr}. Closing.")
                    break
                if f is None:
                    print("==== Start of reception ====")
                    ip, sender_port = addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, 'wb')
                    print(f"[*] First packet received from {addr}. File opened for writing as '{sender_filename}'.")
                # Write data to disk
                f.write(data)
                # print(f"Server received {len(data)} bytes from {addr}") # Optional: noisy
            if f:
                f.close()
            print("==== End of reception ====")
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
        """
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
        # save any incomplete file before exiting
        if received_data:
            with open(output_file, 'wb') as f:
                f.write(received_data)
            print(f"[*] Incomplete file saved as '{output_file}'")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()
        print("[*] Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Receiver")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    run_server(args.port, args.output)