#A stratum compatible miniminer
#based in the documentation
#https://slushpool.com/help/#!/manual/stratum-protocol
#2017-2019 Martin Nadal https://martinnadal.eu

import socket
import json
import hashlib
import binascii
from pprint import pprint
import time
import random
import tdc_mine
from multiprocessing import Process, Queue


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

def hash_encode(x: bytes) -> str:
    return x[::-1]

def worker(q, sock):
    started = time.time()
    hash_count = 0
    while 1:
        job = q.get()
        xblockheader0 = job.get('xblockheader0')
        job_id = job.get('job_id')
        extranonce2 = job.get('extranonce2')
        ntime = job.get("ntime")
        difficult = job.get('difficult')
        nonce = job.get('nonce')
        address = job.get('address')
        print(job)
        while 1:
            xnonce = hex(nonce)[2:].zfill(8)
            xblockheader = xblockheader0 + xnonce

            nonce_and_hash = tdc_mine.miner_thread(xblockheader.encode('utf8'), bytes(str(difficult), "utf-8"), nonce)
            z = nonce_and_hash.decode('utf-8').split(',')

            print('success!!')
            print('success!!', address, job_id, ntime, z[0])
            payload = '{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 \
                      + '", "' + ntime + '", "' + z[0] + '"], "id": 4, "method": "mining.submit"}\n'
            sock.sendall(bytes(payload, "UTF-8"))
            nonce += 1
            if not q.empty():
                break

bfh = bytes.fromhex


def miner():
    address = 'TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw.upgrade'

    host = 'pool.tidecoin.exchange'
    port = 3033

    print("address:{}".format(address))
    print("host:{} port:{}".format(host, port))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    # server connection
    sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
    lines = sock.recv(1024).decode().split('\n')
    response = json.loads(lines[0])
    sub_details, extranonce1, extranonce2_size = response['result']
    print(sub_details, extranonce1, extranonce2_size)
    # authorize workers
    sock.sendall(b'{"params": ["' + address.encode() + b'", "password"], "id": 2, "method": "mining.authorize"}\n')

    # we read until 'mining.notify' is reached

    q = Queue()
    proc = Process(target=worker, args=(q, sock))
    proc.daemon = True
    proc.start()

    try:
        while True:
            response = b''

            comeback = sock.recv(2024)
            response += comeback
            print(comeback)

            # get rid of empty lines
            if b'mining.set_difficulty' in response:
                diff = [json.loads(res) for res in response.decode().split('\n') if
                        len(res.strip()) > 0 and 'mining.set_difficulty' in res]
                difficult = diff[0]['params'][0]
                znonce = random.randint(0, 2 ** 32 - 1)

            if (b'mining.notify' in response):
                responses = [json.loads(res) for res in response.decode().split('\n') if
                             len(res.strip()) > 0 and 'mining.notify' in res]
                pprint(responses)

                job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs \
                    = responses[0]['params']
                target = bits_to_target(target_to_bits(int(nbits, 16)))
                d = ''
                print('nbits:{} target:{}\n'.format(nbits, target))

                for h in merkle_branch:
                    d += h
                extranonce2 = '00' * extranonce2_size
                merkleroot_1 = tdc_mine.sha256d_str(coinb1.encode('utf8'), extranonce1.encode('utf8'),
                                                    extranonce2.encode('utf8'), coinb2.encode('utf8'), d.encode('utf8'))

                xblockheader0 = version + prevhash + merkleroot_1.decode('utf8') + ntime + nbits
                znonce = random.randint(0, 2 ** 32 - 1)

            if b'mining.set_difficulty' in response or b'mining.notify' in response:
                q.put({"xblockheader0": xblockheader0,
                       "job_id": job_id,
                       "extranonce2": extranonce2,
                       "ntime": ntime,
                       "difficult": difficult,
                       "nonce": znonce,
                       'address':address
                       })
    except KeyboardInterrupt:
        proc.terminate()
        sock.close()


if __name__ == "__main__":
    miner()
