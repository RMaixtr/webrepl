import uos
from websockets.server import serve
import _thread
import uasyncio
import io

lock = _thread.allocate_lock()

class WebreplWrapper(io.IOBase):
    def __init__(self, ws=None, loop=None, lock=None):
        self.ws = ws
        self.loop = loop
        self.lis = []
        self.lock = lock

    def wsread(self):
        if len(self.lis) == 0:
            result = self.loop.run_until_complete(self.ws.recv())
            if result == None:
                return None
            for byte in result:
                self.lis.append(byte)
            return self.lis.pop(0)
        else:
            return self.lis.pop(0)

    def write(self, buf):
        # try:
        if self.ws:
            # Note that there is a problem with byte sending implemented by the websocket library
            self.loop.run_until_complete(self.ws.send(bytes(buf).decode()))
            return len(buf)
        else:
            return len(buf)
        # except Exception as e:
        #     self.ws = None
        #     print("write err", e)

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
        try:
            if self.ws:
                tmp = self.wsread()
                if tmp == None:
                    print("EOF\r\n")
                    self.ws = None
                    self.lock.release()
                    return None
                else:
                    return tmp
            else:
                self.lock.acquire()
                return None
        except Exception as e:
            # self.ws = None
            print("read", e)

async def add_client(ws, path):
    global duptermio,lock
    print("Connection on {}".format(path))
    try:
        lock.release()
    except Exception as e:
        print(e)
    duptermio.ws = ws

def main():
    global duptermio, lock
    server = serve(add_client, "0.0.0.0", 8266)
    loop = uasyncio.get_event_loop()
    duptermio = WebreplWrapper(None, loop, lock)
    lock.acquire()
    uos.dupterm(duptermio)
    loop.run_until_complete(server)
    loop.run_forever()


_thread.start_new_thread(main,())