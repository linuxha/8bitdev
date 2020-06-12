from    abc  import ABC, abstractmethod
from    collections.abc  import Sequence
from    numbers  import Integral

class MemoryAccess(ABC):
    ''' Access methods for a random-access memory stored as a mutable
        sequence of values.

        This handles reading and depositing of bytes and words (in
        big-endian format) with error checking.

        XXX this needs to be extended to be configurable for big-
        or little-endian access.
    '''

    @abstractmethod
    def get_memory_seq(self):
        ''' Return the mutable sequence representing the memory that we access.

            In normal circumstances this should be a `bytearray`, but
            depending on the simulator you may need to use another type,
            such as py65's list of Integer.
        '''

    def byte(self, addr):
        ' Return the byte at `addr`. '
        return self.get_memory_seq()[addr]

    def bytes(self, addr, n):
        ' Return `n` `bytes` starting at `addr`. '
        bs = self.get_memory_seq()[addr:addr+n]
        if len(bs) < n:
            raise IndexError(
                'Last address ${:4X} out of range'.format(addr+n-1))
        return bytes(bs)

    def word(self, addr):
        ' Return the word (decoding native endianness) at `addr`. '
        mem = self.get_memory_seq()
        return mem[addr] * 0x100 + mem[addr+1]

    def words(self, addr, n):
        ''' Return a sequence of `n` words (decoding native endianness)
            starting `addr`. '
        '''
        return tuple( self.word(i) for i in range(addr, addr+n*2, 2) )

    def deposit(self, addr, *values):
        ''' Deposit bytes to memory at `addr`. Remaining parameters
            are values to deposit at contiguous addresses, each of which
            is a `numbers.Integral` in range 0x00-0xFF or a `Sequence`
            of such numbers (e.g., `list`, `tuple`, `bytes`).

            Returns a `bytes` of the deposited data.
        '''
        def err(s, *errvalues):
            msg = 'deposit @${:04X}: ' + s
            raise ValueError(msg.format(addr, *errvalues))
        def assertvalue(x):
            if not isinstance(x, Integral):
                err('non-integral value {}', repr(x))
            if x < 0x00 or x > 0xFF:
                err('invalid byte value ${:02X}', x)

        vlist = []
        for value in values:
            if isinstance(value, Integral):
                assertvalue(value)
                vlist.append(value)
            elif isinstance(value, Sequence):
                list(map(assertvalue, value))
                vlist += list(value)
            else:
                err('invalid argument {}', repr(value))

        lastaddr = addr + len(vlist) - 1
        if lastaddr > 0xFFFF:
            raise IndexError(
                'Last address ${:X} out of range'.format(lastaddr))
        self.get_memory_seq()[addr:lastaddr+1] = vlist
        return bytes(vlist)

    def _deperr(self, addr, message, *errvalues):
        s = 'deposit @${:04X}: ' + message
        raise ValueError(s.format(addr, *errvalues))

    def depword(self, addr, *values):
        ''' Deposit 16-bit words to memory at `addr` in native endian
            format. Remaining parameters are values to deposit at
            contiguous addresses, each of which is a
            `numbers.Integral` in range 0x0000-0xFFFF or a `Sequence`
            of such numbers (e.g., `list`, `tuple`, `bytes`).

            Returns a `bytes` of the deposited data.
        '''
        def assertvalue(x):
            if not isinstance(x, Integral):
                self._deperr(addr, 'non-integral value {}', repr(x))
            if x < 0x00 or x > 0xFFFF:
                self._deperr(addr, 'invalid word value ${:02X}', x)

        words = []
        for value in values:
            if isinstance(value, Integral):
                assertvalue(value)
                words.append(value)
            elif isinstance(value, Sequence):
                list(map(assertvalue, value))
                words += list(value)
            else:
                self._deperr(addr, 'invalid argument {}', repr(value))

        data = []
        for word in words:
            data.append((word & 0xFF00) >> 8)   # MSB first for 6800
            data.append(word & 0xFF)            # LSB
        self.deposit(addr, data)

        return self.bytes(addr, len(words)*2)

