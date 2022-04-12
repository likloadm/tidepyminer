#A stratum compatible miniminer
#based in the documentation
#https://slushpool.com/help/#!/manual/stratum-protocol
#2017-2019 Martin Nadal https://martinnadal.eu

import socket
import json
import random
import traceback

import tdc_mine
import time
from multiprocessing import Process, Queue, cpu_count
from numba import cuda # Библиотека Nvidia для работы с GPU

bfh = bytes.fromhex


def hash_decode(x: str) -> bytes:
    return bfh(x)[::-1]


def target_to_bits(target: int) -> int:
    c = ("%066x" % target)[2:]
    while c[:2] == '00' and len(c) > 6:
        c = c[2:]
    bitsN, bitsBase = len(c) // 2, int.from_bytes(bfh(c[:6]), byteorder='big')
    if bitsBase >= 0x800000:
        bitsN += 1
        bitsBase >>= 8
    return bitsN << 24 | bitsBase


def bits_to_target(bits: int) -> int:
    bitsN = (bits >> 24) & 0xff
    if not (0x03 <= bitsN <= 0x20):
        raise Exception("First part of bits should be in [0x03, 0x1d]")
    bitsBase = bits & 0xffffff
    if not (0x8000 <= bitsBase <= 0x7fffff):
        raise Exception("Second part of bits should be in [0x8000, 0x7fffff]")
    return bitsBase << (8 * (bitsN - 3))


def bh2u(x: bytes) -> str:
    """
    str with hex representation of a bytes-like object
    >>> x = bytes((1, 2, 10))
    >>> bh2u(x)
    '01020A'
    """
    return x.hex()


def miner_thread(xblockheader, difficult):
    nonce = random.randint(0, 2 ** 32 - 1)  # job.get('nonce')
    nonce_and_hash = tdc_mine.miner_thread(xblockheader, difficult, nonce)
    return nonce_and_hash


def worker(xblockheader, payload1, payload2, bdiff, sock, number):
    while 1:
        # started = time.time()
        z = miner_thread(xblockheader, bdiff)
        # print(f'{number} thread yay!!! Time:', time.time() - started, 'Diff', difficult)
        print(payload1 + z[:8] + payload2)
        sock.sendall(payload1 + z[:8] + payload2)


def miner(address, host, port, cpu_count=cpu_count(), password='password'):
    print("address:{}".format(address))
    print("host:{} port:{}".format(host, port))
    print("Count threads: {}".format(cpu_count))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("Socket connected")

        sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": ["pytideminer-1.0.0"]}\n')
        lines = sock.recv(1024).decode().split('\n')
        response = json.loads(lines[0])
        sub_details, extranonce1, extranonce2_size = response['result']
        print(response)
        extranonce2 = '00' * extranonce2_size
        sock.sendall(b'{"params": ["' + address.encode() + b'", "' + password.encode() + b'"], "id": 2, "method": "mining.authorize"}\n')
        print("Mining authorize")

        procs = []
        count = cpu_count
        print("start mining")
        new_time = time.time()
        count_shares = 0
        global_count_share = 0
        global_count_success_share = 0
        difficult = 0.5

        while True:
            response = sock.recv(2024).decode()
            responses = [json.loads(res) for res in response.split('\n') if len(res.strip()) > 0]
            for response in responses:
                if response['id'] == 4 and not response['error']:
                    count_shares += 1
                    global_count_share += 1
                    global_count_success_share += 1
                    print(f"accepted: {global_count_success_share}/{global_count_share} ({round(global_count_success_share/global_count_share*100)}%) (yay!!!)")

                elif response['id'] == 4 and response['error']:
                    global_count_share += 1
                    print("boooo", response['error'])

                elif response['id'] == 2 and not response['error']:
                    print("Authorize successful!!!")

                elif response['id'] == 2 and response['error']:
                    print("Authorize error!!!", response['error'])

                # get rid of empty lines
                elif response['method'] == 'mining.set_difficulty':
                    old_diff = difficult
                    difficult = response['params'][0]
                    bdiff = bytes(str(difficult), "UTF-8")
                    print("New stratum difficulty: ", difficult)

                elif response['method'] == 'mining.notify':
                    job_id, prevhash, coinb1, coinb2, merkle_branch, \
                    version, nbits, ntime, clean_jobs = response['params']

                    d = ''

                    for h in merkle_branch:
                        d += h

                    merkleroot_1 = tdc_mine.sha256d_str(coinb1.encode('utf8'), extranonce1.encode('utf8'),
                                                        extranonce2.encode('utf8'), coinb2.encode('utf8'), d.encode('utf8'))

                    xblockheader0 = version + prevhash + merkleroot_1.decode('utf8') + ntime + nbits
                    print("Mining notify")
                    for proc in procs:
                        proc.terminate()

                    procs = []
                    old_time = new_time
                    new_time = time.time()

                    xnonce = "00000000"
                    xblockheader = (xblockheader0 + xnonce).encode('utf8')
                    payload1 = bytes(
                        '{"params": ["' + "address" + '", "' + job_id + '", "' + extranonce2 + '", "' + ntime + '", "',
                        "UTF-8")
                    payload2 = bytes('"], "id": 4, "method": "mining.submit"}\n', "UTF-8")

                    for number in range(count):
                        proc = Process(target=worker, args=(xblockheader, payload1, payload2, bdiff, sock, number + 1))
                        proc.daemon = True
                        procs.append(proc)
                        proc.start()

                    if count_shares:
                        hashrate = count_shares * (old_diff / 65536) * 2 ** 32 / (new_time-old_time)
                        print(f"Found {count_shares} shares in {round(new_time-old_time)} seconds at diff", old_diff)
                        print(f"Current Hashrate:", round(hashrate), "H/s")
                        print(f"Recommended diff:", round((count_shares*10/(new_time-old_time))*old_diff, 2))
                        old_diff = difficult
                        count_shares = 0

    except KeyboardInterrupt:
        for proc in procs:
            proc.terminate()
        sock.close()
    except:
        print(traceback.format_exc())
        try:
            for proc in procs:
                proc.terminate()
        except:
            pass
        try:
            sock.close()
        except:
            pass
        print("Connection refused, restart after 30 s")
        time.sleep(30)
        miner(address, host, port, cpu_count, password)



if __name__ == "__main__":
    import argparse
    import sys

    # Parse the command line
    parser = argparse.ArgumentParser(description="PyMiner is a Stratum CPU mining client. "
                                                 "If you like this piece of software, please "
                                                 "consider supporting its future development via "
                                                 "donating to one of the addresses indicated in the "
                                                 "README.md file")

    parser.add_argument('-o', '--url', default="pool.tidecoin.exchange:3032", help='mining server url (eg: pool.tidecoin.exchange:3033)')
    parser.add_argument('-u', '--user', dest='username', default='TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw.default', help='username for mining server',
                        metavar="USERNAME")
    parser.add_argument('-t', '--threads', dest='threads', default=cpu_count(), help='count threads',
                        metavar="USERNAME")
    parser.add_argument('-p', '--password', dest='password', default='password', help='password',
                        metavar="USERNAME")

    options = parser.parse_args(sys.argv[1:])

    miner(options.username, options.url.split(":")[0], int(options.url.split(":")[1]), int(options.threads), options.password)
