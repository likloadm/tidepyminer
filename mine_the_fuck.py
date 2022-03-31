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


bfh = bytes.fromhex


address = 'TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw'


host    = 'pool.tidecoin.exchange'
port    = 3033

print("address:{}".format(address))
print("host:{} port:{}".format(host,port))

sock    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host,port))

#server connection
sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
lines = sock.recv(1024).decode().split('\n')
response = json.loads(lines[0])
sub_details,extranonce1,extranonce2_size = response['result']
print(sub_details, extranonce1,extranonce2_size)
#authorize workers
sock.sendall(b'{"params": ["'+address.encode()+b'", "password"], "id": 2, "method": "mining.authorize"}\n')

#we read until 'mining.notify' is reached
while True:
    response = b''

    while response.count(b'\n') < 4 and not(b'mining.notify' in response):
        comeback = sock.recv(1024)
        response += comeback
        print(comeback)


    #get rid of empty lines
    responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip())>0 and 'mining.notify' in res]
    diff = [json.loads(res) for res in response.decode().split('\n') if
                 len(res.strip()) > 0 and 'mining.set_difficulty' in res]
    if diff:
        difficult = diff[0]['params'][0]
    pprint(responses)

    job_id,prevhash,coinb1,coinb2,merkle_branch,version,nbits,ntime,clean_jobs \
        = responses[0]['params']

    #target https://bitcoin.stackexchange.com/a/36228/44319

    target = bits_to_target(target_to_bits(int(nbits, 16)))
    print('nbits:{} target:{}\n'.format(nbits,target))

    extranonce2 = '00'*extranonce2_size

    d=''

    for h in merkle_branch:
     d+=h

    merkleroot_1=tdc_mine.sha256d_str(coinb1.encode('utf8'),extranonce1.encode('utf8'),extranonce2.encode('utf8'),coinb2.encode('utf8'),d.encode('utf8'))
    print(merkleroot_1.decode('utf8'))
    znonce= random.randint(0, 2 ** 32 - 1)
    xnonce = hex(znonce)[2:].zfill(8)
    xblockheader = version + prevhash + merkleroot_1.decode('utf8') + ntime + nbits + xnonce
    print("xblockheader", xblockheader)
    nonce_and_hash=tdc_mine.miner_thread(xblockheader.encode('utf8'),bytes(str(difficult), "utf-8"), znonce)

    print("XFUCK")
    print(nonce_and_hash)
    print("XFUCK2")
    z=nonce_and_hash.decode('utf-8').split(',')
    print(z)

    if int.from_bytes(bfh(hash_encode(z[1])), byteorder='big') < 0x01ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff*difficult:
        print('success!!')
        payload = '{"params": ["'+address+'", "'+job_id+'", "'+extranonce2 \
            +'", "'+ntime+'", "'+z[0]+'"], "id": 1, "method": "mining.submit"}\n'
        sock.sendall(bytes(payload, "UTF-8"))
    else:
        print('failed mine, hash is greater than target')

sock.close()