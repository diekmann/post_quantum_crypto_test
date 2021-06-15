#!/usr/bin/env python3

import numpy as np

# The most simple Learning With Errors (LWE) Public Key Cryptosystem
#
# Based on author's copy of book chapter in Post Quantum Cryptography,
#   D.J. Bernstein; J. Buchmann; E. Dahmen (eds.), pp. 147-191, Springer (February 2009).
# Lattice-Based Cryptography
# Author: Daniele Micciancio, Oded Regev
# https://cseweb.ucsd.edu/~daniele/papers/PostQuantum.pdf pp.18


# DO NOT USE IN PRODICTION! I HAVE NO IDEA WHAT I'M DOING.
# THIS CODE DEFINITELY HAS SIDE-CHANNELS, IS SUPER SLOW, AND LIKELY INSECURE!!!!



# https://cseweb.ucsd.edu/~daniele/papers/PostQuantum.pdf p.23
n = 136
l = 136
m = 2008
q = 2003
r = 1
t = 2
alpha = 0.0065

expected_pub_key_size_bits = 6*10**6
expected_encryption_blowup_factor = 21.9
expected_error_probability = 0.9/100



def hamming(xs, ys):
    """hamming distance helper to print number of bit decryption errors later."""
    distance = 0
    assert len(xs) == len(ys)
    assert all(x in ['0','1'] for x in xs)
    assert all(y in ['0','1'] for y in ys)
    for a, b in zip(xs, ys):
        if a != b:
            distance += 1
    return distance
assert hamming("010101", "010101") == 0
assert hamming("010101", "010001") == 1
assert hamming("010101", "010011") == 2


def bitstring(xs):
    return "".join(map(str, xs))
assert bitstring([0,1,0]) == "010"


rng = np.random.default_rng()



# mapping the {0,1} messages to the Z_q encryption space and back.
def f(x):
    return np.array([round(val * (q/t)) for val in x])
def f_inv(x):
    # mod t not _explicitly_ mentioned in book, but we neet to map into Z^l_t 
    return np.mod(np.array([int(round(val / (q/t))) for val in x]), t)

assert np.array_equal(f(np.array([0,1])), [0, 1002])
assert np.array_equal(f_inv(f(np.array([0,1]))), [0,1])

def encode_ascii(str_):
    def flatten(vss):
        return [v for vs in vss for v in vs]
    assert flatten([[1,2], [3,4]]) == [1,2,3,4]
    return flatten([map(int, list(f"{ord(w):08b}")) for w in str_])
def decode_ascii(vs):
    assert len(vs) % 8 == 0, f"{len(vs)} must be a multiple of 8"
    result = ""
    for i in range(0, len(vs), 8):
        byte = bitstring(vs[i:i+8])
        result += chr(int(byte, 2))
    return result

assert encode_ascii("A")  == [0, 1, 0, 0, 0, 0, 0, 1]
assert encode_ascii("AB") == [0, 1, 0, 0, 0, 0, 0, 1] + [0, 1, 0, 0, 0, 0, 1, 0]
assert decode_ascii(encode_ascii("Hello, World")) == "Hello, World"
assert decode_ascii(f_inv(f(encode_ascii("Hello, World, foo")))) == "Hello, World, foo"




def gen_private_key():
    S = rng.integers(low=0, high=q, size=(n,l))
    assert S.shape == (n,l)
    return S

def gen_public_key(S):
    A = rng.integers(low=0, high=q, size=(m,n))
    assert A.shape == (m,n)

    # E according to Sigma_alpha distribution on Z_q!
    # normal variable with mean 0 and standard deviation alpha*q/sqrt(2*pi) round()'ed
    # and np.mod(_, q).
    stddev = (alpha*q)/(np.sqrt(2*np.pi))
    E = rng.normal(loc=0, scale=stddev, size=(m,l))
    assert np.mean(E) < 0.1, f"mean should be somewhat around 0, but is actually {np.mean(E)} in this example"
    E = np.mod(np.int64(np.rint(E)), q)
    assert E.shape == (m,l)

    PubKey = (A, np.mod(np.mod(np.matmul(A, S), q) + E, q))
    assert PubKey[1].shape == (m,l)
    assert all(all(0 <= c < q for c in row) for row in PubKey[0])
    assert all(all(0 <= c < q for c in row) for row in PubKey[1])
    return PubKey

