import json
import time

ALL = 'ALL'

TRAIN_DIR = 'out'


class WordReader(object):
    def __init__(self, file_path, chunk_size=8096):
        self.__path = file_path
        self.__file_object = None
        self.chunk_size = chunk_size

    def __enter__(self):
        self.__file_object = open(self.__path, errors='ignore')
        return self

    def __exit__(self, type, val, tb):
        self.__file_object.close()

    def __iter__(self):
        self.chached_chunk = self.__file_object.read(self.chunk_size)
        return self

    def __next__(self):
        word = ''
        length = 0
        word_completed = False
        chunk = self.chached_chunk
        while not word_completed:
            # if not chunk:
            #     raise StopIteration
            # char = ord(symb)
            for i in range(self.chunk_size):
                try:
                    char = ord(chunk[i])
                    if char < 91 and char > 64:
                        word += chr(char + 32)
                        length += 1
                    elif char > 96 and char < 123:
                        word += chunk[i]
                        length += 1
                    elif word:
                        word_completed = True
                        self.chached_chunk = chunk[i:] + self.__file_object.read(i + 1)
                except IndexError:
                    # file ended before chunk
                    raise StopIteration
            chunk = self.__file_object.read(self.chunk_size)

        return word, length


class MarkovModel(object):
    dump_filename = 'model.json'

    @classmethod
    def from_dump(cls, order):
        m = cls(order)
        with open(cls.dump_filename, 'r') as f:
            m.graph = json.loads(f.read())

        return m

    def __init__(self, orders, filename=None):
        self.graph = {}
        self.orders = orders

        if filename:
            self.feed(filename)

    def feed(self, filename):
        with WordReader(filename) as w:
            for word, w_len in w:
                for order in self.orders:
                    if w_len < order:
                        continue
                    for i in range(0, w_len - order):
                        kgram = word[i:i+order]
                        symb = word[i+order]
                        self.graph.setdefault(kgram, {}).setdefault(symb, 0)
                        self.graph[kgram][symb] += 1
                        self.graph[kgram].setdefault(ALL, 0)
                        self.graph[kgram][ALL] += 1

    def freq_part(self, part):
        return sum(self.graph[part])

    def freq(self, part, symb):
        try:
            return self.graph[part][symb] / self.graph[part][ALL]
        except KeyError:
            return 0

    def pprint(self):
        out = ['%s: %s' % (k, v) for k, v in self.graph.items()]
        return '\n'.join(out)

    def save(self):
        with open(self.dump_filename, 'r') as f1:
            with open('%s.%s' % (time.time(), self.dump_filename), 'w') as f2:
                f2.write(f1.read())

        with open(self.dump_filename, 'w') as f:
            f.write(json.dumps(self.graph))


def spellcheck(m):
    import getch

    iinput = ''
    checking = ''
    input('GO:')
    while True:
        ch = getch.getch()
        if ch == ' ':
            checking = ''
        freq = 1
        if len(checking) > 4:
            freq = m.freq(iinput[-4:], ch)
        iinput += ch
        checking += ch
        sys.stdout.write('%s(%10.2f)\r' % (iinput, freq))


if __name__ == "__main__":
    import sys
    from os import listdir, path

    docs = listdir(TRAIN_DIR)
    file_count = len(docs)
    processed = 0

    m = MarkovModel([3, ])

    for doc in docs:
        m.feed(path.join(TRAIN_DIR, doc))
        processed += 1
        sys.stdout.write('\r[%2.2f%%]' % (processed / file_count * 100))

    # m.save()
