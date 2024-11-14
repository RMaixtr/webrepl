# This module should be imported from REPL, not run from command line.
import binascii
import hashlib
from micropython import const
# import network
import uos
import socket
import usys
import websocket
import uselect
import _thread
import _webrepl

listen_s = None
client_s = None

lock = _thread.allocate_lock()

DEBUG = 0

_DEFAULT_STATIC_HOST = const("https://micropython.org/webrepl/")
static_host = _DEFAULT_STATIC_HOST


def server_handshake(cl):
    req = cl.makefile("rwb", 0)
    # Skip HTTP GET line.
    l = req.readline()
    if DEBUG:
        usys.stdout.write(repr(l))

    webkey = None
    upgrade = False
    websocket = False

    while True:
        l = req.readline()
        if not l:
            # EOF in headers.
            return False
        if l == b"\r\n":
            break
        if DEBUG:
            usys.stdout.write(l)
        h, v = [x.strip() for x in l.split(b":", 1)]
        if DEBUG:
            print((h, v))
        if h == b"Sec-WebSocket-Key":
            webkey = v
        elif h == b"Connection" and b"Upgrade" in v:
            upgrade = True
        elif h == b"Upgrade" and v == b"websocket":
            websocket = True

    if not (upgrade and websocket and webkey):
        return False

    if DEBUG:
        print("Sec-WebSocket-Key:", webkey, len(webkey))

    d = hashlib.sha1(webkey)
    d.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
    respkey = d.digest()
    respkey = binascii.b2a_base64(respkey)[:-1]
    if DEBUG:
        print("respkey:", respkey)

    cl.send(
        b"""\
HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Accept: """
    )
    cl.send(respkey)
    cl.send("\r\n\r\n")

    return True


def send_html(cl):
    cl.send(
        b"""\
HTTP/1.0 200 OK\r
\r
<base href=\""""
    )
    cl.send(static_host)
    cl.send(
        b"""\"></base>\r
<script src="webrepl_content.js"></script>\r
"""
    )
    cl.close()


def setup_conn(port, accept_handler):
    global listen_s
    listen_s = socket.socket()
    listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ai = socket.getaddrinfo("0.0.0.0", port)
    addr = ai[0][4]

    listen_s.bind(addr)
    listen_s.listen(1)
    if accept_handler:
        accept_conn(listen_s)
    return listen_s


def accept_conn(listen_sock):
    global client_s, dupWebrepl
    print("waiting for connection")
    cl, remote_addr = listen_sock.accept()
    if not server_handshake(cl):
        send_html(cl)
        return False
    
    print("\nWebREPL connection from:", remote_addr)
    client_s = cl

    ws = websocket.websocket(cl, True)
    ws = _webrepl._webrepl(ws)
    # cl.setblocking(False)
    # uos.dupterm(ws)
    dupWebrepl.ws = ws
    lock.release()

    return True


# def stop():
#     global listen_s, client_s
#     uos.dupterm(None)
#     if client_s:
#         client_s.close()
#     if listen_s:
#         listen_s.close()


def start(port=8266, password="1234", accept_handler=accept_conn):
    global static_host, listen_s
    # stop()
    _webrepl.password(password)
    setup_conn(port, accept_handler)
    while True:
        accept_conn(listen_s)

import io
class WebreplWrapper(io.IOBase):
    def __init__(self, ws=None):
        self.ws = ws

    def readinto(self, buf):
        print("readinto")
        try:
            if self.ws:
                return self.ws.readinto(buf)
            else:
                return 0
        except Exception as e:
            self.ws = None
            print("readinto", e)

    def write(self, buf):
        # print("write")
        try:
            if self.ws:
                return self.ws.write(buf)
            else:
                return len(buf)
        except Exception as e:
            self.ws = None
            print("write", e)

    def ioctl(self, kind, arg):
        print("ioctl")
        return -1

    def close(self):
        print("close")
        try:
            if self.ws:
                return self.ws.close()
        except Exception as e:
            self.ws = None
            print("close", e)

    def read(self, n):
        # print("read", n)
        # try:
        if self.ws:
            po = uselect.poll()
            po.register(client_s, uselect.POLLIN)
            po.poll()
            tmp = self.ws.read(n)
            if tmp == b'':
                self.ws = None
                print("EOF")
                return None
            else:
                return tmp
        else:
            lock.acquire()
            return None
        # except Exception as e:
            # self.ws = None
            # print("read", e)

# 'close', 'read', 'readinto', 'readline', 'write', 'ioctl'

_thread.start_new_thread(start, ())
# start()
dupWebrepl = WebreplWrapper(None)
uos.dupterm(dupWebrepl)