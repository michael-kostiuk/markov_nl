import random


ASCII = 128
ASCII_CODES = range(ASCII)
ALL = 'ALL'


def read_file(fileanme):
    with open(fileanme) as f:
        return f.read()


class MarkovModel(object):

    def __init__(self, text, order):
        self.graph = {}
        self.order = order
        self._text = text
        length = len(text)
        text += text[:order]
        for i in range(0, length):
            kgram = text[i:i+order]
            symb = text[i+order]
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

    # text = 'banana'
    # m = MarkovModel(text, 2)
    # pprint.pprint(m.pprint())


    # text = 'gagggagaggcgagaaa'
    # m = MarkovModel(text, 2)
    # pprint.pprint(m.pprint())
    # txt = m.random_text(1000)
    # import pdb; pdb.set_trace()
    import re
    # text = read_file('wiki_100k.txt')
    text = read_file('hltv.txt')
    import pdb; pdb.set_trace()
    # m = MarkovModel(text, 4)

    # spellcheck(m)