def enc(PubKey, v):
    for val in v:
        assert 0 <= val and val < t
        assert type(val) == np.int64
    assert v.shape == (l,), f"message to encrypt must be of length {l}, but is {v.shape}"
    A = PubKey[0]
    P = PubKey[1]
    a = rng.integers(low=-r, high=r, endpoint=True, size=(m,))
    u = np.mod(np.matmul(np.transpose(A), a), q)
    assert u.shape == (n,)
    c = np.mod(np.mod(np.matmul(np.transpose(P), a), q) + f(v), q)
    assert c.shape == (l,)
    return (u,c)

def dec(S, ciphertext):
    u,c = ciphertext
    assert u.shape == (n,)
    assert c.shape == (l,)
    return f_inv(np.mod(c - np.mod(np.matmul(np.transpose(S), u), q), q))




# Simulate the number of decryption errors for a new random private string when encrypting and
# decrypting the hard-coded string 'Hello, World, foo'
def simulate_error_ratio():
    S = gen_private_key()
    PubKey = gen_public_key(S)
    plaintext = np.array(encode_ascii("Hello, World, foo")) # exactly the size needed
    assert plaintext.shape == (136, ), f"encoded plaintext should have size {l}, has size {plaintext.shape}"

    ciphertext = enc(PubKey, plaintext)
    
    decrypted = dec(S, ciphertext)

    plaintext = bitstring(plaintext)
    decrypted = bitstring(decrypted)
    
    errors = hamming(plaintext, decrypted)
    observed_error_ratio = errors/len(plaintext)
    print(f"Hamming distance of original plaintext vs decrypted text (i.e. wrong bits): {errors}, error ratio: {observed_error_ratio * 100}%")

    assert np.abs(expected_error_probability - observed_error_ratio) < 0.1 # more than 10%!
    return observed_error_ratio


print("== Experiment 1: is the observed error probability as expected? ==")
num_simulations = 100
error_ratio = 0
for i in range(num_simulations):
    error_ratio += simulate_error_ratio()
error_ratio /= num_simulations

print(f"Over {num_simulations} encryptions/decryptions, the observed error ratio is : {error_ratio * 100}%  expected: {expected_error_probability*100}%")
assert np.abs(expected_error_probability - error_ratio) < 0.01 # more than 1% from the expected error ratio
print("pass")

print("Now that we checked that encryption/decrption is within the expected error ratio, we can look at one run in detail. Chances are high, that the final `decrypted == plaintext` assertion will fail, since a small amount of bits may decrypt wrong.")



print("== Experiment 2: inspecting one encryption/decryption in detail ==")
S = gen_private_key()
print(f"PrivateKey = {S}")

PubKey = gen_public_key(S)
print(f"PubKey = {PubKey}")

public_key_size_in_bits = (PubKey[0].shape[0]*PubKey[0].shape[1] + PubKey[1].shape[0]*PubKey[1].shape[1]) * np.ceil(np.log2(q))
assert 0.99 < public_key_size_in_bits/expected_pub_key_size_bits < 1.01

plaintext = np.array(encode_ascii("Hello, World, foo"))
assert plaintext.shape == (136, ), f"encoded plaintext should have size {l}, has size {plaintext.shape}"

ciphertext = enc(PubKey, plaintext)
print(f"ciphertext = {ciphertext}")

