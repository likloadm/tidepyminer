import tdc_yespower
import kawpow
import time

final_hash = kawpow.light_verify( bytes("000000206e8c2f50c5779457d1ba097061e9d7dd1f7802bfede217b0c1d9c30100000000e32e4c7c4178e98430f863c3b2f6a5698cbf95b9c0b2ddcef256d41d956b1bcfce4d4f62c3aa021c10ee0000f0db2a86bfdd1f3d23f10049e81b97365a5e31ae728cb82e7ef65161bd402748bbdc06573e352acc"), bytes("cc2a353e5706dcbb482740bd6151f67e2eb88c72ae315e5a36971be84900f123"), "3D1FDDBF862ADC00" )

yes = bytes.fromhex("0000002009f42768de3cfb4e58fc56368c1477f87f60e248d7130df3fb8acd7f6208b83a72f90dd3ad8fe06c7f70d73f256f1e07185dcc217a58b9517c699226ac0297d2ad60ba61b62a021d9b7700f0")

iterator = 0
time_start = time.time()

while iterator < 10000:
    x=tdc_yespower.getPoWHash(yes)
    iterator += 1

print(time.time() - time_start)

b1, b2, b3 =  bytes("000000206e8c2f50c5779457d1ba097061e9d7dd1f7802bfede217b0c1d9c30100000000e32e4c7c4178e98430f863c3b2f6a5698cbf95b9c0b2ddcef256d41d956b1bcfce4d4f62c3aa021c10ee0000f0db2a86bfdd1f3d23f10049e81b97365a5e31ae728cb82e7ef65161bd402748bbdc06573e352acc"), bytes("cc2a353e5706dcbb482740bd6151f67e2eb88c72ae315e5a36971be84900f123"), "3D1FDDBF862ADC00"

iterator = 0
time_start = time.time()

while iterator < 10000:
    x=kawpow.light_verify(b1, b2, b3)
    iterator += 1

print(time.time() - time_start)