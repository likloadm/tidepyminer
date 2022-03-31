/*
 * Copyright 2010 Jeff Garzik
 * Copyright 2012-2014 pooler
 * Copyright 2017 ohac
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.  See COPYING for more details.
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <inttypes.h>
#include <unistd.h>
#include <sys/time.h>
#include <time.h>
#include <errno.h>
#include <signal.h>
#include <sys/resource.h>
#if HAVE_SYS_SYSCTL_H
#include <sys/types.h>
#if HAVE_SYS_PARAM_H
#include <sys/param.h>
#include <sys/sysctl.h>
#endif
#endif
#include "miner.h"
#include "sysendian.h"
#include "yespower.h"

static inline int pretest(const uint32_t *hash, const uint32_t *target)
{
	return hash[7] < target[7];
}

int
miner_thread(const char* blockheader, const char* targetstr,
		uint32_t first_nonce, char *rv)
{
	char pdata[80];
	uint32_t target[8];
	uint32_t max_nonce = 0xffffffffU;
	uint32_t data[28] __attribute__((aligned(128)));
	uint32_t hash[8] __attribute__((aligned(32)));
	uint32_t n = 0;
	uint32_t n2 = 0;
	double diff;
	uint32_t headerlen = 80;

	yespower_params_t params = {
		.version = YESPOWER_1_0,
		.N = 2048,
		.r = 8,
		.pers = NULL,
		.perslen = 0
	};

	hex2bin((void*)pdata, blockheader, headerlen);
	diff = atof(targetstr);
	diff_to_target(target, diff / 65536.0);

	n = first_nonce - 1;

	data[0] = be32dec(&pdata[0]); // version
	for (int i = 0; i < 8; i++) { // prev hash
		data[i+1] = be32dec(&pdata[(i+1)*4]);
	}
	for (int i = 0; i < 8; i++) { // merkle root
		data[9 + i] = le32dec(&pdata[(i+9)*4]);
	}
	for (int i = 17; i < 20; i++) {
		data[i] = be32dec(&pdata[i*4]);
	}
	do {
		be32enc(&data[19], ++n);
		yespower_tls((const uint8_t *) data, headerlen, &params,
			     (yespower_binary_t *) hash);
		if (pretest(hash, target) && fulltest(hash, target)) {
			n2 = n;
			bin2hex(rv, (void*)&n2, 4);
			rv[8] = ',';
			bin2hex(&rv[8+1], (void*)hash, 32);
			rv[8+1+64] = ',';
			bin2hex(&rv[8+1+64+1], (void*)target, 32);
			rv[8+1+64+1+64] = 0;
			return 1;
		}
	} while (n < max_nonce);
	rv[0] = 0;
	return 1;
}
