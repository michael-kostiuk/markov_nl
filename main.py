import random
import re
import json
import time

ASCII = 128
ASCII_CODES = range(ASCII)
ALL = 'ALL'


def read_file(fileanme):
    with open(fileanme) as f:
        return f.read()

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
            if not chunk:
                raise StopIteration
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

    def __init__(self, order, filename=None):
        self.graph = {}
        self.order = order
        # self._text = text
        # length = len(text)
        if filename:
            self.feed(filename)

    def feed(self, filename):
        word = ''
        with WordReader(filename) as w:
            for word, w_len in w:
                # w_len = len(word) # faster len?
                # w_len = match.end() - match.start() # faster len?
                if w_len < self.order:
                    continue
                for i in range(0, len(word) - self.order):
                    kgram = word[i:i+self.order]
                    symb = word[i+self.order]
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

    def random_char(self, part):
        symb_code = random.choices(range(ASCII), self.graph[part])
        return chr(symb_code[0])

    def random_text(self, length):
        current = self._text[:self.order]
        out = [current[:],]
        for i in range(length):
            new = self.random_char(current)
            out.append(new)
            current = current[1:] + new
        return ''.join(out)

    def pprint(self):
        out = {}
        for x in self.graph:
            out[x] = {chr(l): self.graph[x][l] for l in ASCII_CODES if self.graph[x][l]}
        return out

    def save(self):
        with open(self.dump_filename, 'r') as f:
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
    import pprint
    import sys
    from os import listdir

    # text = 'banana'
    # m = MarkovModel(text, 2)
    # pprint.pprint(m.pprint())


    # text = 'gagggagaggcgagaaa'
    # m = MarkovModel(text, 2)
    # pprint.pprint(m.pprint())
    # txt = m.random_text(1000)
    # import pdb; pdb.set_trace()
    # text = read_file('wiki_100k.txt')
    # text = read_file('hltv.txt')
    # docs = listdir('/Users/michael/Documents/projector/markov_nl/out')
    # file_count = len(docs)
    # processed = 0

    # m = MarkovModel(4)

    # for doc in docs:
    #     m.feed('out/%s' % doc)
    #     processed += 1
    #     sys.stdout.write('\r[%2.2f%%]' % (processed / file_count))

    # m.save()

    # m = MarkovModel.from_dump(4)

    # m = MarkovModel(order=[3, 7], 'wiki_100k.txt')

    import pdb; pdb.set_trace()
