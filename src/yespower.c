/*-
 * Copyright 2013-2018 Alexander Peslyak
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */

#include "miner.h"
#include "sysendian.h"

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "yespower.h"

const char* sha256d_str(
		const char *coinb1str,
		const char *xnonce1str,
		const char *xnonce2str,
		const char *coinb2str,
		const char *merklestr,
		char *rv)
{
	unsigned char merkle_root[64];
	unsigned char buff[256];
	size_t coinb1_size = strlen(coinb1str) / 2;
	size_t xnonce1_size = strlen(xnonce1str) / 2;
	size_t xnonce2_size = strlen(xnonce2str) / 2;
	size_t coinb2_size = strlen(coinb2str) / 2;
	size_t coinbase_size = coinb1_size + xnonce1_size + xnonce2_size + coinb2_size;
	int merkle_count = strlen(merklestr) / (32 * 2);
	int i;
	unsigned char coinbase[256];

	hex2bin(coinbase, coinb1str, coinb1_size);
	hex2bin(coinbase + coinb1_size, xnonce1str, xnonce1_size);
	hex2bin(coinbase + coinb1_size + xnonce1_size, xnonce2str, xnonce2_size);
	hex2bin(coinbase + coinb1_size + xnonce1_size + xnonce2_size, coinb2str, coinb2_size);
	sha256d(merkle_root, coinbase, coinbase_size);

	for (i = 0; i < merkle_count; i++) {
		hex2bin(merkle_root + 32, merklestr + i * 32 * 2, 32);
		sha256d(merkle_root, merkle_root, 64);
	}
	bin2hex(rv, merkle_root, 32);
	return 1;
}
