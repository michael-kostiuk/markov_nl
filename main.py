import json
import time
import re

from functools import reduce


TRAIN_DIR = 'out'
MINIMAL_WORD_FREQ_THRESHOLD = 0.0001
MARKOV_PROBABILY_THRESHOLD = 0.0003


def memo(f):
    "Memoize function f, whose args must all be hashable."
    cache = {}
    def fmemo(*args):
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]
    fmemo.cache = cache
    return fmemo


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

    def reset(self):
        self.__file_object.seek(0)

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
                        break
                except IndexError:
                    # file ended before chunk
                    raise StopIteration
            chunk = self.__file_object.read(self.chunk_size)

        return word, length


class MarkovModel(object):
    dump_filename = 'model.json'

    @classmethod
    def from_dump(cls):
        with open(cls.dump_filename, 'r') as f:
            data = json.loads(f.read())
            m = cls(data['orders'])
            m.graph = data['graph']

        return m

    def __init__(self, orders=[], filename=None):
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
                        self.graph[kgram].setdefault('ALL', 0)
                        self.graph[kgram]['ALL'] += 1

    def freq_part(self, part):
        try:
            kk = self.graph[part].keys()
        except KeyError:
            return 0

        N = kk.pop('ALL')
        return sum(kk.values())

    def next_for_part(self, part):
        try:
            kk = list(self.graph[part].keys())
        except KeyError:
            return []
        kk.remove('ALL')
        return kk

    def freq(self, part, symb):
        """Return smoothed frequency how many times symbol appears after kgram"""
        return (self.graph.get(part, {}).get(symb, 0) + 1) / self.graph.get(part, {'ALL': len(self.graph)})['ALL']

    def pprint(self):
        out = ['%s: %s' % (k, v) for k, v in self.graph.items()]
        return '\n'.join(out)

    def save(self):
        with open(self.dump_filename, 'r') as f1:
            with open('%s.%s' % (time.time(), self.dump_filename), 'w') as f2:
                f2.write(f1.read())

        with open(self.dump_filename, 'w') as f:
            dump_data = {'graph': self.graph, 'orders': self.orders}
            f.write(json.dumps(dump_data))


class Spellcheck(object):
    alphabet = 'abcdefghijklmnopqrstuvwxyz'

    def __init__(self, words_bag, model):
        self.words_bag = words_bag
        self.model = model
        self.N = sum(words_bag.values())

    def edits1(self, word):
        "Return all strings that are one edit away from this word."
        pairs      = self.splits(word)
        deletes    = [a+b[1:]           for (a, b) in pairs if b]
        transposes = [a+b[1]+b[0]+b[2:] for (a, b) in pairs if len(b) > 1]
        replaces   = [a+c+b[1:]         for (a, b) in pairs for c in Spellcheck.alphabet if b]
        inserts    = [a+c+b             for (a, b) in pairs for c in Spellcheck.alphabet]
        return set(deletes + transposes + replaces + inserts)

    def editsN(self, word, num):
        edits = {word}
        for _ in range(num):
            temp = set()
            for edit in edits:
                temp.update(self.edits1(edit))
            edits.update(temp)
        return edits

    def splits(self, text, start=0, L=20):
        "Return a list of all (first, rest) pairs; start <= len(first) <= L."
        return [(text[:i], text[i:]) for i in range(start, min(len(text), L)+1)]

    def freq(self, word):
        try:
            return self.words_bag[word] / self.N
        except KeyError:
            return 0

    def p_words(self, words):
        return self._product([self.freq(w) for w in words])

    def _product(self, l):
        result = 1
        for el in l:
            result *= el
        return result

    @memo
    def segment(self, text):
        "Return a list of words that is the most probable segmentation of text."
        if not text:
            return []
        else:
            candidates = [[first] + self.segment(rest) for (first, rest) in self.splits(text, 1)]
            return max(candidates, key=self.p_words)

    def looks_like_word(self, word):
        l_word = len(word)

        if all([order < l_word for order in self.model.orders]):
            # cant check word less then order of model
            return False

        probability = 1
        for order in self.model.orders:
            for i in range(l_word-order):
                kgram = word[i:i+order]
                probability *= self.model.freq(kgram, word[i+order])
        return probability > MARKOV_PROBABILY_THRESHOLD

    def correct(self, word, edits_depth=2):
        if self.looks_like_word(word):
            return word

        options = []
        if self.freq(word) > MINIMAL_WORD_FREQ_THRESHOLD:
            options.append((self.freq(word), word))
        else:
            word_fixed = max(self.editsN(word, edits_depth), key=lambda x: self.freq(x))
            options.append((self.freq(word_fixed), word_fixed))

        # check if multiple words collapsed
        out = []
        for word_candidate in self.segment(word):
            out.append(word_candidate)


        options.append((sum([self.freq(x) for x in out]), ' '.join(out)))
        return max(options)[1]

    def correct_match(self, match):
        "Spell-correct word in match, and preserve proper upper/lower/title case."
        word = match.group()
        return self.case_of(word)(self.correct(word.lower()))

    def case_of(self, text):
        "Return the case-function appropriate for text: upper, lower, title, or just str."
        return (str.upper if text.isupper() else
                str.lower if text.islower() else
                str.title if text.istitle() else
                str)

    def check_text(self, text):
        "Correct all the words within a text, returning the corrected text."
        return re.sub('[a-zA-Z]+', self.correct_match, text)


if __name__ == "__main__":
    import sys
    from os import listdir, path
    from collections import Counter

    # docs = listdir(TRAIN_DIR)
    # file_count = len(docs)
    # processed = 0


    # heavy calculate
    # model = MarkovModel([3, 5, 7])
    # bag = Counter()
    # for doc in docs:
    #     model.feed(path.join(TRAIN_DIR, doc))
        # with WordReader(path.join(TRAIN_DIR, doc)) as w:
        #     for word in w:
        #         bag[word] += 1
    #     processed += 1
    #     sys.stdout.write('\r[%2.2f%%]' % (processed / file_count * 100))
    # model.save()

    # or fast restore from dump
    m = MarkovModel.from_dump()

    with open('words_bag_dump.json', 'r') as f:
        bag = Counter(json.loads(f.read()))

    spellcheck = Spellcheck(bag, m)
    text = """
            The Zen of Python, by Tim Peters

            Beauteaful is bettor thanugly.
            Explicit isbetter than implicit.
            Simple is betterthan complex.
            Complex is better thancomplicated.
            Flat is better than nested.
            Sparse is better than dense.
            Readabilitie counts.
            Speciall cases aren't speciial enouugh to breakk othoe rulles.
            Although practicality beats purity.
            Errors should never pass silently.
            Unless explicitly silenced.
            In the face of ambiguity, refuse the temptation to guess.
            There should be one-- and preferably only one --obvious way to do it.
            Although that way may not be obvious at first unless you're Dutch.
            Now is better than never.
            Although never is often better than *right* now.
            If the implementation is hard to explain, it's a bad idea.
            If the implementation is easy to explain, it may be a good idea.
            Namespaces are one honking great idea -- let's do more of those!
            """
    # text = input()
    corrected_text = spellcheck.check_text(text)
    print(corrected_text)