assert all(0 <= c < q for c in ciphertext[0])
binary_size_of_plaintext = len(plaintext) * np.log2(t)
binary_size_of_ciphertext = len(ciphertext[0])*np.ceil(np.log2(q)) + len(ciphertext[1])*np.ceil(np.log2(q))
print(f"plaintext is about {binary_size_of_plaintext} bits, ciphertext is about {binary_size_of_ciphertext} bits.")
assert 0.99 < binary_size_of_plaintext*expected_encryption_blowup_factor/binary_size_of_ciphertext < 1.01


# ciphertext[1] is the part containing the secret message
assert len(ciphertext[1]) == len(plaintext)

decrypted = dec(S, ciphertext)

plaintext = bitstring(plaintext)
decrypted = bitstring(decrypted)


print(f"plaintext = {plaintext}")
print(f"decrypted = {decrypted}")
print(f"decoded decrypted: {decode_ascii(decrypted)}")



### comparing a binary represenation of the ciphertext with the plaintext and asserting, that they look different enough.
ciphertext_visual = bitstring(f_inv(ciphertext[1]))
# ciphertext_visual can no longer be decrypted and is only for visualization, since `f_inv` loses information.
print(f"ciphertxt = {ciphertext_visual} (only second part \"visualized\" as binary)")
distance_cipher_plaintext = hamming(plaintext, ciphertext_visual)
assert distance_cipher_plaintext/len(plaintext) >= 0.25, f"plaintext and ciphertext look too similar!! Only {distance_cipher_plaintext} bits differ, which means {distance_cipher_plaintext / len(plaintext)*100}% are different"


errors = hamming(plaintext, decrypted)
observed_error_ratio = errors/len(plaintext)
print(f"Hamming distance of original plaintext vs decrypted text (i.e. wrong bits): {errors}, error ratio: {observed_error_ratio * 100}%")

assert np.abs(expected_error_probability - observed_error_ratio) < 0.1 # more than 10%!
if decrypted != plaintext:
    print("assert decrypted == plaintext failed (but bit error rate is still plausible)!!")
print("pass")




print("== Experiment 3: encrypt/decrypt identity ==")
def assert_enc_dec_identity(m, num_allowed_bit_errors=3):
    enc_dec = dec(S, enc(PubKey, m))
    bit_errors = hamming(bitstring(enc_dec), bitstring(m))
    assert bit_errors <= num_allowed_bit_errors, f"dec(enc({bitstring(m)})) != {bitstring(m)}, there are {bit_errors} bit errors, but we only accept {num_allowed_bit_errors} bit errors"

assert_enc_dec_identity(np.array(encode_ascii("A"*(l//8))))
assert_enc_dec_identity(np.array(encode_ascii("X"*(l//8))))
assert_enc_dec_identity(np.array([0]*l))
for _ in range(num_simulations):
    assert_enc_dec_identity(rng.integers(low=0, high=t, size=(l,)), num_allowed_bit_errors=5)
print("pass")



print("== Experiment 4: encrypting the message zero several times and printing the resulting distribution of ciphertext values ==")
print("When encrypting with the public key, ciphertext[1] contains the error vector E with its gaussian distribution. IIUC, if we could extract E, we could derive the private key.")
print("The expected result is that the resulting distribution looks very uniform and no gaussian bell curve is visible.")
import matplotlib.pyplot as plt
ciphertext_values = []

plaintext = np.array([0]*l) # just zeros
prev_ciphertext = ([], np.array([0]*l))
num_simulations = 10_000
for i in range(num_simulations):
    ciphertext = enc(PubKey, plaintext)
    ciphertext_values += list(ciphertext[1])
    assert not np.array_equal(prev_ciphertext[1], ciphertext[1]), "encryption is randomized!"
    prev_ciphertext = ciphertext
    if i%1000==0: print(f"{i/num_simulations*100:.0f}%")

print("plotting")
plt.hist(ciphertext_values, bins='auto')
plt.title("Histogram over ciphertext[1] (the part with the norm distribution in it)")
plt.show()

print(f"mean = {np.mean(ciphertext_values)} std dev = {np.std(ciphertext_values)}")
assert np.abs(np.mean(ciphertext_values) - q/2) < 1

