#!/usr/bin/env python3
"""Maintain the password-protected home page (site/home.json).

  python3 tools/make_home.py --setup            # once: make a new password and key pair (prints the password)
  python3 tools/make_home.py --setup --password "my own passphrase"
  python3 tools/make_home.py                    # rebuild the encrypted client list from clients.json (no password needed)

How it works: the client list is encrypted with a public key, so adding clients never needs the password.
The matching private key is stored in home.json locked with the password (PBKDF2 + AES-GCM); the home page
asks for the password in the browser and unlocks the list there. Nothing readable is published.
"""
import argparse, base64, hashlib, json, os, secrets, sys
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.join(ROOT, 'site', 'home.json')
REG = os.path.join(ROOT, 'clients.json')
ITER = 600_000
b64 = lambda b: base64.b64encode(b).decode()
unb64 = lambda s: base64.b64decode(s)

def setup(password):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pkcs8 = key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    salt, iv = os.urandom(16), os.urandom(12)
    k = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITER, 32)
    wrapped = AESGCM(k).encrypt(iv, pkcs8, None)
    return {'v': 1, 'iter': ITER, 'salt': b64(salt), 'iv': b64(iv), 'wrapped': b64(wrapped), 'pub': b64(spki), 'entries': []}

def encrypt_entry(pub_der, obj):
    pub = serialization.load_der_public_key(pub_der)
    k, iv = AESGCM.generate_key(256), os.urandom(12)
    ct = AESGCM(k).encrypt(iv, json.dumps(obj, separators=(',', ':')).encode(), None)
    wk = pub.encrypt(k, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return {'k': b64(wk), 'iv': b64(iv), 'ct': b64(ct)}

def rebuild(home):
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    pub = unb64(home['pub'])
    items = [{'group': g, 'code': e['code'], 'name': e.get('name', g), 'last_day': e.get('last_day')} for g, e in reg.items()]
    items.sort(key=lambda x: x['name'].lower())
    home['entries'] = [encrypt_entry(pub, it) for it in items]
    return len(items)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--setup', action='store_true')
    ap.add_argument('--password')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    if a.setup:
        if os.path.exists(HOME) and not a.force:
            sys.exit('home.json already exists - add --force to replace the password (the old one stops working).')
        pw = a.password or '-'.join(''.join(secrets.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(4)) for _ in range(4))
        home = setup(pw)
        n = rebuild(home)
        json.dump(home, open(HOME, 'w'), separators=(',', ':'))
        print('PASSWORD:', pw)
        print('encrypted', n, 'client(s)')
    else:
        if not os.path.exists(HOME):
            sys.exit('run with --setup first')
        home = json.load(open(HOME))
        n = rebuild(home)
        json.dump(home, open(HOME, 'w'), separators=(',', ':'))
        print('home page list rebuilt:', n, 'client(s)')
