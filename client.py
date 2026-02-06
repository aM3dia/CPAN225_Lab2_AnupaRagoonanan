# This program was modified by Anupa Ragoonanan (n01423202)

import socket
import argparse
import time
import os
import struct

def run_client(target_ip, target_port, input_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (target_ip, target_port)

    # client waits for ACK. If timeout -> retransmit
    sock.settimeout(1.0) # 1 second timeout

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    try:
        with open(input_file, 'rb') as f:
            file_data = f.read() # read file

        # create chunks with sequence numbers
        chunk_size = 1400 # bytes per packet data
        chunks = [file_data[i:i+chunk_size] for i in range(0, len(file_data), chunk_size)]
        seq_num = 0
        total_chunks = len(chunks)

        while seq_num < total_chunks:
            # Create packet with sequence number header
            header = struct.pack('!I', seq_num) # Network byte order
            packet = header + chunks[seq_num]

            # Send packet
            sock.sendto(packet, server_address)
            print(f"[*] Sent packet seq {seq_num + 1}/{total_chunks}")

            # Wait for ACK
            ack_received = False
            while not ack_received:
                try:
                    ack_data, _ = sock.recvfrom(1024)
                    ack_seq, = struct.unpack('!I', ack_data) # parse ACK sequence number

                    if ack_seq == seq_num:
                        # ACK received for this packet
                        ack_received = True
                        print(f"[*] Received ACK for packet {ack_seq}")
                        seq_num += 1
                    else:
                        print(f"[!] Unexpected ACK packet {ack_seq}, expected {seq_num}.")
                except socket.timeout:
                    print(f"[!] Timeout waiting for ACK for seq {seq_num}. Retransmitting.")
                    sock.sendto(packet, server_address)

        # Send EOF marker
        eof_seq = 0xFFFFFFFF
        eof_header = struct.pack('!I', eof_seq)
        sock.sendto(eof_header, server_address)
        print("[*] Sent EOF marker.")
        
        # Wait for EOF ACK
        eof_ack_received = False
        while not eof_ack_received:
            try:
                ack_data, _ = sock.recvfrom(1024)
                ack_seq, = struct.unpack('!I', ack_data)
                if ack_seq == eof_seq:
                    eof_ack_received = True
                    print("[*] Received ACK for EOF. File transmission complete.")
                else:
                    print(f"[!] Unexpected ACK {ack_seq} while waiting for EOF ACK. Ignoring.")
            except socket.timeout:
                print("[!] Timeout waiting for EOF ACK. Retransmitting EOF.")
                sock.sendto(eof_header, server_address)

        """
            while True:
                # Read a chunk of the file
                chunk = f.read(4096) # 4KB chunks
                
                if not chunk:
                    # End of file reached
                    break

                # Send the chunk
                sock.sendto(chunk, server_address)
                
                # Optional: Small sleep to prevent overwhelming the OS buffer locally
                # (In a perfect world, we wouldn't need this, but raw UDP is fast!)
                time.sleep(0.001)

        # Send empty packet to signal "End of File"
        sock.sendto(b'', server_address)
        print("[*] File transmission complete.")
        """

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Sender")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)