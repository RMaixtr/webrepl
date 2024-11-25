
import uos
import unats as nats
import io
class WebreplWrapper(io.IOBase):
    def __init__(self, nc):
        self.nc = nc
        self.sub = nc.subscribe(b"mpy.repl.input")
        self.datalis = []

    def write(self, buf):
        nc.publish(b"mpy.repl.output", buf)
        return len(buf)

    def read(self, n):
        if len(self.datalis) == 0:
            result = self.sub.next_msg().__next__()
            result = bytes(result.data).decode()
            # print(result)
            if result == None:
                return None
            for byte in result:
                self.datalis.append(byte)
        return self.datalis.pop(0)

nc = nats.connect("192.168.1.111")
Webrepl = WebreplWrapper(nc)
uos.dupterm(Webrepl)
