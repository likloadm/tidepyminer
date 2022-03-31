#  Copyright (c) 2019, The Monero Project
#
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  3. Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#  FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import socket
import select
import binascii
import struct
import json
import sys
import os
import time
from multiprocessing import Process, Queue
import tdc_mine
import random

pool_host = 'pool.tidecoin.exchange'
pool_port = 3033
pool_pass = 'xx'
wallet_address = 'TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw'
nicehash = False
address = 'TSrAZcfyx8EZdzaLjV5ketPwtowgw3WUYw'


host    = 'pool.tidecoin.exchange'
port    = 3033


def main():
    pool_ip = socket.gethostbyname(pool_host)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((pool_ip, pool_port))

    q = Queue()
    proc = Process(target=worker, args=(q, s))
    proc.daemon = True
    proc.start()

    s.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
    lines = s.recv(2024).decode().split('\n')
    response = json.loads(lines[0])
    sub_details, extranonce1, extranonce2_size = response['result']
    print(sub_details, extranonce1, extranonce2_size)

    login = {
        'method': 'mining.authorize',
        'params': [
            wallet_address,
            pool_pass
        ],
        'id': 1
    }
    print('Logging into pool: {}:{}'.format(pool_host, pool_port))
    print('Using NiceHash mode: {}'.format(nicehash))
    s.sendall(str(json.dumps(login) + '\n').encode('utf-8'))

    try:
        while 1:
            line = s.makefile().readline()
            r = json.loads(line)
            error = r.get('error')
            result = r.get('result')
            method = r.get('method')
            params = r.get('params')
            if error:
                print('Error: {}'.format(error))
                continue
            if result and result.get('status'):
                print('Status: {}'.format(result.get('status')))
            if result and result.get('job'):
                login_id = result.get('id')
                job = result.get('job')
                job['login_id'] = login_id
                q.put(job)
            elif method and method == 'job' and len(login_id):
                q.put(params)
    except KeyboardInterrupt:
        print('{}Exiting'.format(os.linesep))
        proc.terminate()
        s.close()
        sys.exit(0)


def pack_nonce(blob, nonce):
    b = binascii.unhexlify(blob)
    bin = struct.pack('39B', *bytearray(b[:39]))
    if nicehash:
        bin += struct.pack('I', nonce & 0x00ffffff)[:3]
        bin += struct.pack('{}B'.format(len(b) - 42), *bytearray(b[42:]))
    else:
        bin += struct.pack('I', nonce)
        bin += struct.pack('{}B'.format(len(b) - 43), *bytearray(b[43:]))
    return bin


def worker(q, s):
    started = time.time()
    hash_count = 0

    while 1:
        job = q.get()
        if job.get('login_id'):
            login_id = job.get('login_id')
            print('Login ID: {}'.format(login_id))
        target = job.get('target')
        job_id = job.get('job_id')
        height = job.get('height')
        version = job.get('version')
        prevhash = job.get('prevhash')
        merkleroot_1 = job.get('merkleroot_1')
        ntime = job.get('ntime')
        nbits = job.get('nbits')

        print('New tide job with target: {}, height: {}'.format(target, height))
        target = struct.unpack('I', binascii.unhexlify(target))[0]
        if target >> 32 == 0:
            target = int(0xFFFFFFFFFFFFFFFF / int(0xFFFFFFFF / target))
        nonce = 1

        while 1:
            znonce = random.randint(0, 2 ** 32 - 1)
            xnonce = hex(znonce)[2:].zfill(8)
            xblockheader = version + prevhash + merkleroot_1.decode('utf8') + ntime + nbits + xnonce
            hash = tdc_mine.miner_thread(xblockheader.encode('utf8'), b'0.05', znonce)
            # pycryptonight.cn_slow_hash(bin, cnv, 0, height)
            hash_count += 1
            sys.stdout.write('.')
            sys.stdout.flush()
            hex_hash = binascii.hexlify(hash).decode()
            r64 = struct.unpack('Q', hash[24:])[0]
            if r64 < target:
                elapsed = time.time() - started
                hr = int(hash_count / elapsed)
                print('{}Hashrate: {} H/s'.format(os.linesep, hr))
                if nicehash:
                    nonce = struct.unpack('I', bin[39:43])[0]
                submit = {
                    'method': 'mining.submit',
                    'params': {
                        'id': login_id,
                        'job_id': job_id,
                        'nonce': binascii.hexlify(struct.pack('<I', nonce)).decode(),
                        'result': hex_hash
                    },
                    'id': 1
                }
                print('Submitting hash: {}'.format(hex_hash))
                s.sendall(str(json.dumps(submit) + '\n').encode('utf-8'))
                select.select([s], [], [], 3)
                if not q.empty():
                    break
            nonce += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nicehash', action='store_true', help='NiceHash mode')
    parser.add_argument('--host', action='store', help='Pool host')
    parser.add_argument('--port', action='store', help='Pool port')
    args = parser.parse_args()
    if args.nicehash:
        nicehash = True
    if args.host:
        pool_host = args.host
    if args.port:
        pool_port = int(args.port)
    main()
