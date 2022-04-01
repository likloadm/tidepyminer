#A stratum compatible miniminer
#based in the documentation
#https://slushpool.com/help/#!/manual/stratum-protocol
#2017-2019 Martin Nadal https://martinnadal.eu

import socket
import json
import random
import tdc_mine
import time
from multiprocessing import Process, Queue, cpu_count
import asyncio
import websockets


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


def miner_thread(xblockheader, difficult, q):
    z = [0, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"]
    while int.from_bytes(hash_decode(z[1]), byteorder='big') > int(
            1 / (difficult / 65536) * 0x00000000ffff0000000000000000000000000000000000000000000000000000):
        nonce = random.randint(0, 2 ** 32 - 1)  # job.get('nonce')
        nonce_and_hash = tdc_mine.miner_thread(xblockheader.encode('utf8'), bytes(str(difficult / 4), "utf-8"), nonce)
        if not q.empty():
            return False
        z = nonce_and_hash.decode('utf-8').split(',')
    return z


def worker(q, sock, number):
    xnonce = "00000000"
    while 1:
        job = q.get()
        xblockheader0 = job.get('xblockheader0')
        job_id = job.get('job_id')
        extranonce2 = job.get('extranonce2')
        ntime = job.get("ntime")
        difficult = job.get('difficult')
        address = job.get('address')
        xblockheader = xblockheader0 + xnonce
        payload1 = '{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 + '", "' + ntime + '", "'
        payload2 = '"], "id": 4, "method": "mining.submit"}\n'

        while 1:
            started = time.time()
            if not (z := miner_thread(xblockheader, difficult, q)):
                break
            print(f'{number} thread yay!!! Time:', time.time()-started, 'Diff', difficult)
            sock.sendall(bytes(payload1+z[0]+payload2, "UTF-8"))
            if not q.empty():
                break


async def miner(address, host, port, cpu_count=cpu_count()):
    print("address:{}".format(address))
    print("host:{} port:{}".format(host, port))
    async with websockets.serve(echo, host, port) as websocket:
        await websocket.send(b'{"id": 1, "method": "mining.subscribe", "params": ["pytideminer-1.0.0"]}\n')
        await asyncio.Future()  # run forever
    procs = []
    queues = []
    count = cpu_count

    for number in range(count):
        q = Queue()
        proc = Process(target=worker, args=(q, sock, number+1))
        proc.daemon = True
        procs.append(proc)
        queues.append(q)
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

            if (b'mining.notify' in response):
                responses = [json.loads(res) for res in response.decode().split('\n') if
                             len(res.strip()) > 0 and 'mining.notify' in res]

                job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs \
                    = responses[0]['params']
                d = ''

                for h in merkle_branch:
                    d += h
                extranonce2 = '00' * extranonce2_size
                merkleroot_1 = tdc_mine.sha256d_str(coinb1.encode('utf8'), extranonce1.encode('utf8'),
                                                    extranonce2.encode('utf8'), coinb2.encode('utf8'), d.encode('utf8'))

                xblockheader0 = version + prevhash + merkleroot_1.decode('utf8') + ntime + nbits

            if b'mining.set_difficulty' in response or b'mining.notify' in response:
                for number in range(count):
                    if not queues[number].empty():
                        queues[number].get()

                    queues[number].put({"xblockheader0": xblockheader0,
                           "job_id": job_id,
                           "extranonce2": extranonce2,
                           "ntime": ntime,
                           "difficult": difficult,
                           'address':address
                           })
    except KeyboardInterrupt:
        proc.terminate()
        sock.close()


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)



asyncio.run(main())

if __name__ == "__main__":
    address = 'TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw.upgrade'

    host = 'pool.tidecoin.exchange'
    port = 3033
    miner(address, host, port, 4)
